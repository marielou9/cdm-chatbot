import math

from google import genai
from google.genai import types

# models
EMBEDDING_MODEL = "gemini-embedding-001"
ANSWER_MODEL = "gemini-3.5-flash-lite"

# vector size and API limit per request
DIMENSIONS = 768
BATCH_SIZE = 100


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed texts with Gemini, normalized to length 1 as Google requires below 3072 dimensions.

    Sends at most 100 texts per request, the limit of the Gemini API.
    """

    client = genai.Client()
    config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=DIMENSIONS)
    vectors = []

    # one request per 100 texts
    for start in range(0, len(texts), BATCH_SIZE):
        result = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=texts[start : start + BATCH_SIZE], config=config
        )
        vectors += [_normalize(e.values) for e in result.embeddings]

    return vectors


def _normalize(vector: list[float]) -> list[float]:
    """Scale a vector to length 1."""

    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector]


def complete(prompt: str) -> str:
    """Send a prompt to the Gemini answer model at temperature 0 and return its text reply."""

    client = genai.Client()
    config = types.GenerateContentConfig(temperature=0)
    return client.models.generate_content(model=ANSWER_MODEL, contents=prompt, config=config).text
