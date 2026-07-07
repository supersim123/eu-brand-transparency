from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESEARCH_DIR = ROOT / "research"
PROMPT_PATH = RESEARCH_DIR / "weekly_research_prompt.md"
OUTPUT_PATH = RESEARCH_DIR / "weekly_research.json"
SUMMARY_PATH = RESEARCH_DIR / "weekly_research_summary.md"
LATEST_CHANGES_PATH = ROOT / "latest-changes.md"

DEFAULT_MODEL = "gpt-5.5"

RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["new_deal_candidates", "candidate_updates", "search_gaps"],
    "properties": {
        "new_deal_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "brand",
                    "sector",
                    "origin_country",
                    "buyer",
                    "buyer_country",
                    "buyer_region",
                    "deal_year",
                    "deal_status",
                    "deal_type",
                    "source_urls",
                    "preferred_source_type",
                    "confidence",
                    "why_relevant",
                    "dedupe_note",
                ],
                "properties": {
                    "brand": {"type": "string"},
                    "sector": {"type": "string"},
                    "origin_country": {"type": "string"},
                    "buyer": {"type": "string"},
                    "buyer_country": {"type": "string"},
                    "buyer_region": {"type": "string", "enum": ["USA", "China", "Europe", "Other"]},
                    "deal_year": {"type": ["integer", "null"]},
                    "deal_status": {
                        "type": "string",
                        "enum": ["completed", "announced", "pending_regulatory_review", "unclear", "cancelled"],
                    },
                    "deal_type": {
                        "type": "string",
                        "enum": [
                            "acquisition",
                            "majority_stake",
                            "take_private",
                            "asset_deal",
                            "merger",
                            "pending_takeover",
                            "indirect_ownership",
                        ],
                    },
                    "source_urls": {"type": "array", "items": {"type": "string"}},
                    "preferred_source_type": {
                        "type": "string",
                        "enum": [
                            "regulator",
                            "official_press_release",
                            "competition_authority",
                            "sec_filing",
                            "annual_report",
                            "reliable_media",
                            "other",
                        ],
                    },
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "why_relevant": {"type": "string"},
                    "dedupe_note": {"type": "string"},
                },
            },
        },
        "candidate_updates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["brand", "suggested_update", "source_urls", "confidence"],
                "properties": {
                    "brand": {"type": "string"},
                    "suggested_update": {"type": "string"},
                    "source_urls": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "search_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["area", "suggested_query"],
                "properties": {
                    "area": {"type": "string"},
                    "suggested_query": {"type": "string"},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """You are a research analyst for an open-source European brand ownership transparency list.

Find possible new or missing ownership changes involving well-known European consumer brands,
apps, platforms, retailers, travel companies, fintechs, mobility services, marketplaces,
fashion, beauty, food delivery, gaming, household, and electronics companies.

Rules:
- Do not guess.
- OpenAI output is not the source of truth.
- Every suggested ownership claim must include source URLs.
- Prefer official sources: regulator filings, competition authorities, company press releases,
  investor relations pages, SEC filings, annual reports, and official offer documents.
- Reliable media is acceptable only when official sources are unavailable.
- If evidence is weak or ownership is complex, mark confidence as low or medium.
- Exclude entries already present in known_deals unless there is a material update.
- If a brand exists only in known_candidates, check whether ownership can now be confirmed.
- Return only structured JSON that matches the requested schema.
"""


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is not set. Skipping OpenAI news research.")
        return

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt()
    PROMPT_PATH.write_text(prompt, encoding="utf-8")

    try:
        payload = call_openai(api_key, prompt)
        payload = dedupe_payload(payload)
        payload["status"] = "completed"
    except Exception as exc:
        payload = failed_payload(str(exc))
        print(f"OpenAI news research failed: {exc}", file=sys.stderr)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(payload), encoding="utf-8")
    append_latest_changes(payload)

    print(f"Wrote {PROMPT_PATH.relative_to(ROOT)}")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Wrote {SUMMARY_PATH.relative_to(ROOT)}")


def call_openai(api_key: str, prompt: str) -> dict[str, Any]:
    request_payload: dict[str, Any] = {
        "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        "instructions": SYSTEM_PROMPT,
        "input": prompt,
        "tools": [{"type": "web_search"}],
        "max_output_tokens": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "12000")),
        "reasoning": {"effort": os.getenv("OPENAI_REASONING_EFFORT", "low")},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "eu_brand_weekly_research",
                "strict": True,
                "schema": RESULT_SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "900"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"OpenAI request failed with HTTP {exc.code}: {detail}", file=sys.stderr)
        raise

    output_text = extract_output_text(response_payload).strip()
    if not output_text:
        raise RuntimeError("OpenAI response did not contain output text.")
    try:
        return json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI response was not valid JSON: {output_text[:1000]}") from exc


def extract_output_text(response_payload: dict[str, Any]) -> str:
    if response_payload.get("output_text"):
        return str(response_payload["output_text"])
    parts = []
    for item in response_payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts)


def build_prompt() -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    known_deals = compact_rows(
        read_csv(DATA_DIR / "deals.csv"),
        ["brand", "sector", "origin_country", "buyer", "buyer_country", "year", "deal_status"],
        int(os.getenv("OPENAI_RESEARCH_MAX_DEALS", "120")),
    )
    known_candidates = compact_rows(
        read_optional(DATA_DIR / "company_candidates.csv"),
        ["brand", "sector", "origin_country", "ownership_status", "known_owner", "research_priority"],
        int(os.getenv("OPENAI_RESEARCH_MAX_CANDIDATES", "120")),
    )
    buyer_watchlist = compact_rows(
        read_optional(DATA_DIR / "buyer_watchlist.csv"),
        ["buyer", "buyer_country", "buyer_region", "buyer_type", "priority", "lead_notes"],
        int(os.getenv("OPENAI_RESEARCH_MAX_BUYERS", "80")),
    )
    seed_lists = compact_rows(
        read_optional(DATA_DIR / "seed_lists.csv"),
        ["seed_list_id", "publisher", "title", "sector", "geography", "url"],
        int(os.getenv("OPENAI_RESEARCH_MAX_SEED_LISTS", "40")),
    )
    return f"""# EU Brand Transparency Weekly News Research

Date window:
- Search current news and official sources up to {today}.
- Prioritize ownership changes announced or completed in the last 7-30 days.
- Also include high-confidence missed deals from 2015 onward if relevant and absent.

Goal:
Find newly announced or previously missed acquisitions, majority stakes, take-privates,
mergers, or indirect ownership changes involving European consumer brands and platforms.

Known deals:
{known_deals}

Known research candidates:
{known_candidates}

Buyer watchlist:
{buyer_watchlist}

Seed-list sources:
{seed_lists}

Search priorities:
- Large consumer-facing European brands and apps.
- Marketplace, travel, retail, food delivery, gaming, fintech, mobility, fashion, beauty,
  household, and electronics sectors.
- Query known buyer types and names such as private equity firms, US tech companies,
  Chinese strategic buyers, marketplace groups, and large public-company acquirers.

Source priority:
1. EU Commission, national competition authorities, SEC filings, annual reports
2. company press releases or investor relations pages
3. reputable business media

Output:
- Only suggest leads that include URLs.
- Do not add already-known deals unless the current owner materially changed.
- Include useful search gaps for manual follow-up.
"""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_optional(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return read_csv(path)


def compact_rows(rows: list[dict[str, str]], columns: list[str], max_rows: int) -> str:
    selected = rows[:max_rows]
    lines = []
    for row in selected:
        values = [f"{column}={row.get(column, '')}" for column in columns if row.get(column, "")]
        lines.append("- " + "; ".join(values))
    if len(rows) > max_rows:
        lines.append(f"- ... {len(rows) - max_rows} more rows omitted")
    return "\n".join(lines) if lines else "- none"


def dedupe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    known_brands = {row["brand"].strip().lower() for row in read_csv(DATA_DIR / "deals.csv")}
    deduped = []
    for item in payload.get("new_deal_candidates", []):
        brand = str(item.get("brand", "")).strip().lower()
        dedupe_note = str(item.get("dedupe_note", "")).lower()
        if brand in known_brands and "material update" not in dedupe_note:
            continue
        deduped.append(item)
    payload["new_deal_candidates"] = deduped
    return payload


def render_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# Weekly OpenAI News Research",
        "",
        f"- Generated at: `{payload.get('generated_at', '')}`",
        f"- Status: `{payload.get('status', '')}`",
        f"- New deal candidates: **{len(payload.get('new_deal_candidates', []))}**",
        f"- Candidate updates: **{len(payload.get('candidate_updates', []))}**",
        f"- Search gaps: **{len(payload.get('search_gaps', []))}**",
        "",
        "OpenAI output is review material only. Verify every ownership claim against source documents before adding it to `data/deals.csv`.",
        "",
    ]
    if payload.get("error"):
        lines.extend(["## Error", "", str(payload["error"]), ""])
    if payload.get("new_deal_candidates"):
        lines.extend(["## New Deal Candidates", ""])
        for item in payload["new_deal_candidates"]:
            lines.append(
                f"- **{item.get('brand', '')}** -> {item.get('buyer', '')} "
                f"({item.get('deal_year', '')}, {item.get('confidence', '')})"
            )
            source_urls = ", ".join(item.get("source_urls", []))
            if source_urls:
                lines.append(f"  Sources: {source_urls}")
        lines.append("")
    if payload.get("candidate_updates"):
        lines.extend(["## Candidate Updates", ""])
        for item in payload["candidate_updates"]:
            lines.append(f"- **{item.get('brand', '')}**: {item.get('suggested_update', '')}")
        lines.append("")
    if payload.get("search_gaps"):
        lines.extend(["## Search Gaps", ""])
        for item in payload["search_gaps"]:
            lines.append(f"- **{item.get('area', '')}**: `{item.get('suggested_query', '')}`")
        lines.append("")
    return "\n".join(lines)


def failed_payload(error: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "error": error,
        "new_deal_candidates": [],
        "candidate_updates": [],
        "search_gaps": [],
    }


def append_latest_changes(payload: dict[str, Any]) -> None:
    if not LATEST_CHANGES_PATH.exists():
        return
    text = LATEST_CHANGES_PATH.read_text(encoding="utf-8").rstrip()
    addition = "\n".join(
        [
            "",
            "## Weekly OpenAI News Research",
            "",
            f"- New deal candidates: {len(payload.get('new_deal_candidates', []))}",
            f"- Candidate updates: {len(payload.get('candidate_updates', []))}",
            f"- Search gaps: {len(payload.get('search_gaps', []))}",
            "- Review: `research/weekly_research_summary.md`",
            "",
        ]
    )
    LATEST_CHANGES_PATH.write_text(text + "\n" + addition, encoding="utf-8")


if __name__ == "__main__":
    main()
