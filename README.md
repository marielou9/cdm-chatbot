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

The response is JSON with two fields, `answer` as Markdown and `sources` as the CDM entries the answer is based on. Shortened example for "What are the core attributes of the 'Account' entity?":

```json
{
  "answer": "The entity `banking Account` has the following attributes:\n\n- `accountId`\n- `name`\n- `accountNumber`\n- `creditLimit`\n- ...",
  "sources": [
    "banking Account overview",
    "banking Account attributes",
    "banking Account relationships",
    "..."
  ]
}
```

To read only the answer with rendered line breaks, pipe it through [jq](https://jqlang.org):

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the core attributes of the Account entity?"}' \
  | jq -r '.answer'
```

Questions to try
- How does a 'Contact' relate to an 'Organization'?
- What are the core attributes of the 'Account' entity?
- Where do I store a customer's credit limit?
- What attributes does the 'CryptoWallet' entity have?

## How it works

### Prepared in the repo

1. **`data/cdm/`** holds an unchanged subset of the Microsoft CDM, the Banking accelerator (24 entities) and the 23 common objects it builds on.
2. **`data/embeddings.json`** holds the vectors of all entries, computed once with Gemini by `scripts/store_index_embeddings.py`, so the service starts without embedding calls.

### At startup

1. **`app/api.py`** checks that `GEMINI_API_KEY` is set and starts building the index.
2. **`app/cdm.py`** reads every entity file and follows the inheritance chain, so the banking Account carries all attributes and relationships of its parent layers.
3. **`app/knowledge_base.py`** turns each entity into an overview, an attributes and a relationships entry and loads them with their stored vectors into an in-memory Chroma index.

### For each question

1. **`app/api.py`** receives `POST /ask` and rejects empty questions.
2. **`app/knowledge_base.py`** stops right away if the question names an entity that is not in the index.
3. **`app/gemini.py`** turns the question into a vector.
4. **`app/knowledge_base.py`** finds the 5 most similar entries and keeps those with a similarity of at least 0.6.
5. **`app/answerer.py`** returns a fixed "no information" answer if nothing is left, without calling the language model.
6. **`app/answerer.py`** lets Gemini split the question into up to 3 sub-questions and searches each one the same way.
7. **`app/gemini.py`** answers from the found entries only, at temperature 0.
8. **`app/api.py`** returns the answer and the entries it is based on as `sources`.

**Stack** Python 3.14, FastAPI, Chroma (embedded), Gemini (`gemini-embedding-001` for vectors, `gemini-3.5-flash-lite` for answers)

## Design

### Parsing

- **Kept** only name, data type and description of each attribute, the trait and resolution metadata of the CDM files is left out.
- **Inheritance** is resolved layer by layer, banking → crmCommon → foundationCommon → applicationCommon, and stops at `CdsStandard`.
- **Relationships** come from attributes that point to another entity, including inherited ones and lookups with several targets.
- **Layer labels** like `banking` or `crmCommon` keep the four `Account` definitions apart.
- **Three entries per entity,** overview, attributes and relationships, plus one catalog of all banking entities.
- **Attributes entries** are embedded from their field names only, because the longest entry is far beyond the embedding model's limit of 2,048 tokens, while the language model still gets the full text.

### Retrieval

- **Top 5** entries per search, set as `MAX_HITS` in `app/knowledge_base.py`.
- **Similarity of at least 0.6,** set as `THRESHOLD` in the same file, measured on the example questions, the lowest one needed 0.64, an off-topic question scored 0.50.
- **Up to 3 sub-questions,** set as `MAX_SUB_QUESTIONS` in `app/answerer.py`, each searched like the full question.
- **Merged results** keep every entry once, at its best score.
- **All three values** can be changed without new embeddings, only the image has to be rebuilt.

## Limitations

- **Shared fields** like `owningBusinessUnit` not loaded, so Contact → BusinessUnit → Organization is not found
- **Relationships** outgoing only
- **Code fields** allowed values not included
- **Threshold** 0.6, measured on the example questions
- **Field origin** not marked per attribute, so a question about what the banking layer adds relies on the field descriptions

## Development

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The tests run offline on stored vectors. They cover CDM parsing, entry building, retrieval on the task's example questions and the API's error handling. `test_search.py` uses real Gemini vectors stored in `tests/testdata/embeddings.json`, `test_answerer.py` uses a fake language model, so no test calls Gemini. After changes to the CDM data or the entry texts, `python -m scripts.store_index_embeddings` and `python -m scripts.store_test_embeddings` regenerate the vectors.

## Data

The files in `data/cdm/` are an unchanged subset of the [Microsoft Common Data Model](https://github.com/microsoft/CDM), © Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
