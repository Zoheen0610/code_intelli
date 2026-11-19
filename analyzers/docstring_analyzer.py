"""Analyzers turn extracted symbols into findings."""
from models import FileInfo, Finding, Symbol


def needs_docstring(symbol: Symbol) -> bool:
    """Decide whether a symbol should be flagged when it has no docstring."""
    short = symbol.name.split(".")[-1]   # "Dog._clean" -> "_clean"
    if short.startswith("_"):            # private helpers, and dunders like __init__
        return False
    if short.startswith("test_"):        # test names describe themselves
        return False
    
    return True


def docs_analyzer(info: FileInfo) -> list[Finding]:
    """Flag public classes, methods and functions that have no docstring."""
    findings = []
    for symbol in info.symbols:
        if not symbol.has_docstring and needs_docstring(symbol):
            findings.append(Finding(
                rule="missing-docstring",
                severity="low",
                file=info.path,
                line=symbol.line_start,
                message=f"{symbol.kind.capitalize()} '{symbol.name}' has no docstring",
            ))
    return findings


if __name__ == "__main__":
    import sys
    from loader import find_files, parse_python

    for f in find_files(sys.argv[1]):
        for finding in docs_analyzer(parse_python(f)):
            print(f"[{finding.severity}] {finding.file}:{finding.line}  {finding.message}")
