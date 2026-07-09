"""Custom TMDL lint rules for iTrade semantic model.

P0 delivers the minimal rule:
  - summarizeBy-none-on-pct: any column whose name matches *_pct or *_rate_pct
    must have summarizeBy: none
  - summarizeBy-none-on-tariff: any column in a fact_tariff_* table must have
    summarizeBy: none

Extended in later phases:
  - P1: dim grain uniqueness check
  - P3 Iter 3: full tariff rules + Direct Lake specific rules
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TARIFF_TABLE_RE = re.compile(r"^table\s+(fact_tariff_\w+)", re.MULTILINE)
COLUMN_BLOCK_RE = re.compile(
    r"column\s+(?P<name>\w+)(?P<body>(?:\n\s{8,}.*)*)", re.MULTILINE
)
SUMMARIZE_RE = re.compile(r"summarizeBy:\s*(\w+)", re.IGNORECASE)
PCT_NAME_RE = re.compile(r"^\w*_(pct|rate_pct)$")
GRAIN_COLUMNS_REQUIRED = {
    "txn_year", "importer_code", "exporter_code", "hs_code", "tariff_type",
}
LINEAGE_TAG_RE = re.compile(r"lineageTag:\s*([0-9a-fA-F-]+)", re.IGNORECASE)
FACT_TARIFF_RATE_DEF_RE = re.compile(r"^table\s+fact_tariff_rate\b", re.MULTILINE)


@dataclass(frozen=True)
class LintViolation:
    rule: str
    file_path: str
    line: int
    message: str


def _column_summarize_by(body: str) -> str | None:
    m = SUMMARIZE_RE.search(body)
    return m.group(1).lower() if m else None


def _check_fact_tariff_grain(text: str, file_path: str) -> list[LintViolation]:
    if not FACT_TARIFF_RATE_DEF_RE.search(text):
        return []
    column_names = {m.group("name") for m in COLUMN_BLOCK_RE.finditer(text)}
    missing = GRAIN_COLUMNS_REQUIRED - column_names
    if not missing:
        return []
    return [
        LintViolation(
            rule="fact-tariff-rate-grain-columns",
            file_path=file_path,
            line=1,
            message=(
                f"fact_tariff_rate missing grain columns: "
                f"{sorted(missing)}; required: {sorted(GRAIN_COLUMNS_REQUIRED)}"
            ),
        )
    ]


def lint_tmdl_text(text: str, file_path: str = "<string>") -> list[LintViolation]:
    violations: list[LintViolation] = []
    is_tariff_table = bool(TARIFF_TABLE_RE.search(text))

    for match in COLUMN_BLOCK_RE.finditer(text):
        name = match.group("name")
        body = match.group("body") or ""
        summarize = _column_summarize_by(body)
        line_no = text[: match.start()].count("\n") + 1

        is_pct = bool(PCT_NAME_RE.match(name))
        if is_pct and summarize not in (None, "none"):
            violations.append(
                LintViolation(
                    rule="summarizeBy-none-on-pct",
                    file_path=file_path,
                    line=line_no,
                    message=f"column {name!r} has summarizeBy={summarize!r}; required: none",
                )
            )
        if is_tariff_table and summarize not in (None, "none"):
            violations.append(
                LintViolation(
                    rule="summarizeBy-none-on-tariff",
                    file_path=file_path,
                    line=line_no,
                    message=(
                        f"tariff column {name!r} has summarizeBy={summarize!r}; "
                        "tariff columns are non-additive and must be summarizeBy: none"
                    ),
                )
            )
    violations.extend(_check_fact_tariff_grain(text, file_path))
    return violations


def lint_tmdl_folder(folder: Path) -> list[LintViolation]:
    results: list[LintViolation] = []
    seen: dict[str, tuple[str, int]] = {}
    for tmdl_file in folder.rglob("*.tmdl"):
        text = tmdl_file.read_text(encoding="utf-8")
        results.extend(lint_tmdl_text(text, file_path=str(tmdl_file)))
        for m in LINEAGE_TAG_RE.finditer(text):
            tag = m.group(1).lower()
            line_no = text[: m.start()].count("\n") + 1
            prior = seen.get(tag)
            if prior is not None:
                results.append(
                    LintViolation(
                        rule="lineage-tag-unique",
                        file_path=str(tmdl_file),
                        line=line_no,
                        message=(
                            f"duplicate lineageTag {tag!r}; first seen at "
                            f"{prior[0]}:{prior[1]}"
                        ),
                    )
                )
            else:
                seen[tag] = (str(tmdl_file), line_no)
    return results


def main() -> None:
    import argparse
    import sys

    p = argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    args = p.parse_args()

    violations = lint_tmdl_folder(args.folder)
    for v in violations:
        # GitHub Actions annotation format
        print(
            f"::error file={v.file_path},line={v.line}::"
            f"{v.rule} — {v.message}",
            file=sys.stderr,
        )
    if violations:
        sys.exit(1)
    print(f"tmdl_lint: 0 violations in {args.folder}")


if __name__ == "__main__":
    main()
