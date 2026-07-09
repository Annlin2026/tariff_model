import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEF = REPO_ROOT / "semantic_model" / "itrade_tariff_model.SemanticModel" / "definition"


def test_tariff_relationships_have_expected_topology():
    """Assert the 5 tariff relationships exist with correct active/inactive
    topology, scoped to fact_tariff_* so later phases adding non-tariff
    relationships don't break this test (P2a Iter 14.5 rescoping).

    Original P3 count was 4 (importer, exporter, hs, type); P2a Iter 2 added
    fact_tariff_time (clearing ADR 0010's pending row). Issue #79 rewired the
    country roles to match the shipped report UX (ADR 0023): dim_country is
    the exporter axis (出口國 slicer), dim_country_partner the importer axis
    (進口國 rows) — so fact_tariff_exporter flipped active,
    fact_tariff_importer flipped inactive (USERELATIONSHIP fallback), and
    fact_tariff_importer_role (→ dim_country_partner) was added.

    2026-07-09 split-model change: fact_tariff_type dropped together with
    dim_tariff_detail (zero report-layer references; user decision).
    """
    text = (DEF / "relationships.tmdl").read_text(encoding="utf-8")
    # Only line-start `relationship fact_tariff_*` declarations.
    tariff_decls = re.findall(r"^relationship\s+(fact_tariff_\w+)", text, flags=re.MULTILINE)
    assert set(tariff_decls) == {
        "fact_tariff_importer",
        "fact_tariff_exporter",
        "fact_tariff_importer_role",
        "fact_tariff_hs",
        "fact_tariff_time",
    }, f"unexpected tariff relationship set: {sorted(tariff_decls)}"

    # Extract each tariff relationship block and check active/inactive.
    def _block(name: str) -> str:
        m = re.search(
            rf"relationship {re.escape(name)}\n.*?(?=\nrelationship |\Z)",
            text,
            re.DOTALL,
        )
        assert m is not None, f"relationship {name} block not found"
        return m.group()

    # Exactly one inactive tariff relationship: fact_tariff_importer
    # (legacy fallback for USERELATIONSHIP, per the model-wide pattern).
    inactive = [n for n in tariff_decls if "isActive: false" in _block(n)]
    assert inactive == ["fact_tariff_importer"], (
        f"expected fact_tariff_importer as the only inactive tariff rel; "
        f"actual inactive tariff rels: {inactive}"
    )

    # The other four tariff rels are active.
    active = [n for n in tariff_decls if "isActive: true" in _block(n)]
    assert set(active) == {
        "fact_tariff_exporter",
        "fact_tariff_importer_role",
        "fact_tariff_hs",
        "fact_tariff_time",
    }, f"expected 4 active tariff rels; actual: {sorted(active)}"

    # Role wiring: exporter axis on dim_country, importer axis on the
    # role-playing dim_country_partner (issue #79 root fix).
    assert "toColumn: dim_country.country_id" in _block("fact_tariff_exporter")
    imp_role = _block("fact_tariff_importer_role")
    assert "fromColumn: fact_tariff_rate.importer_code" in imp_role
    assert "toColumn: dim_country_partner.country_id" in imp_role


def test_perspective_file_names_tariff():
    text = (DEF / "perspectives.tmdl").read_text(encoding="utf-8")
    assert "perspective Tariff" in text
    for needed in ("fact_tariff_rate", "dim_country", "dim_country_partner",
                   "dim_hs_code"):
        assert needed in text
    assert "dim_tariff_detail" not in text, (
        "dim_tariff_detail was removed from the split model (2026-07-09)"
    )


def test_model_refs_relationships_and_perspectives():
    """Fabric auto-discovers relationships.tmdl + perspectives.tmdl from the
    definition/ folder; explicit `ref relationships` / `ref perspectives` at
    model.tmdl level causes TMDL Format Error 'UnsupportedObjectType'
    (confirmed via fabric-cicd deploy 2026-04-22). Verify the files exist
    and have content instead of the stale ref-line check.
    """
    rels = (DEF / "relationships.tmdl").read_text(encoding="utf-8")
    perss = (DEF / "perspectives.tmdl").read_text(encoding="utf-8")
    assert "relationship " in rels, "relationships.tmdl must contain relationships"
    assert "perspective " in perss, "perspectives.tmdl must contain perspectives"
