"""Tests for building entries and the catalog from entities."""

import pytest

from app.cdm import Attribute, Entity, Relationship
from app.knowledge_base import build_catalog_entry, build_entries

# banking Account with one field and one link
ACCOUNT = Entity(
    name="Account",
    layer="banking",
    description="A company that represents a customer or a potential customer.",
    extends="crmCommon Account",
    attributes=[Attribute("availableLimit", "currency", "Total amount remaining from the credit line.")],
    relationships=[Relationship("enrollmentBranch", "Branch", "enrollmentBranchId")],
)


# ============================================================
# Entries per entity
# ============================================================

def test_entity_gives_three_entries():

    entries = build_entries(ACCOUNT)

    # overview, attributes, relationships, all for banking Account
    assert [e.kind for e in entries] == ["overview", "attributes", "relationships"]
    assert all(e.entity == "Account" and e.layer == "banking" for e in entries)


def test_entry_text_starts_with_layer_label():

    entries = build_entries(ACCOUNT)

    # label keeps the twins apart
    assert all(e.text.startswith("banking Account") for e in entries)


def test_attribute_line_has_name_type_and_description():

    attributes = build_entries(ACCOUNT)[1]

    assert "- availableLimit (currency): Total amount remaining from the credit line." in attributes.text


def test_attributes_entry_embeds_only_names():

    attributes = build_entries(ACCOUNT)[1]

    # vector from names, model reads the full text
    assert attributes.embed_text == "banking Account has these attributes: availableLimit"
    assert "Total amount remaining" in attributes.text


def test_overview_without_description_has_no_double_space():

    entity = Entity(name="Account", layer="crmCommon", extends="foundationCommon Account")

    overview = build_entries(entity)[0]

    assert overview.text == "crmCommon Account: It extends foundationCommon Account."


# ============================================================
# Catalog
# ============================================================

def test_catalog_entry_lists_all_entities():

    branch = Entity(name="Branch", layer="banking")

    catalog = build_catalog_entry([ACCOUNT, branch])

    assert catalog.kind == "catalog"
    assert catalog.text == "The banking model contains these entities: Account, Branch."


def test_catalog_entry_needs_entities():

    with pytest.raises(ValueError, match="at least one entity"):
        build_catalog_entry([])
