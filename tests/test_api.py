import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.knowledge_base import Entry, Hit

RELATIONSHIPS = Hit(Entry("banking Account has these relationships: ...", "Account", "banking", "relationships"), 0.73)


def fake_complete(prompt: str) -> str:
    """No sub-questions for the split prompt, a fixed answer otherwise."""
    return "" if prompt.startswith("Split") else "Account refers to Branch through enrollmentBranch."


@pytest.fixture
def client():
    app.state.search = lambda question: [RELATIONSHIPS]
    app.state.complete = fake_complete
    return TestClient(app)


def test_question_returns_answer(client):
    response = client.post("/ask", json={"question": "How is an Account related to a Branch?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Account refers to Branch through enrollmentBranch.",
        "sources": ["banking Account relationships"],
    }


@pytest.mark.parametrize("question", ["", "   "])
def test_empty_question_returns_422(client, question):
    response = client.post("/ask", json={"question": question})

    assert response.status_code == 422


def test_llm_failure_returns_503(client):
    def unreachable(prompt):
        raise ConnectionError("503 UNAVAILABLE")

    app.state.complete = unreachable
    response = client.post("/ask", json={"question": "How is an Account related to a Branch?"})

    assert response.status_code == 503
    assert "language model is not available" in response.json()["detail"]


def test_missing_key_gives_clear_message(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        with TestClient(app):
            pass
