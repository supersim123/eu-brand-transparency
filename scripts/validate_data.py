from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

REQUIRED_COLUMNS = {
    "deals.csv": {
        "deal_id",
        "brand",
        "sector",
        "origin_country",
        "buyer",
        "buyer_country",
        "buyer_region",
        "buyer_type",
        "year",
        "deal_type",
        "deal_status",
        "consumer_score",
        "confidence",
        "complexity",
        "reddit_ready",
        "one_line_summary",
    },
    "sources.csv": {
        "source_id",
        "deal_id",
        "brand",
        "source_type",
        "publisher",
        "title",
        "url",
        "accessed_date",
        "reliability_score",
        "summary",
    },
    "seed_brands.csv": {"brand", "sector", "origin_country", "brand_type", "notes"},
}

ALLOWED = {
    "buyer_region": {"USA", "China", "Europe", "Other"},
    "buyer_type": {"strategic", "private_equity", "consortium", "public_company", "state_owned", "unknown"},
    "deal_status": {"completed", "announced", "pending_regulatory_review", "unclear", "cancelled"},
    "confidence": {"high", "medium", "low"},
    "complexity": {"low", "medium", "high"},
    "reddit_ready": {"yes", "no", "maybe"},
}


def main() -> None:
    errors = []
    tables = {}
    for filename, columns in REQUIRED_COLUMNS.items():
        path = DATA_DIR / filename
        if not path.exists():
            errors.append(f"Missing required file: {path}")
            continue
        rows, fieldnames = _read_csv(path)
        tables[filename] = rows
        missing = sorted(columns - set(fieldnames or []))
        if missing:
            errors.append(f"{filename} missing columns: {', '.join(missing)}")

    if errors:
        _finish(errors)

    deals = tables["deals.csv"]
    sources = tables["sources.csv"]
    seed_brands = tables["seed_brands.csv"]

    errors.extend(_duplicates(deals, "deal_id", "deals.csv"))
    errors.extend(_duplicates(sources, "source_id", "sources.csv"))
    errors.extend(_duplicates(seed_brands, "brand", "seed_brands.csv"))
    errors.extend(_validate_deals(deals))
    errors.extend(_validate_sources(sources))

    deal_ids = {row["deal_id"] for row in deals}
    source_deal_ids = {row["deal_id"] for row in sources}
    missing_sources = sorted(deal_ids - source_deal_ids)
    unknown_sources = sorted(source_deal_ids - deal_ids)
    if missing_sources:
        errors.append("Deals missing sources: " + ", ".join(missing_sources))
    if unknown_sources:
        errors.append("Sources reference unknown deal_ids: " + ", ".join(unknown_sources))

    _finish(errors)


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str] | None]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames


def _duplicates(rows: list[dict[str, str]], column: str, label: str) -> list[str]:
    counts = Counter(row[column] for row in rows)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    if not duplicates:
        return []
    return [f"{label} duplicate {column}: " + ", ".join(duplicates)]


def _validate_deals(rows: list[dict[str, str]]) -> list[str]:
    errors = []
    for index, row in enumerate(rows, start=2):
        for column, allowed in ALLOWED.items():
            if row.get(column) not in allowed:
                errors.append(f"deals.csv row {index}: invalid {column}={row.get(column)!r}")
        errors.extend(_int_range(row, index, "year", 2005, 2026))
        errors.extend(_int_range(row, index, "consumer_score", 0, 10))
    return errors


def _validate_sources(rows: list[dict[str, str]]) -> list[str]:
    errors = []
    for index, row in enumerate(rows, start=2):
        errors.extend(_int_range(row, index, "reliability_score", 1, 5, label="sources.csv"))
        if not row.get("url", "").startswith(("http://", "https://")):
            errors.append(f"sources.csv row {index}: source url must be http(s)")
    return errors


def _int_range(
    row: dict[str, str],
    index: int,
    column: str,
    minimum: int,
    maximum: int,
    label: str = "deals.csv",
) -> list[str]:
    value = row.get(column, "")
    try:
        parsed = int(value)
    except ValueError:
        return [f"{label} row {index}: {column} must be an integer"]
    if minimum <= parsed <= maximum:
        return []
    return [f"{label} row {index}: {column} must be between {minimum} and {maximum}"]


def _finish(errors: list[str]) -> None:
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Validation passed.")


if __name__ == "__main__":
    main()
