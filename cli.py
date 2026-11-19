"""Command-line entry point.

Usage:
    python cli.py analyze <path> [-o report.md] [--fail-on high]

Exit codes (how CI knows whether the check passed):
    0  no findings at or above --fail-on (or --fail-on not given)
    1  at least one finding at or above --fail-on
    2  bad usage, e.g. the path doesn't exist
"""
import argparse
import sys
from pathlib import Path

from analyzers.complexity_analyzer import complexity_analyzer
from analyzers.docstring_analyzer import docs_analyzer
from analyzers.security_analyzer import security_analyzer
from loader import find_files, parse_python
from models import FileInfo, Finding
from report_generation.report import SEVERITY_ORDER, render_report
from graph.dependency_graph import build_graph, find_hotspots, find_cycles
# Functions are values in Python, so analyzers can live in a list.
# Adding a fourth analyzer = adding one entry here.
ANALYZERS = [docs_analyzer, complexity_analyzer, security_analyzer]


def run_analysis(path: str) -> tuple[list[FileInfo], list[Finding]]:
    """Parse every file under path and run every analyzer on the ones that parsed."""
    files = [parse_python(f) for f in find_files(path)]
    findings = []
    for info in files:
        if info.error:
            continue  # nothing to analyze; the report lists it separately
        for analyzer in ANALYZERS:
            findings.extend(analyzer(info))
    return files, findings


def should_fail(findings: list[Finding], fail_on: str | None) -> bool:
    """True if any finding is at least as serious as fail_on."""
    if fail_on is None:
        return False
    # SEVERITY_ORDER is most serious first, so "at or above medium" = ["high", "medium"].
    blocking = SEVERITY_ORDER[: SEVERITY_ORDER.index(fail_on) + 1]
    return any(f.severity in blocking for f in findings)


def analyze(path: str, output: str, fail_on: str | None) -> int:
    """Run the `analyze` command. Returns the exit code."""
    if not Path(path).is_dir():
        print(f"error: '{path}' is not a folder", file=sys.stderr)
        return 2

    files, findings = run_analysis(path)
    
    graph = build_graph(files, path)
    hotspots = find_hotspots(graph, files)
    cycles = find_cycles(graph)

    report = render_report(findings, files,  root=path, hotspots=hotspots, cycles=cycles)
    Path(output).write_text(report, encoding="utf-8")

    # A short summary on screen, so the user knows it worked and where to look.
    counts = ", ".join(f"{sum(1 for f in findings if f.severity == s)} {s}" for s in SEVERITY_ORDER)
    print(f"Scanned {len(files)} files: {counts}. Report written to {output}")

    if should_fail(findings, fail_on):
        print(f"FAILED: findings at or above '{fail_on}' severity", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    """Parse command-line arguments and run the chosen command."""
    parser = argparse.ArgumentParser(prog="yourtool", description="Static code analysis for Python projects.")
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="analyze a folder and write a Markdown report")
    a.add_argument("path", help="folder to analyze")
    a.add_argument("-o", "--output", default="report.md", help="where to write the report (default: report.md)")
    a.add_argument("--fail-on", choices=SEVERITY_ORDER, default=None,
                   help="exit with code 1 if any finding is at or above this severity (for CI)")

    args = parser.parse_args()
    if args.command == "analyze":
        return analyze(args.path, args.output, args.fail_on)
    return 2


if __name__ == "__main__":
    sys.exit(main())  # the return value becomes the process exit code
