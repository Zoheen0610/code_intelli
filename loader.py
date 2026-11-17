import ast
from dataclasses import dataclass, field
from pathlib import Path

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}


@dataclass
class Symbol:
    name: str
    kind: str          # "function" | "class"
    file: str
    line: int
    has_docstring: bool


@dataclass
class FileInfo:
    path: str
    language: str
    source: str
    symbols: list[Symbol] = field(default_factory=list)
    error: str | None = None


def find_files(root: str) -> list[Path]:
    p = Path(root).resolve()
    return [f for f in p.rglob("*.py") if f.is_file() and not any(part in IGNORE_DIRS for part in f.relative_to(p).parts)]


def parse_python(path: Path) -> FileInfo:
    source = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        return FileInfo(path=str(path), language="python", source=source, error=str(e))
    
    info = FileInfo(path=str(path), language="python", source=source)

    # ast.walk is bfs traversal
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        info.symbols.append(Symbol(
                name=node.name,
                kind="class" if isinstance(node, ast.ClassDef) else "function",
                file=info.path,
                line=node.lineno,
                has_docstring=bool(ast.get_docstring(node))
        ))
        
    return info


if __name__ == "__main__":
    import sys

    for f in find_files(sys.argv[1]):
        info = parse_python(f)
        if info.error:
            print(f"Error parsing {info.path}: {info.error}")
        else:
            for s in info.symbols:
                print(f"{s.file}:{s.line}  {s.kind:8} {s.name}  doc={s.has_docstring}")
