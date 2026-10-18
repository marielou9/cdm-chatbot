"""Embed all index entries once and store the vectors, so the app starts without embedding calls."""

import json
import time

from app.api import EMBEDDINGS_FILE, build_index_entries
from app.gemini import BATCH_SIZE, embed

# free tier allows 100 texts per minute
FREE_TIER_PAUSE_SECONDS = 61


def main():
    """Embed every distinct index text and write the vectors to the embeddings file."""

    # every distinct embed text once
    texts = sorted({entry.embed_text for entry in build_index_entries()})
    vectors = []

    # 100 texts per batch, pause between batches
    for start in range(0, len(texts), BATCH_SIZE):
        if start > 0:
            print(f"waiting {FREE_TIER_PAUSE_SECONDS}s for the free tier limit of 100 texts per minute")
            time.sleep(FREE_TIER_PAUSE_SECONDS)
        vectors += embed(texts[start : start + BATCH_SIZE], "RETRIEVAL_DOCUMENT")

    # write rounded vectors
    stored = {text: [round(x, 5) for x in vector] for text, vector in zip(texts, vectors)}
    EMBEDDINGS_FILE.write_text(json.dumps(stored))
    print(f"{len(stored)} vectors written to {EMBEDDINGS_FILE}")


if __name__ == "__main__":
    main()
