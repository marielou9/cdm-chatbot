from collections.abc import Callable
from dataclasses import dataclass, field

from app.knowledge_base import Entry, Hit

Search = Callable[[str], list[Hit]]
Complete = Callable[[str], str]

NO_INFORMATION = "The CDM data has no information about this."
MAX_SUB_QUESTIONS = 3
SPLIT_PROMPT = (
    "Split the question into at most {limit} short sub-questions about single CDM entities "
    "or their relationships. Write one sub-question per line and nothing else.\n\nQuestion: {question}"
)
ANSWER_PROMPT = (
    "Answer only from the context below, which describes entities of the Microsoft Common Data Model. "
    "If the context does not contain the answer, say that the CDM data has no information about it. "
    "Do not add entities, attributes or relationships that are not in the context.\n\n"
    "Context:\n{context}\n\nQuestion: {question}"
)


@dataclass
class Answer:
    text: str
    sources: list[Entry] = field(default_factory=list)


def ask(question: str, search: Search, complete: Complete) -> Answer:
    """Answer a question from the CDM entries, searching once per sub-question.

    If the question itself finds nothing, the fixed no-information answer comes back
    without calling the language model.
    """
    hits = search(question)
    if not hits:
        return Answer(NO_INFORMATION)
    llm = _guarded(complete)
    for sub_question in _sub_questions(question, llm):
        hits += search(sub_question)
    sources = _unique_best_first(hits)
    context = "\n\n".join(entry.text for entry in sources)
    return Answer(llm(ANSWER_PROMPT.format(context=context, question=question)), sources)


def _sub_questions(question: str, complete: Complete) -> list[str]:
    """Ask the language model to split the question, one sub-question per line."""
    reply = complete(SPLIT_PROMPT.format(limit=MAX_SUB_QUESTIONS, question=question))
    lines = [line.strip() for line in reply.splitlines()]
    return [line for line in lines if line][:MAX_SUB_QUESTIONS]


def _unique_best_first(hits: list[Hit]) -> list[Entry]:
    """Keep each entry once, at its best score, best first."""
    best = {}
    for hit in hits:
        key = (hit.entry.layer, hit.entry.entity, hit.entry.kind)
        if key not in best or hit.score > best[key].score:
            best[key] = hit
    return [hit.entry for hit in sorted(best.values(), key=lambda hit: hit.score, reverse=True)]


def _guarded(complete: Complete) -> Complete:
    """Wrap the language model so any failure becomes one clear error for the caller."""

    def call(prompt: str) -> str:
        try:
            return complete(prompt)
        except Exception as error:
            raise RuntimeError(f"The language model is not available: {error}") from error

    return call
