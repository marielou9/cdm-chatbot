import json
from pathlib import Path

import pytest

from app.knowledge_base import create_index, search
from scripts.store_test_embeddings import QUESTIONS, build_test_entries

STORED = json.loads((Path(__file__).parent / "testdata" / "embeddings.json").read_text())
THRESHOLD = 0.6


def stored_embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Return the stored Gemini vectors instead of calling Gemini."""
    kind = "documents" if task_type == "RETRIEVAL_DOCUMENT" else "queries"
    missing = [text[:60] for text in texts if text not in STORED[kind]]
    if missing:
        raise KeyError(f"No stored embedding for {missing}, run: python -m scripts.store_test_embeddings")
    return [STORED[kind][text] for text in texts]


@pytest.fixture(scope="module")
def index():
    return create_index(build_test_entries(), stored_embed)


def first_hit(index, question_number):
    hits = search(index, QUESTIONS[question_number - 1], stored_embed, THRESHOLD)
    return hits[0].entry


def test_question_3_finds_banking_account_relationships_first(index):
    entry = first_hit(index, 3)

    assert (entry.layer, entry.entity, entry.kind) == ("banking", "Account", "relationships")


def test_question_4_finds_banking_account_overview_first(index):
    entry = first_hit(index, 4)

    assert (entry.layer, entry.entity, entry.kind) == ("banking", "Account", "overview")


def test_question_1_finds_an_account_attributes_entry_first(index):
    entry = first_hit(index, 1)

    assert (entry.entity, entry.kind) == ("Account", "attributes")


def test_question_7_finds_banking_account_attributes_among_hits(index):
    hits = search(index, QUESTIONS[6], stored_embed, THRESHOLD)

    assert ("banking", "Account", "attributes") in {(h.entry.layer, h.entry.entity, h.entry.kind) for h in hits}


def test_question_8_finds_catalog_first(index):
    entry = first_hit(index, 8)

    assert entry.kind == "catalog"


def test_off_topic_question_returns_no_hits(index):
    assert search(index, QUESTIONS[9], stored_embed, THRESHOLD) == []


@pytest.mark.parametrize("question_number", [6, 9])
def test_unknown_named_entity_returns_no_hits(index, question_number):
    assert search(index, QUESTIONS[question_number - 1], stored_embed, THRESHOLD) == []


def test_apostrophes_are_not_taken_for_quoted_names(index):
    assert search(index, QUESTIONS[10], stored_embed, THRESHOLD) != []


def test_acronyms_are_not_taken_for_entity_names(index):
    assert search(index, QUESTIONS[11], stored_embed, THRESHOLD) != []
