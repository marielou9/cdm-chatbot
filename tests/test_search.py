"""Retrieval tests on real entries, with stored Gemini vectors instead of live calls."""

import json
from pathlib import Path

import pytest

from app.knowledge_base import THRESHOLD, create_index, search
from scripts.store_test_embeddings import QUESTIONS, build_test_entries

# real Gemini vectors, stored once
STORED = json.loads((Path(__file__).parent / "testdata" / "embeddings.json").read_text())


def stored_embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Return the stored Gemini vectors instead of calling Gemini."""

    kind = "documents" if task_type == "RETRIEVAL_DOCUMENT" else "queries"

    # stale file, clear hint
    missing = [text[:60] for text in texts if text not in STORED[kind]]
    if missing:
        raise KeyError(f"No stored embedding for {missing}, run: python -m scripts.store_test_embeddings")

    return [STORED[kind][text] for text in texts]


@pytest.fixture(scope="module")
def index():
    """Build one index of the test entries for all tests in this file."""

    return create_index(build_test_entries(), stored_embed)


def first_hit(index, question_number):
    """Return the best entry for a numbered test question."""

    hits = search(index, QUESTIONS[question_number - 1], stored_embed, THRESHOLD)
    return hits[0].entry


def hit_labels(index, question_number):
    """Return (layer, entity, kind) of every hit for a numbered test question."""

    hits = search(index, QUESTIONS[question_number - 1], stored_embed, THRESHOLD)
    return {(h.entry.layer, h.entry.entity, h.entry.kind) for h in hits}


# ============================================================
# Test questions with an answer in the data
# ============================================================

def test_question_1_finds_an_account_attributes_entry_first(index):

    entry = first_hit(index, 1)

    assert (entry.entity, entry.kind) == ("Account", "attributes")


def test_question_2_finds_contact_and_organization_entries(index):

    entities = {entity for _, entity, _ in hit_labels(index, 2)}

    assert {"Contact", "Organization"} <= entities


def test_question_3_finds_banking_account_relationships(index):

    assert ("banking", "Account", "relationships") in hit_labels(index, 3)


def test_question_4_finds_banking_account_overview_first(index):

    entry = first_hit(index, 4)

    assert (entry.layer, entry.entity, entry.kind) == ("banking", "Account", "overview")


def test_question_5_finds_branch_relationships_among_hits(index):

    assert ("banking", "Branch", "relationships") in hit_labels(index, 5)


def test_question_7_finds_banking_account_attributes_among_hits(index):

    assert ("banking", "Account", "attributes") in hit_labels(index, 7)


def test_question_8_finds_catalog_first(index):

    entry = first_hit(index, 8)

    assert entry.kind == "catalog"


# ============================================================
# Questions without an answer in the data
# ============================================================

@pytest.mark.parametrize("question_number", [6, 9])
def test_unknown_named_entity_returns_no_hits(index, question_number):

    # CryptoWallet and FHLoan, caught by the name check
    assert search(index, QUESTIONS[question_number - 1], stored_embed, THRESHOLD) == []


def test_off_topic_question_returns_no_hits(index):

    # weather, caught by the threshold
    assert search(index, QUESTIONS[9], stored_embed, THRESHOLD) == []


# ============================================================
# Name check edge cases
# ============================================================

def test_apostrophes_are_not_taken_for_quoted_names(index):

    # "Where's the customer's ..."
    assert search(index, QUESTIONS[10], stored_embed, THRESHOLD) != []


def test_acronyms_are_not_taken_for_entity_names(index):

    # "... in the CDM?"
    assert search(index, QUESTIONS[11], stored_embed, THRESHOLD) != []
