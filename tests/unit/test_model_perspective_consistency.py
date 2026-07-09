"""Structural consistency between model.tmdl / perspectives.tmdl / relationships.tmdl.

Catches the class of bug where a table is renamed / disabled but one of the
three top-level TMDL files still references it. Example caught: C15
(`fact_product_export_situation`) appearing in `perspectives.tmdl` after its
table file was disabled — Fabric framing would fail silently.
"""

from __future__ import annotations

import re
from pathlib import Path

DEF_DIR = (
    Path(__file__).resolve().parents[2]
    / "semantic_model"
    / "itrade_tariff_model.SemanticModel"
    / "definition"
)

_MODEL = DEF_DIR / "model.tmdl"
_PERSPECTIVES = DEF_DIR / "perspectives.tmdl"
_RELATIONSHIPS = DEF_DIR / "relationships.tmdl"


def _model_ref_tables() -> set[str]:
    text = _MODEL.read_text(encoding="utf-8")
    return set(re.findall(r"^ref table (\S+)", text, flags=re.MULTILINE))


def _perspective_tables() -> set[str]:
    text = _PERSPECTIVES.read_text(encoding="utf-8")
    return set(re.findall(r"perspectiveTable (\S+)", text))


def _relationship_tables() -> set[str]:
    text = _RELATIONSHIPS.read_text(encoding="utf-8")
    # Grab table from fromColumn: <table>.<col> and toColumn: <table>.<col>
    pairs = re.findall(r"(?:fromColumn|toColumn):\s*(\S+?)\.", text)
    return set(pairs)


def test_every_perspective_table_is_ref_in_model() -> None:
    model_refs = _model_ref_tables()
    orphans = _perspective_tables() - model_refs
    assert not orphans, (
        f"perspectives.tmdl references tables missing from model.tmdl: "
        f"{sorted(orphans)}. Either add `ref table X` to model.tmdl or "
        f"remove the perspectiveTable entry."
    )


def test_every_relationship_table_is_ref_in_model() -> None:
    model_refs = _model_ref_tables()
    orphans = _relationship_tables() - model_refs
    assert not orphans, (
        f"relationships.tmdl references tables missing from model.tmdl: "
        f"{sorted(orphans)}. Stale relationship will break framing — drop the "
        f"relationship or add the table back to model.tmdl."
    )


def test_model_ref_tables_have_tmdl_files() -> None:
    """Every `ref table X` in model.tmdl must have a tables/X.tmdl file.

    Disabled files (`tables/X.tmdl.disabled_*`) do NOT count — that's the
    exact C15 failure mode we're preventing.
    """
    tables_dir = DEF_DIR / "tables"
    existing = {p.stem for p in tables_dir.glob("*.tmdl") if p.suffix == ".tmdl"}
    missing = _model_ref_tables() - existing
    assert not missing, (
        f"model.tmdl refs tables without a live .tmdl file: {sorted(missing)}. "
        f"Check tables/ for disabled_* suffixes."
    )
