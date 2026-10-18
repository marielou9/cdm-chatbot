# CDM Chatbot

A FastAPI service that answers questions about the Microsoft Common Data Model (CDM). It covers the Dynamics 365 Banking accelerator and the common objects it builds on, and it answers only from the CDM definitions.

## Start

You need Docker and a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cp .env.example .env    # add your key
docker build -t cdm-chatbot .
docker run --env-file .env -p 8000:8000 cdm-chatbot
```

## Ask a question

Open http://localhost:8000/docs, choose `POST /ask` and click "Try it out". In the terminal it works with curl.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How is an Account related to a Branch?"}'
```

The response contains the answer and the CDM entries it is based on, for example `"sources": ["banking Account relationships", ...]`.

Questions to try
- How does a 'Contact' relate to an 'Organization'?
- What are the core attributes of the 'Account' entity?
- Where do I store a customer's credit limit?
- What attributes does the 'CryptoWallet' entity have?

## How it works

```
question → unknown-entity check → vector search (top 5, similarity ≥ 0.6)
         → nothing found → fixed "no information" answer
         → otherwise → up to 3 sub-questions → search each → answer from the found entries only
```

- **Stack** Python 3.14, FastAPI, Chroma (embedded), Gemini (`gemini-embedding-001`, `gemini-3.5-flash-lite`)
- **Data** Banking accelerator (24 entities) + 23 common objects, inheritance resolved, layer labels like `banking`, `crmCommon`
- **Entries** overview, attributes and relationships per entity, plus one banking catalog
- **Embedding** attributes entries from field names only, 2,048-token model limit
- **Relationships** foreign keys, incl. inherited ones and lookups with several targets
- **Startup** stored vectors in `data/embeddings.json`, no embedding calls

## Limitations

- **Shared fields** like `owningBusinessUnit` not loaded, so Contact → BusinessUnit → Organization is not found
- **Relationships** outgoing only
- **Code fields** allowed values not included
- **Threshold** 0.6, measured on the example questions

## Project layout

```
app/cdm.py              loads the CDM files, resolves inheritance and relationships
app/knowledge_base.py   builds the entries, the Chroma index and the search
app/answerer.py         splits questions, merges results, asks Gemini
app/gemini.py           embedding and answer calls
app/api.py              FastAPI endpoint and startup
```

## Development

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The tests run offline on stored vectors. They cover CDM parsing, entry building, retrieval on the task's example questions and the API's error handling. After changes to the CDM data or the entry texts, `python -m scripts.store_index_embeddings` and `python -m scripts.store_test_embeddings` regenerate the vectors.

## Data

The files in `data/cdm/` are an unchanged subset of the [Microsoft Common Data Model](https://github.com/microsoft/CDM), © Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
