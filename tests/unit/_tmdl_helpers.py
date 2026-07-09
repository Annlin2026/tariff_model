"""Shared utilities for TMDL structural tests.

Leading underscore prevents pytest from auto-collecting this module as tests.
Consumers: `test_dim_*_tmdl.py` — extract duplicated idioms here so new dim
tests (P1 Iter 3+) can reuse them without re-copying regex boilerplate.

Indent assumption
-----------------
TMDL tables emitted by Tabular Editor / this project use **4-space indentation**
for child blocks of a `table` (columns, partitions, hierarchies). All regex
patterns here anchor on `^\\s{4}<keyword>` to scope matches to direct children
of the table — this mirrors the original inline regexes in the caller tests.
If the emitter ever switches indent width, these helpers (and the tests that
use them) must be updated in lockstep.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_MODEL_DIR = (
    REPO_ROOT / "semantic_model" / "itrade_tariff_model.SemanticModel" / "definition"
)


def load_tmdl(relative_path: str) -> str:
    """Read a TMDL file under SEMANTIC_MODEL_DIR and return its text.

    `relative_path` is interpreted relative to
    `semantic_model/itrade_tariff_model.SemanticModel/definition/`, e.g.
    `"tables/dim_country.tmdl"`.
    """
    return (SEMANTIC_MODEL_DIR / relative_path).read_text(encoding="utf-8")


def extract_lineage_tags(tmdl_text: str) -> list[str]:
    """Return all `lineageTag: <uuid>` values (order preserved, duplicates kept)."""
    return re.findall(r"lineageTag:\s*([0-9a-fA-F-]+)", tmdl_text)


def _column_block(tmdl_text: str, name: str) -> str | None:
    """Return the text of the `column <name>` block, or None if absent.

    Block scope: from the matching `^\\s{4}column <name>` line to the next
    `^\\s{4}(column|partition|hierarchy) ` sibling (or EOF).
    """
    match = re.search(rf"^\s{{4}}column\s+{re.escape(name)}\b", tmdl_text, re.MULTILINE)
    if match is None:
        return None
    start = match.start()
    rest = tmdl_text[start:]
    next_block = re.search(r"^\s{4}(column|partition|hierarchy)\s+", rest[1:], re.MULTILINE)
    return rest[: 1 + next_block.start()] if next_block else rest


def column_exists(tmdl_text: str, name: str, source: str | None = None) -> bool:
    """Return True if a `column <name>` block exists.

    If `source` is given, additionally require `sourceColumn: <source>` inside
    the column's block.
    """
    block = _column_block(tmdl_text, name)
    if block is None:
        return False
    if source is None:
        return True
    return f"sourceColumn: {source}" in block


def columns_with_summarize_by_none(tmdl_text: str) -> set[str]:
    """Return names of columns whose block contains `summarizeBy: none`."""
    result: set[str] = set()
    column_starts = [
        (m.start(), m.group(1))
        for m in re.finditer(r"^\s{4}column\s+(\w+)\b", tmdl_text, re.MULTILINE)
    ]
    for start, name in column_starts:
        rest = tmdl_text[start:]
        next_block = re.search(r"^\s{4}(column|partition|hierarchy)\s+", rest[1:], re.MULTILINE)
        block = rest[: 1 + next_block.start()] if next_block else rest
        if "summarizeBy: none" in block:
            result.add(name)
    return result


def measure_block(tmdl_text: str, name: str) -> str:
    """Return a measure's block: its `///` doc-comments through to the line
    before the next 4-space-indented sibling object.

    Raises AssertionError if the measure is absent (callers assert presence).
    Shared by the per-issue measure structural tests (#57, #66, ...).
    """
    lines = tmdl_text.splitlines()
    pattern = re.compile(rf"^\s{{4}}measure '{re.escape(name)}'")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        raise AssertionError(f"measure {name!r} not found in TMDL")
    # pull in contiguous /// doc-comment lines directly above
    doc_start = start
    while doc_start > 0 and lines[doc_start - 1].lstrip().startswith("///"):
        doc_start -= 1
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if re.match(r"^\s{4}\S", lines[i]) and not lines[i].lstrip().startswith("///")
        ),
        len(lines),
    )
    # the sibling's doc-comments belong to the sibling, not to this block
    while end > start + 1 and lines[end - 1].lstrip().startswith("///"):
        end -= 1
    return "\n".join(lines[doc_start:end])


def measure_expression(block: str) -> str:
    """Strip `///` doc-comment lines so assertions target the live DAX only."""
    return "\n".join(
        line for line in block.splitlines() if not line.lstrip().startswith("///")
    )
