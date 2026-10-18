from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class Attribute:
    """Describe one plain field of an entity.

    name: the field name, like annualReviewDate.
    data_type: the CDM data type, like dateTime or listLookup.
    description: the CDM description text, empty if the file has none.
    """

    name: str
    data_type: str = ""
    description: str = ""


@dataclass
class Relationship:
    """Describe one link from an entity to another entity.

    attribute: the entity attribute holding the link, like enrollmentBranch.
    target: the entity the link points to, like Branch.
    foreign_key: the field storing the target's id, like enrollmentBranchId.
    """

    attribute: str
    target: str
    foreign_key: str = ""


@dataclass
class Entity:
    """Hold one CDM entity with everything it inherits.

    name: the entity name, like Account.
    layer: the folder the entity file sits in, like banking or crmCommon.
    description: the CDM description text.
    extends: layer and name of the parent, like "crmCommon Account", empty without a CDM parent.
    attributes: plain fields, inherited ones first.
    relationships: links to other entities, own and inherited.
    """

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
        file_name, entity_name = entry["entityPath"].rsplit("/", 1)
        entity_path = _resolve_path(root, manifest_path.parent, file_name)
        entities.append(_load_entity(root, entity_path, entity_name))
    for sub_manifest in manifest_doc.get("subManifests", []):
        entities += load_entities(root, sub_manifest["definition"])
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
        entity.attributes = parent.attributes + entity.attributes
        entity.relationships += parent.relationships
    return entity


def _find_definition(path: Path, name: str) -> dict:
    """Return the definition of the named entity inside a CDM file.

    Raises ValueError if the file has no entity with that name.
    """
    document = json.loads(path.read_text())
    definition = next((d for d in document["definitions"] if d.get("entityName") == name), None)
    if definition is None:
        raise ValueError(f"Entity '{name}' not found in {path}")
    return definition


def _own_attributes(definition: dict) -> list[Attribute]:
    """Return the plain attributes an entity adds itself, without entity attributes."""
    attributes = []
    for member in _members(definition):
        if "entity" not in member:
            attributes.append(
                Attribute(member["name"], _data_type(member), member.get("description", ""))
            )
    return attributes


def _own_relationships(definition: dict) -> list[Relationship]:
    """Return the relationships an entity adds itself, from its entity attributes."""
    relationships = []
    for member in _members(definition):
        if "entity" in member:
            relationships += _relationships_of(member)
    return relationships


def _relationships_of(member: dict) -> list[Relationship]:
    """Return one relationship, or one per option if the target can be several entities."""
    name = member["name"]
    reference = member["entity"]["entityReference"]
    if isinstance(reference, dict):
        relationships = [
            Relationship(name, option["entity"]["entityReference"], f"{name}Id")
            for option in reference.get("hasAttributes", [])
        ]
    else:
        foreign_key = (
            member.get("resolutionGuidance", {})
            .get("entityByReference", {})
            .get("foreignKeyAttribute", {})
            .get("name", "")
        )
        if foreign_key == "id":
            foreign_key = f"{name}Id"
        relationships = [Relationship(name, reference, foreign_key)]
    return relationships


def _members(definition: dict) -> list[dict]:
    """Return the described attributes of an entity, skipping attributes given only by name."""
    members = []
    for group in definition.get("hasAttributes", []):
        for member in group["attributeGroupReference"]["members"]:
            if isinstance(member, dict):
                members.append(member)
    return members


def _load_parent(root: Path, path: Path, definition: dict) -> Entity | None:
    """Load the parent entity, or return None if the entity extends no CDM entity."""
    parent = definition.get("extendsEntity", "")
    if "/" not in parent:
        return None
    moniker, parent_name = parent.split("/")
    parent_path = _resolve_moniker(root, path.parent, moniker)
    return _load_entity(root, parent_path, parent_name)


def _resolve_moniker(root: Path, folder: Path, moniker: str) -> Path:
    """Find the file a moniker points to, using the folder's _allImports.cdm.json.

    Raises ValueError if the folder's imports do not define the moniker.
    """
    imports = json.loads((folder / "_allImports.cdm.json").read_text())["imports"]
    corpus_path = next((i["corpusPath"] for i in imports if i.get("moniker") == moniker), None)
    if corpus_path is None:
        raise ValueError(f"Moniker '{moniker}' not found in {folder / '_allImports.cdm.json'}")
    return _resolve_path(root, folder, corpus_path)


def _data_type(member: dict) -> str:
    """Return the data type name, also for types given as an object like listLookup."""
    data_type = member.get("dataType", "")
    if isinstance(data_type, dict):
        data_type = data_type.get("dataTypeReference", "")
    return data_type


def _resolve_path(root: Path, folder: Path, corpus_path: str) -> Path:
    """Turn a CDM path into a file path, absolute ones start at the root, others at the folder."""
    if corpus_path.startswith("/"):
        return root / corpus_path.lstrip("/")
    return folder / corpus_path
