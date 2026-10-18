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
from app.knowledge_base import build_catalog_entry, build_entries, create_index, search

CDM_ROOT = Path(__file__).parent.parent / "data" / "cdm"
MANIFEST = "/manifests/bankingAccelerator.manifest.cdm.json"
THRESHOLD = 0.6


def load_index() -> Collection:
    """Load the CDM Banking scope, turn it into entries and embed them into a new index."""
    entities = load_entities(CDM_ROOT, MANIFEST)
    entries = [entry for entity in entities for entry in build_entries(entity)]
    entries.append(build_catalog_entry([entity for entity in entities if entity.layer == "banking"]))
    return create_index(entries, gemini.embed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check the key and build the index once, when the server starts."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    app.state.search = partial(search, load_index(), embed=gemini.embed, threshold=THRESHOLD)
    app.state.complete = gemini.complete
    yield


app = FastAPI(title="CDM Chatbot", lifespan=lifespan)


class Question(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]


@app.post("/ask")
def ask_question(body: Question, request: Request) -> AnswerResponse:
    """Answer a natural-language question about the CDM Banking model."""
    try:
        answer = ask(body.question, request.app.state.search, request.app.state.complete)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    sources = [" ".join(part for part in (e.layer, e.entity, e.kind) if part) for e in answer.sources]
    return AnswerResponse(answer=answer.text, sources=sources)
