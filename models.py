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