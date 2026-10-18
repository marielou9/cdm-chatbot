import pytest

from app.answerer import NO_INFORMATION, ask
from app.knowledge_base import Entry, Hit

QUESTION = "How does a 'Contact' relate to an 'Organization'?"
SUB_QUESTIONS = ["What is a Contact related to?", "How is an Organization connected to other entities?"]
CONTACT = Hit(Entry("banking Contact has these relationships: ...", "Contact", "banking", "relationships"), 0.70)
ORGANIZATION = Hit(Entry("foundationCommon Organization: Top level ...", "Organization", "foundationCommon", "overview"), 0.69)


class FakeLLM:
    """Answers the split prompt with fixed sub-questions and records every prompt."""

    def __init__(self):
        self.prompts = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if prompt.startswith("Split"):
            return "\n".join(SUB_QUESTIONS)
        return "A Contact reaches Organization through BusinessUnit."


def test_each_sub_question_is_searched():
    searched = []

    def search(question):
        searched.append(question)
        return [CONTACT]

    ask(QUESTION, search, FakeLLM())

    assert searched == [QUESTION, *SUB_QUESTIONS]


def test_prompt_holds_context_and_rule():
    llm = FakeLLM()

    answer = ask(QUESTION, lambda question: [CONTACT, ORGANIZATION], llm)

    final_prompt = llm.prompts[-1]
    assert "Answer only from the context below" in final_prompt
    assert CONTACT.entry.text in final_prompt
    assert ORGANIZATION.entry.text in final_prompt
    assert QUESTION in final_prompt
    assert answer.text == "A Contact reaches Organization through BusinessUnit."


def test_no_hits_gives_fixed_answer_without_llm():
    def llm_must_not_be_called(prompt):
        raise AssertionError("the language model was called")

    answer = ask("What attributes does the 'CryptoWallet' entity have?", lambda question: [], llm_must_not_be_called)

    assert answer.text == NO_INFORMATION
    assert answer.sources == []


def test_llm_failure_gives_clear_error():
    def unreachable_llm(prompt):
        raise ConnectionError("429 RESOURCE_EXHAUSTED")

    with pytest.raises(RuntimeError, match="language model is not available.*429"):
        ask(QUESTION, lambda question: [CONTACT], unreachable_llm)


def test_prompt_allows_partial_answers():
    llm = FakeLLM()

    ask(QUESTION, lambda question: [CONTACT], llm)

    assert "If the context only partly answers the question, say what it contains and what is missing." in llm.prompts[-1]


def test_prompt_asks_for_the_exact_entity():
    llm = FakeLLM()

    ask(QUESTION, lambda question: [CONTACT], llm)

    assert "Name the exact entity for every statement." in llm.prompts[-1]
