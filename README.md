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

## Overview

**Stack**
- Python 3.14, FastAPI
- Chroma as vector database, embedded and in memory
- Gemini: `gemini-embedding-001` for embeddings, `gemini-3.5-flash-lite` for answers
- Docker

**Data**
- Microsoft Common Data Model, the Dynamics 365 Banking accelerator (24 entities) and the 23 common entities it builds on, with inheritance resolved.

**Embedding and retrieval**
- Each entity becomes three short texts, an overview, its attributes and its relationships, plus one catalog of all banking entities.
- The vectors are computed once and stored in `data/embeddings.json`, so the service starts without embedding calls.
- A question is split into sub-questions, and the answer may only use the entries found for them.
- If a question names an unknown entity or nothing matches closely enough, the answer is a fixed "no information".

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
