from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class Attribute:
    name: str
    data_type: str = ""
    description: str = ""


@dataclass
class Relationship:
    attribute: str
    target: str
    foreign_key: str = ""


@dataclass
class Entity:
    name: str
    layer: str = ""
    description: str = ""
    extends: str = ""
    attributes: list[Attribute] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)


def load_entities(root: Path, manifest: str) -> list[Entity]:
    """Load every entity listed in a manifest, resolved with what it inherits."""
    manifest_path = root / manifest.lstrip("/")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"CDM manifest not found: {manifest_path}")
    manifest_doc = json.loads(manifest_path.read_text())
    entities = []
    for entry in manifest_doc["entities"]:
        file_name, entity_name = entry["entityPath"].split("/")
        entities.append(_load_entity(root, manifest_path.parent / file_name, entity_name))
    return entities


def _load_entity(root: Path, path: Path, name: str) -> Entity:
    """Build one entity from its file, including what it inherits from its parent."""
    definition = _find_definition(path, name)
    entity = Entity(
        name=name,
        layer=path.parent.name,
        description=definition.get("description", ""),
        attributes=_own_attributes(definition),
        relationships=_own_relationships(definition),
    )
    parent = _load_parent(root, path, definition)
    if parent is not None:
        entity.extends = f"{parent.layer} {parent.name}"
        entity.attributes += parent.attributes
        entity.relationships += parent.relationships
    return entity


def _find_definition(path: Path, name: str) -> dict:
    """Return the definition of the named entity inside a CDM file."""
    document = json.loads(path.read_text())
    return next(d for d in document["definitions"] if d.get("entityName") == name)


def _own_attributes(definition: dict) -> list[Attribute]:
    """Return the plain attributes an entity adds itself, without entity attributes."""
    attributes = []
    for group in definition.get("hasAttributes", []):
        for member in group["attributeGroupReference"]["members"]:
            if "entity" not in member:
                attributes.append(
                    Attribute(member["name"], _data_type(member), member.get("description", ""))
                )
    return attributes


def _own_relationships(definition: dict) -> list[Relationship]:
    """Return the relationships an entity adds itself, one per entity attribute."""
    relationships = []
    for group in definition.get("hasAttributes", []):
        for member in group["attributeGroupReference"]["members"]:
            if "entity" in member:
                foreign_key = (
                    member.get("resolutionGuidance", {})
                    .get("entityByReference", {})
                    .get("foreignKeyAttribute", {})
                    .get("name", "")
                )
                relationships.append(
                    Relationship(member["name"], member["entity"]["entityReference"], foreign_key)
                )
    return relationships


def _load_parent(root: Path, path: Path, definition: dict) -> Entity | None:
    """Load the parent entity, or return None if the entity extends no CDM entity."""
    parent = definition.get("extendsEntity", "")
    if "/" not in parent:
        return None
    moniker, parent_name = parent.split("/")
    parent_path = _resolve_moniker(root, path.parent, moniker)
    return _load_entity(root, parent_path, parent_name)


def _resolve_moniker(root: Path, folder: Path, moniker: str) -> Path:
    """Find the file a moniker points to, using the folder's _allImports.cdm.json."""
    imports = json.loads((folder / "_allImports.cdm.json").read_text())["imports"]
    corpus_path = next(i["corpusPath"] for i in imports if i.get("moniker") == moniker)
    return root / corpus_path.lstrip("/")

def _data_type(member: dict) -> str:
    """Return the data type name, also for types given as an object like listLookup."""
    data_type = member.get("dataType", "")
    if isinstance(data_type, dict):
        data_type = data_type.get("dataTypeReference", "")
    return data_type
