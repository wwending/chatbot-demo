import hashlib
import math
import re


VECTOR_SIZE = 256


def tokenize(text: str) -> list[str]:
    lower = text.lower()
    words = re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fa5]", lower)
    bigrams = [lower[i : i + 2] for i in range(max(0, len(lower) - 1)) if "\n" not in lower[i : i + 2]]
    return words + bigrams


def embed_text(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    for token in tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % VECTOR_SIZE
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
