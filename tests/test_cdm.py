from pathlib import Path

import pytest

from app.cdm import load_entities

TESTDATA = Path(__file__).parent / "testdata" / "cdm"


def test_child_has_own_and_inherited_attributes():
    entities = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")

    child = entities[0]
    assert child.name == "Child"
    assert {a.name for a in child.attributes} == {"c1", "p1", "p2", "p3"}

def test_child_knows_its_layer_parent_and_description():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    assert child.layer == "child"
    assert child.extends == "base Parent"
    assert child.description == "A child entity for tests."


def test_attributes_carry_type_and_description():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    p1 = next(a for a in child.attributes if a.name == "p1")
    assert p1.data_type == "string"
    assert p1.description == "First parent field."


def test_data_type_given_as_object_is_read_by_name():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    p3 = next(a for a in child.attributes if a.name == "p3")
    assert p3.data_type == "listLookup"


def test_entity_attributes_become_relationships_including_inherited():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    found = {(r.attribute, r.target, r.foreign_key) for r in child.relationships}
    assert {("branch", "Branch", "branchId"), ("owner", "User", "ownerId")} <= found


def test_missing_manifest_raises_clear_error():
    with pytest.raises(FileNotFoundError, match="CDM manifest not found"):
        load_entities(TESTDATA, "/core/nowhere/missing.manifest.cdm.json")


def test_manifest_with_absolute_entity_paths():
    entities = load_entities(TESTDATA, "/core/top.manifest.cdm.json")

    assert "Parent" in {e.name for e in entities}


def test_sub_manifests_are_loaded():
    entities = load_entities(TESTDATA, "/core/top.manifest.cdm.json")

    assert {e.name for e in entities} == {"Parent", "Child"}


def test_polymorphic_lookup_becomes_one_relationship_per_option():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    found = {(r.attribute, r.target, r.foreign_key) for r in child.relationships}
    assert {("customer", "Account", "customerId"), ("customer", "Contact", "customerId")} <= found


def test_foreign_key_named_id_gets_attribute_prefix():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    lead = next(r for r in child.relationships if r.attribute == "originatingLead")
    assert lead.foreign_key == "originatingLeadId"


def test_named_attribute_references_are_skipped():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    assert "ownerIdAttribute" not in {a.name for a in child.attributes}


REAL_CDM = Path(__file__).parent.parent / "data" / "cdm"


def test_real_banking_account_is_resolved():
    entities = load_entities(REAL_CDM, "/manifests/bankingAccelerator.manifest.cdm.json")

    account = next(e for e in entities if e.name == "Account" and e.layer == "banking")
    names = {a.name for a in account.attributes}
    assert "annualReviewDate" in names
    assert "name" in names
    assert account.extends == "crmCommon Account"


def test_inherited_attributes_come_first():
    child = load_entities(TESTDATA, "/core/child/child.manifest.cdm.json")[0]

    assert [a.name for a in child.attributes] == ["p1", "p2", "p3", "c1"]
