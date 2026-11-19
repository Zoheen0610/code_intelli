"""Turn findings into a Markdown report."""
from pathlib import Path
from graph.dependency_graph import Hotspot
from models import FileInfo, Finding

# Most serious first: that's what a reader looks for.
SEVERITY_ORDER = ["high", "medium", "low"]

def _hotspot_section(hotspots: list[Hotspot], root: str | None) -> list[str]:
    """Table of the riskiest files to change."""
    lines = [
        "",
        "## Hotspots",
        "",
        "Files that are both complex and depended on. Change these carefully.",
        "",
        "| File | Score | Fan-in | Fan-out | Complexity |",
        "|---|---|---|---|---|",
    ]
    
    for h in hotspots:
        lines.append(f"| {_cell(_relative(h.path, root))} | {h.score} | {h.fan_in} | {h.fan_out} | {h.complexity} |")
    return lines


def _cycles_section(cycles: list[list[str]], root: str | None) -> list[str]:
    """List every import loop, e.g. `a.py` → `b.py` → `a.py`."""
   
    if not cycles:
        return []

    lines = [
        "",
        f"## Import cycles ({len(cycles)})",
        "",
    ]
    
    for cycle in cycles:
        loop = cycle + [cycle[0]]                                # close it: a, b, a
        names = [f"`{_relative(p, root)}`" for p in loop]        # new list, nothing mutated
        lines.append("- " + " → ".join(names))                   # bullet = its own line


    return lines



def _relative(path: str, root: str | None) -> str:
    """Show paths relative to the scanned folder: 'src/db.py', not 'C:/Users/.../src/db.py'."""
    if root is None:
        return path
    try:
        return Path(path).relative_to(Path(root).resolve()).as_posix()
    except ValueError:  # path isn't inside root
        return path


def _cell(text: str) -> str:
    """Make text safe inside a Markdown table cell: a '|' would start a new column."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _summary(findings: list[Finding], files: list[FileInfo]) -> str:
    """One line, e.g. 'Scanned 4 files: 3 high, 1 medium, 2 low.'"""
    counts = [f"{sum(1 for f in findings if f.severity == s)} {s}" for s in SEVERITY_ORDER]
    return f"Scanned {len(files)} files: {', '.join(counts)}."


def _severity_section(severity: str, group: list[Finding], root: str | None) -> list[str]:
    """A heading plus a table for one severity level."""
    lines = [
        "",
        f"## {severity.capitalize()} ({len(group)})",
        "",
        "| File | Line | Rule | Message |",
        "|---|---|---|---|",
    ]
    for f in group:
        lines.append(f"| {_cell(_relative(f.file, root))} | {f.line} | `{f.rule}` | {_cell(f.message)} |")
    return lines


def render_report(findings: list[Finding], files: list[FileInfo],  root: str | None = None, hotspots: list[Hotspot] | None = None, cycles: list[list[str]] | None = None) -> str:
    """Build the whole report as one Markdown string.

    `root` is the scanned folder; when given, file paths are shown relative to it.
    """
    lines = ["# Code analysis report", "", _summary(findings, files)]

    if not findings:
        # An empty report looks broken, so say it out loud.
        lines += ["", "No findings. 🎉"]

    # One section per severity, most serious first, skipping empty ones.
    for severity in SEVERITY_ORDER:
        group = sorted(
            (f for f in findings if f.severity == severity),
            key=lambda f: (f.file, f.line),   # Findings can't be compared directly
        )
        if group:
            lines += _severity_section(severity, group, root)
    if hotspots:
        lines += _hotspot_section(hotspots, root)
    if cycles:
        lines += _cycles_section(cycles, root)

    # Files we couldn't read or parse: the reader should know they weren't checked.
    broken = [info for info in files if info.error]
    if broken:
        lines += ["", f"## Files that couldn't be parsed ({len(broken)})", ""]
        for info in broken:
            lines.append(f"- `{_relative(info.path, root)}`: {info.error}")

    return "\n".join(lines) + "\n"
