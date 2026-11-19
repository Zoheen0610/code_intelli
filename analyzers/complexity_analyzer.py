"""Flag functions that are too long (and, next step, too branchy)."""
from models import FileInfo, Finding

MAX_LENGTH = 50   # lines; a common rule of thumb is 30-60
MAX_COMPLEXITY = 10  # cyclomatic complexity; a common rule of thumb is 1-10


def complexity_analyzer(info: FileInfo) -> list[Finding]:
    """Flag functions and methods that are longer than MAX_LENGTH or if the complexity exceeds MAX_COMPLEXITY."""
    findings = []
    for symbol in info.symbols:
        if symbol.kind == "class":
            continue
        if symbol.length > MAX_LENGTH:
            findings.append(Finding(
                rule="long-function",
                severity="medium",
                file=info.path,
                line=symbol.line_start,
                message=f"{symbol.kind.capitalize()} '{symbol.name}' is {symbol.length} lines (max {MAX_LENGTH})"
            ))
        if symbol.complexity > MAX_COMPLEXITY:
            findings.append(Finding(
                rule="complex-function",
                severity="medium",
                file=info.path,
                line=symbol.line_start,
                message=f"{symbol.kind.capitalize()} '{symbol.name}' has cyclomatic complexity {symbol.complexity} (max {MAX_COMPLEXITY})"
            ))
    return findings



if __name__ == "__main__":
    import sys
    from loader import find_files, parse_python

    for f in find_files(sys.argv[1]):
        for finding in complexity_analyzer(parse_python(f)):
            print(f"[{finding.severity}] {finding.file}:{finding.line}  {finding.message}")
