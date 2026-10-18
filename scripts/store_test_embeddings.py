"""Embed the test entries and test questions once, so retrieval tests run offline."""

import json
from pathlib import Path

from app.cdm import load_entities
from app.gemini import embed
from app.knowledge_base import Entry, build_catalog_entry, build_entries

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "tests" / "testdata" / "embeddings.json"

TEST_ENTITIES = [
    ("banking", "Account"),
    ("crmCommon", "Account"),
    ("banking", "Branch"),
    ("banking", "Bank"),
    ("banking", "Contact"),
    ("foundationCommon", "Organization"),
    ("applicationCommon", "BusinessUnit"),
]

QUESTIONS = [
    "What are the core attributes of the 'Account' entity?",
    "How does a 'Contact' relate to an 'Organization'?",
    "How is an Account related to a Branch?",
    "Which entity does the banking Account extend?",
    "Which bank does a Branch belong to?",
    "What attributes does the 'CryptoWallet' entity have?",
    "Where do I store a customer's credit limit?",
    "Which entities are in the Banking model?",
    "What attributes does the 'FHLoan' entity have?",
    "What is the weather in Hamburg today?",
    "Where's the customer's credit limit stored?",
    "What is the definition of a 'Contact' in the CDM?",
]


def build_test_entries() -> list[Entry]:
    """Build the entries of the test entities plus the banking catalog from the real data."""
    entities = load_entities(ROOT / "data" / "cdm", "/manifests/bankingAccelerator.manifest.cdm.json")
    chosen = [e for e in entities if (e.layer, e.name) in TEST_ENTITIES]
    entries = [entry for entity in chosen for entry in build_entries(entity)]
    entries.append(build_catalog_entry([e for e in entities if e.layer == "banking"]))
    return entries


def main():
    entries = build_test_entries()
    documents = [entry.embed_text for entry in entries]
    stored = {
        "documents": dict(zip(documents, _rounded(embed(documents, "RETRIEVAL_DOCUMENT")))),
        "queries": dict(zip(QUESTIONS, _rounded(embed(QUESTIONS, "RETRIEVAL_QUERY")))),
    }
    OUTPUT.write_text(json.dumps(stored))
    print(f"{len(documents)} documents and {len(QUESTIONS)} questions written to {OUTPUT}")


def _rounded(vectors: list[list[float]]) -> list[list[float]]:
    """Round to 5 digits to keep the file small."""
    return [[round(x, 5) for x in vector] for vector in vectors]


if __name__ == "__main__":
    main()
