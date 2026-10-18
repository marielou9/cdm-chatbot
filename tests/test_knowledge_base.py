from app.cdm import Attribute, Entity, Relationship
from app.knowledge_base import build_catalog_entry, build_entries

ACCOUNT = Entity(
    name="Account",
    layer="banking",
    description="A company that represents a customer or a potential customer.",
    extends="crmCommon Account",
    attributes=[Attribute("availableLimit", "currency", "Total amount remaining from the credit line.")],
    relationships=[Relationship("enrollmentBranch", "Branch", "enrollmentBranchId")],
)


def test_entity_gives_three_entries():
    entries = build_entries(ACCOUNT)

    assert [e.kind for e in entries] == ["overview", "attributes", "relationships"]
    assert all(e.entity == "Account" and e.layer == "banking" for e in entries)


def test_entry_text_starts_with_layer_label():
    entries = build_entries(ACCOUNT)

    assert all(e.text.startswith("banking Account") for e in entries)


def test_attribute_line_has_name_type_and_description():
    attributes = build_entries(ACCOUNT)[1]

    assert "- availableLimit (currency): Total amount remaining from the credit line." in attributes.text


def test_catalog_entry_lists_all_entities():
    branch = Entity(name="Branch", layer="banking")

    catalog = build_catalog_entry([ACCOUNT, branch])

    assert catalog.kind == "catalog"
    assert catalog.text == "The banking model contains these entities: Account, Branch."
