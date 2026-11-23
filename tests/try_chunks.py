from models import Symbol, FileInfo
from pathlib import Path
from loader import find_files, parse_python
from rag.chunker import chunk_files
import pathlib

files = find_files(".")
file_objs = []
for file in files:
    fileobj = parse_python(file)
    file_objs.append(fileobj)


chunks = chunk_files(file_objs)

for c in chunks:
    if c.name == "redact":
        print(c.text)

print(len(chunks))