"""Split parsed files into searchable chunks: one per function or method."""
from dataclasses import dataclass

from models import FileInfo


@dataclass
class Chunk:
    """One searchable piece of code."""
    file: str
    name: str          # e.g. "Dog.bark"
    line_start: int
    line_end: int
    text: str          # a header (file + name) followed by the code


def chunk_file(info: FileInfo) -> list[Chunk]:
    """One chunk per function or method in the file."""
    lines = info.source.splitlines()
    chunks = []
    for symbol in info.symbols: 
        
        if symbol.kind == 'class':
            continue
  
        start = symbol.line_start
        end = symbol.line_end
        lines_for_context = lines[start-1:end]
        lines_for_context = [f"{n:4} | {text}" for n, text in enumerate(lines_for_context, start = start)]
            
        code = "\n".join(lines_for_context)
        text = "\n".join([f"# File: {info.path}", f"# Function: {symbol.name}", code])

        chunk = Chunk(file=symbol.file, name=symbol.name, line_start=symbol.line_start, line_end=symbol.line_end,text=text)
        chunks.append(chunk)
    return chunks


def chunk_files(files: list[FileInfo]) -> list[Chunk]:
    """Chunks for every file that parsed."""
    all_chunks = []
    for file in files:
        if file.error:
            continue

        chunks = chunk_file(file)
        all_chunks.extend(chunks)

    return all_chunks



