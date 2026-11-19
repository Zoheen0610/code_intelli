"""Build a file-level import graph and find hotspots."""
from pathlib import Path
import networkx as nx
from models import FileInfo
from dataclasses import dataclass


@dataclass
class Hotspot:
    """A file ranked by how risky it is to change."""
    path: str
    fan_in: int
    fan_out: int
    complexity: int      # sum over its functions and methods
    score: int


def find_hotspots(graph: nx.DiGraph, files: list[FileInfo], top: int = 5) -> list[Hotspot]:
    """Rank files by (1 + fan_in) * total complexity, highest first."""
    hotspots = []
    for f in files:
        complexity = 0
        for s in f.symbols:
            if s.kind != "class":
                complexity += s.complexity

        fan_in = graph.in_degree(f.path)
        fan_out = graph.out_degree(f.path)
        score = (1 + fan_in) * complexity

        hotspots.append(Hotspot(path=f.path, fan_in=fan_in, fan_out=fan_out,
                        complexity=complexity, score=score))


    hotspots = sorted([h for h in hotspots if h.score > 0], key= lambda h: (h.score), reverse=True)
   
    return hotspots[:top]


def find_cycles(graph: nx.DiGraph) -> list[list[str]]:
    """Every import loop, e.g. [['a.py', 'b.py']] for a -> b -> a."""
    return list(nx.simple_cycles(graph))


def module_name(path: str, root: str) -> str:
    """'C:/proj/report_generation/report.py' -> 'report_generation.report'."""
    p = Path(path).relative_to(Path(root).resolve())
    p = p.with_suffix("")  
        
    parts = p.parts                  # ('analyzers', '__init__')
    if parts[-1] == "__init__":      # is the LAST part __init__?
        parts = parts[:-1]           # keep everything except the last → ('analyzers',)
    name = ".".join(parts)

    return name


def build_graph(files: list[FileInfo], root: str) -> nx.DiGraph:
    """One node per file, one edge per import between project files."""
    graph = nx.DiGraph()

    lookup = {module_name(f.path, root): f.path for f in files}

    for f in files:
        graph.add_node(f.path)

    for f in files:
        for imp in f.imports:
            if imp in lookup:
                graph.add_edge(f.path,lookup[imp])
    
    return graph
