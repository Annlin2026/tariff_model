"""Golden CSV vs DAX result comparison framework.

P0 delivers a working stub with:
  - CSV loader (polars)
  - DAX-result → DataFrame comparator (polars.assert_frame_equal with tolerance)
  - Column rename helper that reads `semantic_model/translations/zh-TW.json`

P2a first uses this for real. P3 uses it for Tariff golden CSV.

Research anchor: polars frame_equal_with_tolerance for numeric comparison.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl


class GoldenMismatchError(AssertionError):
    """Raised when DAX result differs from golden CSV beyond tolerance."""


def load_golden_csv(path: Path) -> pl.DataFrame:
    """Load a golden CSV with Chinese headers as a polars DataFrame."""
    return pl.read_csv(path, encoding="utf-8", infer_schema_length=10_000)


def _strip_qualifier(target: str) -> str:
    """Strip `table.` or `table:` qualifier so bare column name matches DAX result.

    DAX SUMMARIZECOLUMNS returns bare column names (e.g. `country_name_zh`) and
    measures keep their quoted-string names (e.g. `Global Import Value (K USD)`).
    The zh-TW mapping stores targets in qualified form (`dim_country.country_name_zh`,
    `fact_tariff_rate:Avg Tariff Rate %`) so this helper normalises to bare names.
    Resolves ADR 0011 Known Debt #1.
    """
    for sep in (":", "."):
        if sep in target:
            return target.rsplit(sep, 1)[-1]
    return target


def rename_golden_to_model(
    df: pl.DataFrame,
    mapping: dict[str, str],
    *,
    strip_qualifier: bool = True,
) -> pl.DataFrame:
    """Rename Chinese CSV columns to model column names using mapping.

    With ``strip_qualifier=True`` (default), qualifiers like ``dim_country.`` and
    ``fact_tariff_rate:`` are stripped so renamed columns match the bare column
    names returned by DAX ``SUMMARIZECOLUMNS``. Pass ``strip_qualifier=False`` to
    preserve the qualified form (legacy behavior).

    Collision handling: when two source keys map to the same target (after any
    stripping), the SECOND mapping is skipped to avoid polars DuplicateError and
    a stderr warning is emitted. Role-playing collisions (e.g. 進口國 + 出口國 both
    → country_name_zh) are resolved at the DAX layer via USERELATIONSHIP.
    """
    import sys
    applied: dict[str, str] = {}
    for src, tgt in mapping.items():
        if src not in df.columns:
            continue
        resolved = _strip_qualifier(tgt) if strip_qualifier else tgt
        if resolved in applied.values() or resolved in df.columns:
            print(
                f"rename_golden_to_model: skipping {src!r} -> {resolved!r} "
                f"(target already taken; likely role-playing collision)",
                file=sys.stderr,
            )
            continue
        applied[src] = resolved
    return df.rename(applied)


def compare_frames(
    actual: pl.DataFrame,
    expected: pl.DataFrame,
    tolerance: float = 0.01,
    sort_by: list[str] | None = None,
) -> None:
    """Assert actual ≈ expected within numeric tolerance.

    Caller must pass `sort_by` or pre-sort both frames — row comparison is
    position-sensitive. DAX `EVALUATE` without `ORDER BY` is non-deterministic.

    Null handling: nulls must appear in identical row positions on both sides.
    A null on one side and a real number on the other raises GoldenMismatchError.

    Raises GoldenMismatchError with row/col diff on failure.
    """
    if sort_by:
        actual = actual.sort(sort_by)
        expected = expected.sort(sort_by)

    # Column presence first (more actionable than shape mismatch).
    missing_cols = [c for c in expected.columns if c not in actual.columns]
    if missing_cols:
        raise GoldenMismatchError(
            f"columns missing in actual: {missing_cols}. "
            f"Did you forget to apply rename_golden_to_model()?"
        )

    if actual.shape != expected.shape:
        raise GoldenMismatchError(
            f"shape mismatch: actual={actual.shape} vs expected={expected.shape}"
        )

    for col in expected.columns:
        exp_col = expected[col]
        act_col = actual[col]
        if exp_col.dtype.is_numeric() and act_col.dtype.is_numeric():
            # Null asymmetry: nulls must appear in the same positions on both sides.
            null_diff = act_col.is_null() != exp_col.is_null()
            if null_diff.any():
                idx = int(null_diff.arg_true().item(0))
                raise GoldenMismatchError(
                    f"null-position mismatch in {col!r} at row {idx}: "
                    f"actual_null={bool(act_col.is_null()[idx])}, "
                    f"expected_null={bool(exp_col.is_null()[idx])}"
                )
            # Both non-null: compare with tolerance.
            diffs = (act_col - exp_col).abs()
            # After the null-position check above, any remaining row-wise null in
            # `diffs` means both sides are null → treat as match (fill 0).
            diffs = diffs.fill_null(0.0)
            if (diffs > tolerance).any():
                idx = int(diffs.arg_max())
                raise GoldenMismatchError(
                    f"numeric mismatch in {col!r} at row {idx}: "
                    f"actual={act_col[idx]}, expected={exp_col[idx]}, "
                    f"max_abs_diff={diffs.max()}, tolerance={tolerance}, "
                    f"dtypes={act_col.dtype}/{exp_col.dtype}"
                )
        else:
            if not (act_col == exp_col).all():
                raise GoldenMismatchError(
                    f"string/categorical mismatch in {col!r}"
                )
