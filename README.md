# CDM Chatbot

A FastAPI service that answers natural-language questions about the Microsoft Common Data Model (CDM), focused on the Banking accelerator and the common objects it builds on. Answers come only from the CDM definitions. If the data does not cover a question, the service says so.

## What you need

- Docker
- A Gemini API key, free from [Google AI Studio](https://aistudio.google.com/apikey)

## Start

```bash
cp .env.example .env          # then put your key into .env
docker build -t cdm-chatbot .
docker run --env-file .env -p 8000:8000 cdm-chatbot
```

The service is ready after a few seconds.

## Ask a question

**In the browser:** open http://localhost:8000/docs, choose `POST /ask`, click "Try it out", type a question and click "Execute".

**In the terminal:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How is an Account related to a Branch?"}'
```

The response holds the answer and the CDM entries it is based on:

```json
{
  "answer": "The banking Account refers to Branch through enrollmentBranch, foreign key enrollmentBranchId. ...",
  "sources": ["banking Account relationships", "banking Branch overview", "..."]
}
```

More questions to try:

- How does a 'Contact' relate to an 'Organization'? (the data has no direct link, the answer says so and names what it does contain)
- What are the core attributes of the 'Account' entity?
- Where do I store a customer's credit limit?
- Which entities are in the Banking model?
- What attributes does the 'CryptoWallet' entity have? (not in the CDM, the service says so)

## Overview

```
question → unknown-entity check → vector search (top 5, similarity ≥ 0.6)
         → nothing found: fixed "no information" answer, no LLM call
         → else: split into ≤ 3 sub-questions → search each → answer only from the found entries
```

**Stack**
- Python 3.14, FastAPI
- Chroma as vector database, embedded and in memory
- Gemini: `gemini-embedding-001` for embeddings, `gemini-3.5-flash-lite` for answers
- Docker

**Data**
- Microsoft Common Data Model: the Dynamics 365 Banking accelerator (24 entities) and the 23 common objects it builds on, such as Organization, BusinessUnit and User, with inheritance resolved.
- Source labels name the layer an entity comes from: `banking` for the accelerator, `crmCommon`, `foundationCommon` and `applicationCommon` for the CDM common objects. That keeps the banking Account and the common Account apart.

**Embedding and retrieval**
- Each entity becomes three entries: an overview, its attributes and its relationships, plus one catalog of all banking entities.
- Relationships are the entity attributes of each entity with their foreign keys, including inherited ones and lookups that can point to several entities.
- Attributes entries are embedded from their field names only, because `gemini-embedding-001` reads at most 2,048 tokens. The language model still reads the full descriptions.
- The vectors are computed once and stored in `data/embeddings.json`, so the service starts without embedding calls.

**Limitations**
- Relationships are listed per entity, outgoing only. Paths over several entities depend on finding each step.
- Fields every Dynamics entity shares, like `owningBusinessUnit`, are not loaded, so Contact → BusinessUnit → Organization is not found.
- Allowed values of code fields are not included.
- The similarity threshold of 0.6 was measured on the example questions.

## Project layout

```
app/cdm.py              load CDM manifests and entity files, resolve inheritance and relationships
app/knowledge_base.py   build the entries, the Chroma index and the search with its checks
app/answerer.py         split questions, merge results, ask Gemini
app/gemini.py           embedding and answer calls
app/api.py              FastAPI endpoint and startup
```

## Development

Requires Python 3.14.

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The tests run offline. They use stored vectors in `tests/testdata/embeddings.json` instead of calling Gemini. They cover CDM parsing with inheritance, entry building, retrieval on the task's example questions, the no-information path and the API's error handling.

When the CDM data or the entry texts change, the stored vectors must be regenerated (needs `GEMINI_API_KEY`):

```bash
python -m scripts.store_index_embeddings    # vectors for the app
python -m scripts.store_test_embeddings     # vectors for the tests
```

## Data

The files in `data/cdm/` are a subset of the [Microsoft Common Data Model](https://github.com/microsoft/CDM) schema documents, © Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Only the Banking accelerator, its supporting entities and their parents are included, unchanged.
