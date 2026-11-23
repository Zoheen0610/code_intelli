from loader import find_files, parse_python
from rag.chunker import chunk_files
from rag.keyword import keyword_search

chunks = chunk_files([parse_python(f) for f in find_files(".")])

questions = [
    "where are secrets redacted before sending?",
    "how is cyclomatic complexity counted?",
    "how do I find passwords in someone's code?",
]
for question in questions:
    print("Q:", question)
    retrieved_chunks = keyword_search(question, chunks, k=3)
    print(f"chunk 1: score={retrieved_chunks[0][0]}  chunk={retrieved_chunks[0][1].name}" )
    print()
    print(f"chunk 2: score={retrieved_chunks[1][0]}  chunk={retrieved_chunks[1][1].name}" )
    print()
    print(f"chunk 3: score={retrieved_chunks[2][0]}  chunk={retrieved_chunks[2][1].name}" )
    print()
