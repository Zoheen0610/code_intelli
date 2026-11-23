"""Retrieval v1: score chunks by how many words they share with the question."""
import re
from rag.chunker import Chunk

WORD = re.compile(r"[a-z0-9]+")      # runs of letters/digits; "_" and "(" split words
STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "in", "on", "and", "or", "it",
    "how", "what", "where", "which", "does", "do", "i", "my",
    "def", "self", "return", "for", "if", "else", "none", "true", "false", "file", "function",
}


def tokenize(text: str) -> set[str]:
    """The meaningful lowercase words in text."""
    words = WORD.findall(text.lower())
    return set([word for word in words if word not in STOPWORDS])


def keyword_search(question: str, chunks: list[Chunk], k: int = 5) -> list[tuple[int, Chunk]]:
    """The k chunks sharing the most words with the question, as (score, chunk), best first."""
    # TODO 3: q = tokenize(question)
    q = tokenize(question)
    # TODO 4: scored = [(score, chunk) for each chunk], score = len(q & tokenize(chunk.text))
    scored = []
    for chunk in chunks:
        score = len(q & tokenize(chunk.text))
        scored.append((score, chunk))
    # TODO 5: drop the ones with score 0, sort by score highest first, return the first k

    return sorted([tup for tup in scored if tup[0]>0], key= lambda tup: tup[0], reverse=True)[:k]
