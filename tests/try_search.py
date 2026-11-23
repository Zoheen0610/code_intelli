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

# Q1 worked : redact (2 shared words), then secret_values, then build_prompt, which calls them both. That's a great result.

# Q2 is a three-way tie: complexity_analyzer, cyclomatic_complexity and visit_FunctionDef all score 2. Only one of them actually counts complexity. The score can't tell that "cyclomatic" (a rare word, found in about 2 chunks) is much stronger evidence than "complexity" (found all over the place). Every shared word counts the same.

# Q3 failed completely : got analyze, find_hotspots and run_analysis, none of which is about passwords. 

# That's the core weakness of keyword search: it matches spelling, not meaning. Three failure types, all visible in your output:

# Same meaning, different words: passwords vs secret vs credential
# Different forms of a word: passwords vs password, counted vs count
# All words weigh the same: rare "cyclomatic" counts no more than common "code"
# Type 3 has a classic fix: give rare words more weight. That's called IDF, and it's a good optional stretch. Types 1 and 2 need something that understands meaning. That's embeddings, 
