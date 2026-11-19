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
class FileInfo:
    """Everything extracted from one file. `error` is set when it couldn't be read or parsed."""
    path: str
    language: str
    source: str
    symbols: list[Symbol] = field(default_factory=list)
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
    """

    def __init__(self, file):
        self.file = file
        self.stack = []      # where we are: e.g. [("Dog", "class")]
        self.symbols = []

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