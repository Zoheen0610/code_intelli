"""Language-neutral data shapes, plus the visitor that fills them from a Python AST."""
import ast
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Symbol:
    """One class, method or function found in a source file."""
    name: str
    kind: str          # "function" | "method" | "class"
    file: str
    line_start: int
    line_end: int
    has_docstring: bool
    complexity: int = 1  # cyclomatic complexity

    @property
    def length(self) -> int:
        """Number of lines the symbol spans, inclusive."""
        return self.line_end - self.line_start + 1


@dataclass
class CallSite:
    """One function call, with its name resolved through imports.

    `import subprocess as sp; sp.run(...)` is stored as name="subprocess.run",
    so analyzers can match calls without knowing how they were imported.
    """
    name: str
    line: int
    scope: str                    # enclosing symbol, e.g. "Dog.bark"; "" at module level
    keywords: dict[str, object] = field(default_factory=dict)  # literal values; anything else is "<expr>"
    arg_count: int = 0            # number of positional arguments


@dataclass
class Assignment:
    """A string literal assigned to a name, e.g. API_KEY = "abc123"."""
    target: str                   # the name assigned to, e.g. "API_KEY" or "self.password"
    value: str
    line: int
    scope: str


@dataclass
class FileInfo:
    """Everything extracted from one file. `error` is set when it couldn't be read or parsed."""
    path: str
    language: str
    source: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)          # module names, e.g. "os", ".models"
    calls: list[CallSite] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    error: str | None = None

@dataclass
class Finding:
    """One problem an analyzer found, with where it is and how serious it is."""
    rule: str        # short id, e.g. "missing-docstring"
    severity: str    # "low" | "medium" | "high"
    file: str
    line: int
    message: str     # e.g. "Function 'find_files' has no docstring"

# Nodes where code can take a different path. Each one adds 1 to complexity.
# `elif` needs no entry: Python stores it as an If nested in the else branch.
# `with` is not here: its body always runs, so it adds no new path.
BRANCH_NODES = (
    ast.If,             # if / elif
    ast.For,            # for loop: run the body again, or leave
    ast.AsyncFor,       # async for
    ast.While,          # while loop
    ast.ExceptHandler,  # each `except` block is its own path
    ast.IfExp,          # x if c else y
)

# Nodes that are measured as their own symbol, so we don't step into them.
# Otherwise one messy nested helper would make its outer function look complex too.
NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def cyclomatic_complexity(func_node: ast.AST) -> int:
    """1 + the branch points in this function, not counting nested defs."""
    count = 1  # one straight path through, before any branches

    # We walk the tree ourselves instead of using ast.walk, so we can
    # choose NOT to go inside nested functions and classes.
    to_visit = list(ast.iter_child_nodes(func_node))  # direct children only
    while to_visit:
        node = to_visit.pop()

        if isinstance(node, NESTED_SCOPES):
            continue  # skip it and everything inside it

        if isinstance(node, BRANCH_NODES):
            count += 1
        elif isinstance(node, ast.BoolOp):
            # `a and b and c` is ONE BoolOp with values [a, b, c].
            # Each extra condition is one more way out: 3 values -> 2 branches.
            count += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            # `[x for x in xs if a if b]`: each `if` filter is a branch.
            count += len(node.ifs)

        # Queue this node's children so we look inside it next.
        to_visit.extend(ast.iter_child_nodes(node))

    return count

class SymbolVisitor(ast.NodeVisitor):
    """Walks an AST in code order and collects a Symbol for each class and function.

    A stack of (name, kind) pairs tracks the enclosing scopes, giving
    dotted names like "Dog.bark" and telling methods apart from functions.
    It also records imports, calls and string assignments for the security analyzer.
    """

    def __init__(self, file):
        self.file = file
        self.stack = []      # where we are: e.g. [("Dog", "class")]
        self.symbols = []
        self.imports = []
        self.calls = []
        self.assignments = []
        # Local name -> full dotted name, filled from import statements.
        # e.g. {"sp": "subprocess", "system": "os.system"}
        self.aliases = {}

    # ---------- helpers ----------

    def _scope(self) -> str:
        """Dotted name of where we are right now, e.g. "Dog.bark"."""
        return ".".join(name for name, _ in self.stack)

    def _dotted(self, node) -> str | None:
        """Turn `a.b.c` (Name/Attribute nodes) into the string "a.b.c".

        Returns None for anything else, e.g. `get_func()(x)` or `items[0](x)`.
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._dotted(node.value)
            return f"{base}.{node.attr}" if base else None
        return None

    def _resolve(self, dotted: str) -> str:
        """Replace the first part of a dotted name with what it was imported as.

        With `import subprocess as sp`, "sp.run" becomes "subprocess.run".
        """
        first, _, rest = dotted.partition(".")
        base = self.aliases.get(first, first)
        return f"{base}.{rest}" if rest else base

    # ---------- imports ----------

    def visit_Import(self, node):
        """`import os`, `import os.path`, `import subprocess as sp`."""
        for alias in node.names:
            self.imports.append(alias.name)
            if alias.asname:
                # import os.path as p  ->  p means "os.path"
                self.aliases[alias.asname] = alias.name
            else:
                # import os.path  ->  only the name "os" is bound
                first = alias.name.split(".")[0]
                self.aliases[first] = first
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """`from os import system`, `from . import models`."""
        # node.level counts leading dots for relative imports: `from ..x import y` -> 2
        module = "." * node.level + (node.module or "")
        self.imports.append(module)
        for alias in node.names:
            if alias.name == "*":
                continue  # can't know which names a star import brings in
            self.aliases[alias.asname or alias.name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    # ---------- calls and assignments ----------

    def visit_Call(self, node):
        """Record a call like `subprocess.run(cmd, shell=True)`."""
        dotted = self._dotted(node.func)
        if dotted:
            keywords = {}
            for kw in node.keywords:
                if kw.arg is None:
                    continue  # **kwargs: we can't see the names
                # Keep literal values (True, "md5", 3); mark everything else.
                keywords[kw.arg] = kw.value.value if isinstance(kw.value, ast.Constant) else "<expr>"
            self.calls.append(CallSite(
                name=self._resolve(dotted),
                line=node.lineno,
                scope=self._scope(),
                keywords=keywords,
                arg_count=len(node.args),
            ))
        self.generic_visit(node)  # calls can be nested: f(g(x))

    def _record_string_assignment(self, target, value, line):
        """Store `target = "some string"` if target is a plain or dotted name."""
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            name = self._dotted(target)
            if name:
                self.assignments.append(Assignment(name, value.value, line, self._scope()))

    def visit_Assign(self, node):
        """`password = "hunter2"` (also `a = b = "x"`, which has two targets)."""
        for target in node.targets:
            self._record_string_assignment(target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        """`password: str = "hunter2"` (an assignment with a type annotation)."""
        if node.value is not None:
            self._record_string_assignment(node.target, node.value, node.lineno)
        self.generic_visit(node)

    # ---------- symbols ----------

    def visit_ClassDef(self, node):
        """Record the class, then visit its body with the class on the stack."""
        self.symbols.append(Symbol(
            name=".".join([name for name, _ in self.stack] + [node.name]),
            kind="class",
            file=self.file,
            line_start=node.lineno,
            line_end=node.end_lineno,
            has_docstring=bool(ast.get_docstring(node)),
            complexity=1
        ))

        self.stack.append((node.name, "class"))    # step INTO Dog
        self.generic_visit(node)       # visit everything inside Dog
        self.stack.pop()               # step back OUT of Dog

    def visit_FunctionDef(self, node):
        """Record a function: a method if directly inside a class, else a function."""
        if self.stack and self.stack[-1][1] == "class":
            kind = "method"
        else:
            kind = "function"
        self.symbols.append(Symbol(
            name=".".join([name for name, _ in self.stack] + [node.name]),
            kind=kind,
            file=self.file,
            line_start=node.lineno,
            line_end=node.end_lineno,
            has_docstring=bool(ast.get_docstring(node)),
            complexity=cyclomatic_complexity(node)
        ))
        self.stack.append((node.name, "function"))
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef


if __name__ == "__main__":
    code = """
class Dog:
    def bark(self):
        def helper():
            pass

def main():
    pass
"""
    v = SymbolVisitor("test.py")
    v.visit(ast.parse(code))
    for s in v.symbols:
        print(s)