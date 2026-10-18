import pytest
from fastapi.testclient import TestClient

from app import api
from app.api import app
from app.knowledge_base import Entry, Hit

# one search hit for every question
RELATIONSHIPS = Hit(Entry("banking Account has these relationships: ...", "Account", "banking", "relationships"), 0.73)
QUESTION = "How is an Account related to a Branch?"


def fake_complete(prompt: str) -> str:
    """No sub-questions for the split prompt, a fixed answer otherwise."""

    return "" if prompt.startswith("Split") else "Account refers to Branch through enrollmentBranch."


@pytest.fixture
def client():
    """Return a test client with fake search and fake model, no startup."""

    app.state.search = lambda question: [RELATIONSHIPS]
    app.state.complete = fake_complete
    return TestClient(app)


# ============================================================
# Questions
# ============================================================

def test_question_returns_answer(client):

    response = client.post("/ask", json={"question": QUESTION})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Account refers to Branch through enrollmentBranch.",
        "sources": ["banking Account relationships"],
    }


@pytest.mark.parametrize("question", ["", "   "])
def test_empty_question_returns_422(client, question):

    response = client.post("/ask", json={"question": question})

    assert response.status_code == 422


# ============================================================
# Outside services down
# ============================================================

def test_llm_failure_returns_503(client):

    def unreachable(prompt):
        raise ConnectionError("503 UNAVAILABLE")

    app.state.complete = unreachable
    response = client.post("/ask", json={"question": QUESTION})

    assert response.status_code == 503
    assert "language model is not available" in response.json()["detail"]


def test_embedding_failure_returns_503(client):

    def unreachable(question):
        raise ConnectionError("429 RESOURCE_EXHAUSTED")

    app.state.search = unreachable
    response = client.post("/ask", json={"question": QUESTION})

    assert response.status_code == 503
    assert "search is not available" in response.json()["detail"]


# ============================================================
# Startup
# ============================================================

def test_missing_key_gives_clear_message(monkeypatch):

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # startup runs inside the with block
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        with TestClient(app):
            pass


def test_load_index_uses_stored_vectors(monkeypatch):

    def gemini_must_not_be_called(texts, task_type):
        raise AssertionError("Gemini was called at startup")

    monkeypatch.setattr(api.gemini, "embed", gemini_must_not_be_called)

    # every entry has a stored vector
    assert api.load_index().count() == len(api.build_index_entries())


def test_stale_embeddings_give_clear_error(monkeypatch, tmp_path):

    # empty vector file
    stale = tmp_path / "embeddings.json"
    stale.write_text("{}")
    monkeypatch.setattr(api, "EMBEDDINGS_FILE", stale)

    with pytest.raises(RuntimeError, match="python -m scripts.store_index_embeddings"):
        api.load_index()
