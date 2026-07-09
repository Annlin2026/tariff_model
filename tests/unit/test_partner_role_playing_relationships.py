"""Verifies the active partner/counterpart → dim_country_partner
relationships land in relationships.tmdl (issue #1 BUG-001; extended by
issue #79 for fact_tariff_rate).

Each fact table that has a partner_code (or source_code / importer_code)
column previously had only an *inactive* relationship to dim_country,
because the active slot was held by reporter_code. This caused
partner-axis visuals to show raw codes instead of country names.

The fix adds a parallel **active** relationship to the role-playing
`dim_country_partner` table for each affected fact, leaving the
inactive counterpart→dim_country relationship in place as a fallback for
existing USERELATIONSHIP DAX measures.
"""

from __future__ import annotations

import re

import pytest

from tests.unit._tmdl_helpers import load_tmdl

# (relationship_name, expected fromColumn)
# Tariff-split scope: this standalone model carries only fact_tariff_rate, so
# the parent repo's market/product/industry rows do not apply here. The policy
# under test (active role relationship to dim_country_partner + inactive
# dim_country fallback preserved) is unchanged.
EXPECTED_PARTNER_ROLE_RELATIONSHIPS: list[tuple[str, str]] = [
    # Issue #79: tariff importer axis (進口國 rows) rides dim_country_partner,
    # freeing dim_country for the exporter axis (出口國 slicer). ADR 0023.
    (
        "fact_tariff_importer_role",
        "fact_tariff_rate.importer_code",
    ),
]


@pytest.fixture(scope="module")
def relationships_text() -> str:
    return load_tmdl("relationships.tmdl")


def _block(text: str, name: str) -> str | None:
    """Return the text of `relationship <name>` block, or None."""
    m = re.search(rf"^relationship\s+{re.escape(name)}\b", text, re.MULTILINE)
    if m is None:
        return None
    start = m.start()
    rest = text[start:]
    next_rel = re.search(r"^\s*$\n^relationship\s+", rest[1:], re.MULTILINE)
    return rest[: 1 + next_rel.start()] if next_rel else rest


@pytest.mark.parametrize(
    "rel_name,from_column",
    EXPECTED_PARTNER_ROLE_RELATIONSHIPS,
    ids=[r for r, _ in EXPECTED_PARTNER_ROLE_RELATIONSHIPS],
)
def test_partner_role_relationship_present_and_active(
    relationships_text: str, rel_name: str, from_column: str
) -> None:
    block = _block(relationships_text, rel_name)
    assert block is not None, f"relationship {rel_name!r} missing"
    assert f"fromColumn: {from_column}" in block, (
        f"{rel_name}: expected fromColumn: {from_column}"
    )
    assert "toColumn: dim_country_partner.country_id" in block, (
        f"{rel_name}: must point to dim_country_partner.country_id"
    )
    assert "isActive: true" in block, (
        f"{rel_name}: must be active — that is the whole point of BUG-001"
    )


def test_existing_inactive_partner_relationships_preserved(
    relationships_text: str,
) -> None:
    """Fallback relationships to dim_country must remain so existing
    USERELATIONSHIP-based measures keep working."""
    for legacy in (
        "fact_tariff_importer",
    ):
        block = _block(relationships_text, legacy)
        assert block is not None, f"legacy relationship {legacy!r} disappeared"
        assert "isActive: false" in block, (
            f"{legacy}: must remain isActive: false to avoid double-active conflict"
        )
