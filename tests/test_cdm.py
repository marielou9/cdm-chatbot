"""Tests for loading CDM files, inheritance, relationships and errors."""

from pathlib import Path

import pytest

from app.cdm import load_entities

# hand-made CDM sample and the real CDM subset
TESTDATA = Path(__file__).parent / "testdata" / "cdm"
REAL_CDM = Path(__file__).parent.parent / "data" / "cdm"

# manifest with Child, which extends Parent
CHILD_MANIFEST = "/core/child/child.manifest.cdm.json"


# ============================================================
# Attributes and inheritance
# ============================================================

def test_child_has_own_and_inherited_attributes():

    # load
    entities = load_entities(TESTDATA, CHILD_MANIFEST)

    # own c1 plus inherited p1, p2, p3
    child = entities[0]
    assert child.name == "Child"
    assert {a.name for a in child.attributes} == {"c1", "p1", "p2", "p3"}


def test_inherited_attributes_come_first():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # parent fields before own fields
    assert [a.name for a in child.attributes] == ["p1", "p2", "p3", "c1"]


def test_child_knows_its_layer_parent_and_description():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # layer is the folder name
    assert child.layer == "child"
    assert child.extends == "base Parent"
    assert child.description == "A child entity for tests."


def test_attributes_carry_type_and_description():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # inherited field keeps its type and text
    p1 = next(a for a in child.attributes if a.name == "p1")
    assert p1.data_type == "string"
    assert p1.description == "First parent field."


def test_data_type_given_as_object_is_read_by_name():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # listLookup comes as an object
    p3 = next(a for a in child.attributes if a.name == "p3")
    assert p3.data_type == "listLookup"


def test_named_attribute_references_are_skipped():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # "ownerIdAttribute" is only a name in the file
    assert "ownerIdAttribute" not in {a.name for a in child.attributes}


# ============================================================
# Relationships
# ============================================================

def test_entity_attributes_become_relationships_including_inherited():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # own branch plus inherited owner
    found = {(r.attribute, r.target, r.foreign_key) for r in child.relationships}
    assert {("branch", "Branch", "branchId"), ("owner", "User", "ownerId")} <= found


def test_polymorphic_lookup_becomes_one_relationship_per_option():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # customer can be Account or Contact
    found = {(r.attribute, r.target, r.foreign_key) for r in child.relationships}
    assert {("customer", "Account", "customerId"), ("customer", "Contact", "customerId")} <= found


def test_foreign_key_named_id_gets_attribute_prefix():

    child = load_entities(TESTDATA, CHILD_MANIFEST)[0]

    # file says "id", result says originatingLeadId
    lead = next(r for r in child.relationships if r.attribute == "originatingLead")
    assert lead.foreign_key == "originatingLeadId"


# ============================================================
# Manifests
# ============================================================

def test_manifest_with_absolute_entity_paths():

    # top manifest lists Parent with an absolute path
    entities = load_entities(TESTDATA, "/core/top.manifest.cdm.json")

    assert "Parent" in {e.name for e in entities}


def test_sub_manifests_are_loaded():

    # top manifest points to the child manifest
    entities = load_entities(TESTDATA, "/core/top.manifest.cdm.json")

    assert {e.name for e in entities} == {"Parent", "Child"}


# ============================================================
# Errors
# ============================================================

def test_missing_manifest_raises_clear_error():

    with pytest.raises(FileNotFoundError, match="CDM manifest not found"):
        load_entities(TESTDATA, "/core/nowhere/missing.manifest.cdm.json")


def test_missing_entity_in_file_raises_clear_error():

    # manifest lists Ghost, the file has only Child
    with pytest.raises(ValueError, match="Entity 'Ghost' not found"):
        load_entities(TESTDATA, "/core/child/ghost.manifest.cdm.json")


def test_unknown_moniker_raises_clear_error():

    # Orphan extends base_Missing, which no import defines
    with pytest.raises(ValueError, match="Moniker 'base_Missing' not found"):
        load_entities(TESTDATA, "/core/child/orphan.manifest.cdm.json")


# ============================================================
# Real CDM data
# ============================================================

def test_real_banking_account_is_resolved():

    # load the real banking scope
    entities = load_entities(REAL_CDM, "/manifests/bankingAccelerator.manifest.cdm.json")
    account = next(e for e in entities if e.name == "Account" and e.layer == "banking")

    # own banking field, inherited common field, parent
    names = {a.name for a in account.attributes}
    assert "annualReviewDate" in names
    assert "name" in names
    assert account.extends == "crmCommon Account"
