import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import chromadb
from chromadb.api.models.Collection import Collection

from app.cdm import Entity

Embed = Callable[[list[str], str], list[list[float]]]
MAX_HITS = 5
QUOTED_NAME = re.compile(r"'([A-Z]\w*)'")
CAMEL_CASE_NAME = re.compile(r"\b[A-Z][a-z0-9]*[A-Z]\w*\b")


@dataclass
class Entry:
    text: str
    entity: str
    layer: str
    kind: str
    embed_text: str = ""

    def __post_init__(self):
        if not self.embed_text:
            self.embed_text = self.text


def build_entries(entity: Entity) -> list[Entry]:
    """Turn one entity into its overview, attributes and relationships entries."""
    label = f"{entity.layer} {entity.name}"
    return [
        Entry(_overview_text(label, entity), entity.name, entity.layer, "overview"),
        Entry(
            _attributes_text(label, entity),
            entity.name,
            entity.layer,
            "attributes",
            embed_text=_attribute_names_text(label, entity),
        ),
        Entry(_relationships_text(label, entity), entity.name, entity.layer, "relationships"),
    ]


def _overview_text(label: str, entity: Entity) -> str:
    """Describe what the entity is and which entity it extends."""
    text = f"{label}: {entity.description}"
    if entity.extends:
        text += f" It extends {entity.extends}."
    return text


def _attributes_text(label: str, entity: Entity) -> str:
    """List every attribute of the entity, one line each."""
    lines = [f"{label} has these attributes:"]
    for attribute in entity.attributes:
        lines.append(f"- {attribute.name} ({attribute.data_type}): {attribute.description}")
    return "\n".join(lines)


def _attribute_names_text(label: str, entity: Entity) -> str:
    """List only the attribute names, short enough to embed for every entity."""
    names = ", ".join(attribute.name for attribute in entity.attributes)
    return f"{label} has these attributes: {names}"


def _relationships_text(label: str, entity: Entity) -> str:
    """List every relationship of the entity, one line each."""
    lines = [f"{label} has these relationships:"]
    for relationship in entity.relationships:
        lines.append(
            f"- {relationship.attribute} refers to {relationship.target}, "
            f"foreign key {relationship.foreign_key}."
        )
    return "\n".join(lines)


def build_catalog_entry(entities: list[Entity]) -> Entry:
    """List the names of entities from one layer in a single entry, for listing questions."""
    layer = entities[0].layer
    names = ", ".join(entity.name for entity in entities)
    return Entry(f"The {layer} model contains these entities: {names}.", "", layer, "catalog")


@dataclass
class Hit:
    entry: Entry
    score: float


def create_index(entries: list[Entry], embed: Embed) -> Collection:
    """Embed the entries and store them in a new in-memory Chroma collection using cosine distance."""
    client = chromadb.EphemeralClient(settings=chromadb.config.Settings(anonymized_telemetry=False))
    collection = client.create_collection(
        name=f"cdm-{uuid.uuid4().hex}", configuration={"hnsw": {"space": "cosine"}}
    )
    collection.add(
        ids=[str(number) for number in range(len(entries))],
        embeddings=embed([entry.embed_text for entry in entries], "RETRIEVAL_DOCUMENT"),
        documents=[entry.text for entry in entries],
        metadatas=[
            {"entity": e.entity, "layer": e.layer, "kind": e.kind, "embed_text": e.embed_text}
            for e in entries
        ],
    )
    return collection


def search(index: Collection, question: str, embed: Embed, threshold: float) -> list[Hit]:
    """Return up to five entries similar to the question, best first, none below the threshold.

    A question naming an entity that is not in the index gets no hits at all.
    """
    if _names_unknown_entity(index, question):
        return []
    result = index.query(query_embeddings=embed([question], "RETRIEVAL_QUERY"), n_results=MAX_HITS)
    hits = []
    for text, metadata, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        score = 1 - distance
        if score >= threshold:
            entry = Entry(text, metadata["entity"], metadata["layer"], metadata["kind"], metadata["embed_text"])
            hits.append(Hit(entry, score))
    return hits


def _names_unknown_entity(index: Collection, question: str) -> bool:
    """Tell whether the question names an entity, quoted or in CamelCase, that the index does not know."""
    known = {metadata["entity"].lower() for metadata in index.get(include=["metadatas"])["metadatas"]}
    candidates = set(QUOTED_NAME.findall(question)) | set(CAMEL_CASE_NAME.findall(question))
    return any(candidate.lower() not in known for candidate in candidates)
