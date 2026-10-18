import json
import os
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Annotated

from chromadb.api.models.Collection import Collection
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, StringConstraints

from app import gemini
from app.answerer import ask
from app.cdm import load_entities
from app.knowledge_base import THRESHOLD, Entry, build_catalog_entry, build_entries, create_index, search

# CDM data and stored vectors
CDM_ROOT = Path(__file__).parent.parent / "data" / "cdm"
MANIFEST = "/manifests/bankingAccelerator.manifest.cdm.json"
EMBEDDINGS_FILE = Path(__file__).parent.parent / "data" / "embeddings.json"


def build_index_entries() -> list[Entry]:
    """Load the CDM Banking scope and turn it into entries, plus the banking catalog."""

    # parse the CDM files
    entities = load_entities(CDM_ROOT, MANIFEST)

    # three entries per entity, plus the catalog
    entries = [entry for entity in entities for entry in build_entries(entity)]
    entries.append(build_catalog_entry([entity for entity in entities if entity.layer == "banking"]))

    return entries


def load_index() -> Collection:
    """Build the index from the stored entry vectors, without calling Gemini."""

    stored = json.loads(EMBEDDINGS_FILE.read_text()) if EMBEDDINGS_FILE.is_file() else {}

    def stored_embed(texts: list[str], task_type: str) -> list[list[float]]:
        """Return the stored vectors, raising RuntimeError if any text has none."""

        # stale file, clear hint
        missing = [text for text in texts if text not in stored]
        if missing:
            raise RuntimeError(
                f"{len(missing)} entries have no stored vector, "
                "run: python -m scripts.store_index_embeddings"
            )

        return [stored[text] for text in texts]

    return create_index(build_index_entries(), stored_embed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check the key and build the index once, when the server starts."""

    # key needed for questions
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")

    # search with the index, answers from Gemini
    app.state.search = partial(search, load_index(), embed=gemini.embed, threshold=THRESHOLD)
    app.state.complete = gemini.complete

    yield


app = FastAPI(title="CDM Chatbot", lifespan=lifespan)


class Question(BaseModel):
    """Carry the question text, at least one character after trimming spaces."""

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnswerResponse(BaseModel):
    """Carry the answer and its sources as "layer entity kind" labels."""

    answer: str
    sources: list[str]


@app.post("/ask")
def ask_question(body: Question, request: Request) -> AnswerResponse:
    """Answer a natural-language question about the CDM Banking model."""

    # outside service down, 503
    try:
        answer = ask(body.question, request.app.state.search, request.app.state.complete)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    # sources as short labels
    sources = [" ".join(part for part in (e.layer, e.entity, e.kind) if part) for e in answer.sources]
    return AnswerResponse(answer=answer.text, sources=sources)
