"""Find Python files in a folder and extract their symbols.

Usage: python loader.py <folder>
"""
import ast
from pathlib import Path

from models import Symbol, FileInfo, SymbolVisitor

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}




def find_files(root: str) -> list[Path]:
    """Return every .py file under root, sorted, skipping IGNORE_DIRS inside the project."""
    p =Path(root).resolve()
    return sorted(f for f in p.rglob("*.py")
              if f.is_file() and not any(part in IGNORE_DIRS for part in f.relative_to(p).parts))


def parse_python(path: Path) -> FileInfo:
    """Parse one file into a FileInfo. Never raises on a bad file: sets `error` instead."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        return FileInfo(path=str(path), language="python", source="", error=str(e))
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        return FileInfo(path=str(path), language="python", source=source, error=str(e))
    
    info = FileInfo(path=str(path), language="python", source=source)

    visitor = SymbolVisitor(str(path))
    visitor.visit(tree)

    info.symbols = visitor.symbols
    # The visitor already goes in code order; sorting keeps the output stable anyway.
    info.symbols.sort(key=lambda s: (s.line_start, s.name))
    return info


if __name__ == "__main__":
    import sys

    for f in find_files(sys.argv[1]):
        info = parse_python(f)
        if info.error:
            print(f"Error parsing {info.path}: {info.error}")
        else:
            for s in info.symbols:
                print(f"{s.file}:{s.line_start} 'length of function/class'={s.length} {s.kind:8} {s.name}  doc={s.has_docstring}")
