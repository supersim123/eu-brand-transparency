from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
README_PATH = ROOT / "README.md"
LATEST_CHANGES_PATH = ROOT / "latest-changes.md"

COUNTRY_FLAGS = {
    "Australia": "AU",
    "Austria": "AT",
    "Belarus": "BY",
    "Belgium": "BE",
    "Brazil": "BR",
    "Canada": "CA",
    "China": "CN",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "France": "FR",
    "Germany": "DE",
    "Greece": "GR",
    "India": "IN",
    "Ireland": "IE",
    "Italy": "IT",
    "Finland": "FI",
    "Japan": "JP",
    "Netherlands": "NL",
    "Norway": "NO",
    "Poland": "PL",
    "Romania": "RO",
    "Saudi Arabia": "SA",
    "Serbia": "RS",
    "Singapore": "SG",
    "Slovenia": "SI",
    "South Korea": "KR",
    "South Africa": "ZA",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Thailand": "TH",
    "Turkey": "TR",
    "United Kingdom": "GB",
    "USA": "US",
}

CATEGORY_ORDER = [
    "Travel & Booking",
    "Mobility & Auto",
    "Retail & E-Commerce",
    "Fashion & Beauty",
    "Food Delivery & Grocery",
    "Fintech & Payments",
    "Gaming",
    "Consumer Apps & Software",
    "Household & Electronics",
    "Marketplaces",
    "Other",
]

CATEGORY_MAP = {
    "app": "Consumer Apps & Software",
    "beauty": "Fashion & Beauty",
    "consumer goods": "Retail & E-Commerce",
    "creator commerce": "Retail & E-Commerce",
    "e-commerce": "Retail & E-Commerce",
    "e-commerce infrastructure": "Retail & E-Commerce",
    "e-commerce logistics": "Retail & E-Commerce",
    "electronics": "Household & Electronics",
    "electronics rental": "Household & Electronics",
    "fashion": "Fashion & Beauty",
    "fashion e-commerce": "Fashion & Beauty",
    "fintech": "Fintech & Payments",
    "food": "Food Delivery & Grocery",
    "food delivery": "Food Delivery & Grocery",
    "foodtech": "Food Delivery & Grocery",
    "gaming": "Gaming",
    "grocery": "Food Delivery & Grocery",
    "grocery delivery": "Food Delivery & Grocery",
    "household appliances": "Household & Electronics",
    "industrial": "Other",
    "luxury marketplace": "Marketplaces",
    "marketplace": "Marketplaces",
    "mobility": "Mobility & Auto",
    "real estate": "Marketplaces",
    "retail": "Retail & E-Commerce",
    "software": "Consumer Apps & Software",
    "streaming": "Consumer Apps & Software",
    "travel": "Travel & Booking",
}


def main() -> None:
    deals = _public_deals(_read_csv(_deals_path()))
    sources = _read_csv(DATA_DIR / "sources.csv")
    candidates = _read_optional(DATA_DIR / "company_candidates.csv")
    seed_entries = _read_optional(DATA_DIR / "seed_list_entries.csv")
    deals = _merge_by_brand(deals, _read_optional(DATA_DIR / "brand_assets.csv"))
    deals = _merge_by_brand(deals, _read_optional(DATA_DIR / "readme_display_overrides.csv"))

    README_PATH.write_text(_render_readme(deals, sources, candidates, seed_entries), encoding="utf-8")
    LATEST_CHANGES_PATH.write_text(_render_latest_changes(deals, candidates), encoding="utf-8")
    print(f"Wrote {README_PATH.relative_to(ROOT)}")
    print(f"Wrote {LATEST_CHANGES_PATH.relative_to(ROOT)}")


def _deals_path() -> Path:
    reviewed = DATA_DIR / "reviewed_deals.csv"
    return reviewed if reviewed.exists() and reviewed.stat().st_size > 0 else DATA_DIR / "deals.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_optional(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return _read_csv(path)


def _public_deals(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    public = [
        row.copy()
        for row in rows
        if row.get("reddit_ready") in {"yes", "maybe"} and row.get("deal_status") == "completed"
    ]
    return sorted(
        public,
        key=lambda row: (
            -_int(row.get("consumer_score")),
            -_int(row.get("curation_score")),
            -_int(row.get("year")),
            row.get("brand", ""),
        ),
    )


def _merge_by_brand(rows: list[dict[str, str]], extras: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows or not extras:
        return rows
    index = {row["brand"]: row for row in extras if row.get("brand")}
    merged = []
    for row in rows:
        combined = row.copy()
        combined.update(index.get(row.get("brand", ""), {}))
        merged.append(combined)
    return merged


def _render_readme(
    deals: list[dict[str, str]],
    sources: list[dict[str, str]],
    candidates: list[dict[str, str]],
    seed_entries: list[dict[str, str]],
) -> str:
    header = _template("header.md")
    footer = _template("footer.md")
    category_counts = _category_counts(deals)
    replacements = {
        "{company_count}": str(len(deals)),
        "{candidate_count}": str(len(candidates)),
        "{source_count}": str(len({row["deal_id"] for row in sources})),
        "{category_count}": str(len(category_counts)),
        "{last_updated}": datetime.now(timezone.utc).date().isoformat(),
    }
    for old, new in replacements.items():
        header = header.replace(old, new)
        footer = footer.replace(old, new)

    parts = [header.rstrip(), "", _contents(category_counts)]
    parts.extend(_render_categories(deals, sources))
    parts.append(_render_candidate_snapshot(candidates, seed_entries))
    parts.append(_explanation())
    parts.append(footer.rstrip())
    return "\n\n".join(part for part in parts if part is not None).rstrip() + "\n"


def _render_latest_changes(deals: list[dict[str, str]], candidates: list[dict[str, str]]) -> str:
    now = datetime.now(timezone.utc).date().isoformat()
    high_confidence = sum(1 for row in deals if row.get("confidence") == "high")
    non_european = sum(1 for row in deals if row.get("buyer_region") in {"USA", "China", "Other"})
    return "\n".join(
        [
            f"# Latest Changes ({now})",
            "",
            "This file is generated for the weekly transparency-list update PR.",
            "",
            "## Current Snapshot",
            "",
            f"- Public ownership records: {len(deals)}",
            f"- Research candidates: {len(candidates)}",
            f"- High-confidence records: {high_confidence}",
            f"- Non-European owners: {non_european}",
            "",
            "## Review Notes",
            "",
            "- Confirm every new ownership claim with source evidence before adding it to `data/deals.csv`.",
            "- Regenerate the list with `python scripts/generate_readme.py` after data changes.",
            "",
        ]
    )


def _template(name: str) -> str:
    path = CONFIG_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _category_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[_category(row.get("sector", ""))] += 1
    return {category: counts[category] for category in CATEGORY_ORDER if counts[category]}


def _contents(category_counts: dict[str, int]) -> str:
    lines = ["## Contents", ""]
    for category, count in category_counts.items():
        label = "record" if count == 1 else "records"
        lines.append(f"- [{category}](#{_anchor(category)}) _{count} {label}_")
    lines.extend(["- [Research Candidates](#research-candidates)", "- [Contribution](#contribution)", ""])
    return "\n".join(lines)


def _render_categories(rows: list[dict[str, str]], sources: list[dict[str, str]]) -> list[str]:
    source_index = _source_index(sources)
    sections = []
    for category in CATEGORY_ORDER:
        category_rows = [row for row in rows if _category(row.get("sector", "")) == category]
        if not category_rows:
            continue
        lines = [f"## {category}", "", "| Brand | Founded in | Current owner | Deal year | Source |", "|---|---|---|---:|---|"]
        for row in category_rows:
            lines.append(_table_row(row, source_index))
        sections.append("\n".join(lines).rstrip())
    return sections


def _table_row(row: dict[str, str], source_index: dict[str, list[dict[str, str]]]) -> str:
    brand = _brand_cell(row)
    founded = f"{_flag(row.get('origin_country', ''))} {row.get('origin_country', '')}".strip()
    owner_name = row.get("display_owner") or row.get("buyer", "")
    owner_country = row.get("display_owner_country") or row.get("buyer_country", "")
    owner = f"{_flag(owner_country)} {owner_name}".strip()
    source = _primary_source_link(row.get("deal_id", ""), source_index)
    return f"| {brand} | {founded} | {owner} | {row.get('year', '')} | {source} |"


def _brand_cell(row: dict[str, str]) -> str:
    display_name = row.get("display_brand") or row.get("brand", "")
    brand = f"**{display_name}**"
    favicon = _favicon_url(row)
    if not favicon:
        return brand
    return f'<img src="{favicon}" width="18" height="18" alt=""> {brand}'


def _favicon_url(row: dict[str, str]) -> str:
    if row.get("favicon_url"):
        return row["favicon_url"].strip()
    value = row.get("website_url", "").strip()
    if not value:
        return ""
    domain = urlparse(value).netloc or urlparse(f"https://{value}").netloc
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"


def _source_index(sources: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    sorted_sources = sorted(
        sources,
        key=lambda row: (
            row.get("deal_id", ""),
            -_int(row.get("reliability_score")),
            row.get("published_date", ""),
            row.get("source_type", ""),
        ),
        reverse=False,
    )
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for source in sorted_sources:
        index[source.get("deal_id", "")].append(source)
    return index


def _primary_source_link(deal_id: str, source_index: dict[str, list[dict[str, str]]]) -> str:
    sources = source_index.get(deal_id, [])
    if not sources:
        return ""
    source = sources[0]
    return f"[{source.get('publisher', '')}]({source.get('url', '')})"


def _render_candidate_snapshot(candidates: list[dict[str, str]], seed_entries: list[dict[str, str]]) -> str:
    if not candidates:
        return ""
    return "\n".join(
        [
            "## Research Candidates",
            "",
            "These are not public ownership claims yet. They are the working queue for future source checks.",
            "",
            f"Research queue: **{len(candidates)} candidates** from **{len(seed_entries)} seed-list entries**.",
            "",
            "Working data: [`data/company_candidates.csv`](data/company_candidates.csv).",
            "",
        ]
    )


def _explanation() -> str:
    return "\n".join(
        [
            "## Explanation",
            "",
            "- `Founded in` shows the brand's original European home market where known.",
            "- `Current owner` shows the controlling buyer or ultimate owner from the available sources.",
            "- `Deal year` is the year of the acquisition, take-private, merger, or control change.",
            "- Source links point to the strongest available evidence for the ownership record.",
            "- OpenAI-assisted research may propose leads, but OpenAI output is never treated as a source.",
            "",
        ]
    )


def _category(sector: str) -> str:
    return CATEGORY_MAP.get(sector.strip().lower(), "Other")


def _anchor(value: str) -> str:
    return value.lower().replace("&", "").replace(" ", "-")


def _flag(country: str) -> str:
    if "/" in country:
        flags = [_flag(part.strip()) for part in country.split("/") if part.strip()]
        return " ".join(flag for flag in flags if flag)
    code = COUNTRY_FLAGS.get(country)
    if not code:
        return ""
    base = 127397
    return "".join(chr(base + ord(letter)) for letter in code.upper())


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


if __name__ == "__main__":
    main()
