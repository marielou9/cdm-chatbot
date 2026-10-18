import math

from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"
DIMENSIONS = 768


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed texts with Gemini, normalized to length 1 as Google requires below 3072 dimensions."""
    client = genai.Client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=DIMENSIONS),
    )
    return [_normalize(e.values) for e in result.embeddings]


def _normalize(vector: list[float]) -> list[float]:
    """Scale a vector to length 1."""
    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector]
