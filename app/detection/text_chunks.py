"""Bounded NLP inputs with overlapping edges and original-text offsets."""
from collections.abc import Iterator


def iter_text_chunks(text: str, size: int = 100_000, overlap: int = 256) -> Iterator[tuple[int, str]]:
    if not 0 <= overlap < size:
        raise ValueError('El solapamiento debe ser menor que el tamaño del bloque.')
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        yield start, text[start:end]
        if end == len(text):
            break
        start = end - overlap
