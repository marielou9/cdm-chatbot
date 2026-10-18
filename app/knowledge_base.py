from dataclasses import dataclass

from app.cdm import Entity


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
