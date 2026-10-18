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

- What are the core attributes of the 'Account' entity?
- Where do I store a customer's credit limit?
- Which entities are in the Banking model?
- What attributes does the 'CryptoWallet' entity have? (not in the CDM, the service says so)

## How it works

1. **Load,** `app/cdm.py` reads the CDM manifests and entity files and resolves inheritance (`extendsEntity`) and relationships.
2. **Entries,** `app/knowledge_base.py` turns every entity into three short texts: an overview, its attributes and its relationships, plus one catalog entry listing all banking entities.
3. **Index,** the entries go into an in-memory Chroma collection, using vectors from `gemini-embedding-001` that are computed once and stored in `data/embeddings.json`.
4. **Search,** a question that names an unknown entity gets no results. Otherwise the closest entries above a similarity threshold are returned.
5. **Answer,** `app/answerer.py` searches the full question first. If nothing is found, it returns a fixed "no information" answer without calling Gemini. Otherwise Gemini splits the question into up to three sub-questions, each is searched, and Gemini answers only from the found entries.

## Development

Requires Python 3.14.

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The tests run offline. They use stored vectors in `tests/testdata/embeddings.json` instead of calling Gemini.

When the CDM data or the entry texts change, the stored vectors must be regenerated (needs `GEMINI_API_KEY`):

```bash
python -m scripts.store_index_embeddings    # vectors for the app
python -m scripts.store_test_embeddings     # vectors for the tests
```

## Data

The files in `data/cdm/` are a subset of the [Microsoft Common Data Model](https://github.com/microsoft/CDM) schema documents, © Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Only the Banking accelerator, its supporting entities and their parents are included, unchanged.
