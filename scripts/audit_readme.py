from __future__ import annotations

import argparse
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
README_PATH = ROOT / "README.md"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
AUDIT_JSON_PATH = REPORTS_DIR / "readme_audit.json"
AUDIT_MD_PATH = REPORTS_DIR / "readme_audit.md"

DEFAULT_MODEL = "gpt-5.5"

AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["has_issues", "summary", "push_decision", "push_reason", "issues"],
    "properties": {
        "has_issues": {"type": "boolean"},
        "summary": {"type": "string"},
        "push_decision": {"type": "string", "enum": ["PASS", "STOP"]},
        "push_reason": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["severity", "category", "location", "problem", "suggestion"],
                "properties": {
                    "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                    "category": {
                        "type": "string",
                        "enum": [
                            "format",
                            "readability",
                            "missing_flag",
                            "long_name",
                            "source",
                            "possible_data_error",
                            "other",
                        ],
                    },
                    "location": {"type": "string"},
                    "problem": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """You are auditing a generated GitHub README for an open-source
EU Brand Transparency list.

Only report notable problems. It is fine to return no issues.
Only report issues that require a concrete README or data change.
Do not report generic "verify this" warnings when linked source evidence supports the row.
Set push_decision to STOP only when the README should not be published automatically.
Use STOP for malformed tables, missing critical source evidence, or a likely wrong current-owner claim.
Use PASS for minor readability issues, non-blocking source improvements, or warnings that can be reviewed later.
Do not invent later transactions, source URLs, or completion dates.

Look for:
- missing national flags in table cells where a single clear country is shown
- very long brand or owner names that make tables hard to scan
- malformed Markdown tables
- broken-looking img tags or favicon markup
- inconsistent table columns
- suspicious ownership or source mismatches visible from the README text and provided source evidence

Do not ask for more explanation text. The README should stay simple.
Return only JSON matching the schema.
"""


def main() -> None:
    args = parse_args()
    payload = run_audit()
    print(f"Wrote {AUDIT_JSON_PATH.relative_to(ROOT)}")
    print(f"Wrote {AUDIT_MD_PATH.relative_to(ROOT)}")
    print(f"README audit decision: {payload.get('push_decision')} - {payload.get('push_reason')}")
    if args.fail_on_stop and payload.get("push_decision") == "STOP":
        raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit generated README tables with OpenAI.")
    parser.add_argument(
        "--fail-on-stop",
        action="store_true",
        help="Exit non-zero when the audit says the README should not be published.",
    )
    return parser.parse_args()


def run_audit() -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        payload = {
            "has_issues": True,
            "summary": "README audit skipped because OPENAI_API_KEY is not set.",
            "push_decision": "STOP",
            "push_reason": "OpenAI quality check did not run.",
            "issues": [],
            "generated_at": _now(),
        }
        write_outputs(payload)
        return payload

    readme = README_PATH.read_text(encoding="utf-8")
    prompt = build_prompt(readme)
    try:
        payload = call_openai(api_key, prompt)
    except Exception as exc:
        payload = {
            "has_issues": True,
            "summary": "README audit failed.",
            "push_decision": "STOP",
            "push_reason": str(exc),
            "issues": [
                {
                    "severity": "error",
                    "category": "other",
                    "location": "OpenAI audit",
                    "problem": str(exc),
                    "suggestion": "Re-run the audit after fixing the API or model issue.",
                }
            ],
        }

    payload = normalize_payload(payload)
    payload["generated_at"] = _now()
    write_outputs(payload)
    return payload


def build_prompt(readme: str) -> str:
    return f"""Audit this generated GitHub README.

Current date: {datetime.now(timezone.utc).date().isoformat()}

Source evidence available to the generated README:

```text
{source_evidence()}
```

README:

```markdown
{readme}
```
"""


def call_openai(api_key: str, prompt: str) -> dict[str, Any]:
    request_payload: dict[str, Any] = {
        "model": os.getenv("OPENAI_AUDIT_MODEL", os.getenv("OPENAI_MODEL", DEFAULT_MODEL)),
        "instructions": SYSTEM_PROMPT,
        "input": prompt,
        "max_output_tokens": int(os.getenv("OPENAI_AUDIT_MAX_OUTPUT_TOKENS", "6000")),
        "reasoning": {"effort": os.getenv("OPENAI_REASONING_EFFORT", "low")},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "eu_brand_readme_audit",
                "strict": True,
                "schema": AUDIT_SCHEMA,
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
        raise RuntimeError(f"OpenAI request failed with HTTP {exc.code}: {detail}") from exc

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


def source_evidence() -> str:
    sources_path = DATA_DIR / "sources.csv"
    if not sources_path.exists():
        return "No source evidence file found."

    public_deal_ids = public_deal_ids_from_data()
    lines = []
    with sources_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            deal_id = row.get("deal_id", "")
            if public_deal_ids and deal_id not in public_deal_ids:
                continue
            lines.append(
                " | ".join(
                    [
                        deal_id,
                        row.get("brand", ""),
                        row.get("publisher", ""),
                        row.get("source_type", ""),
                        f"reliability={row.get('reliability_score', '')}",
                        f"date={row.get('published_date', '')}",
                        row.get("title", ""),
                        row.get("url", ""),
                        row.get("summary", ""),
                    ]
                )
            )
    return "\n".join(lines[:250])


def public_deal_ids_from_data() -> set[str]:
    deals_path = DATA_DIR / "deals.csv"
    if not deals_path.exists():
        return set()
    with deals_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row.get("deal_id", "")
            for row in reader
            if row.get("reddit_ready") in {"yes", "maybe"}
            and row.get("deal_status") == "completed"
        }


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    issues = payload.get("issues")
    if not isinstance(issues, list):
        payload["issues"] = []
    decision = payload.get("push_decision")
    if decision not in {"PASS", "STOP"}:
        payload["push_decision"] = "STOP"
        payload["push_reason"] = "Audit returned an invalid push_decision."
    payload["has_issues"] = bool(payload.get("issues")) or payload.get("push_decision") == "STOP"
    payload.setdefault("summary", "")
    payload.setdefault("push_reason", "")
    return payload


def write_outputs(payload: dict[str, Any]) -> None:
    AUDIT_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    AUDIT_MD_PATH.write_text(render_markdown(payload), encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# README Audit",
        "",
        f"- Generated at: `{payload.get('generated_at', '')}`",
        f"- Decision: **{payload.get('push_decision', '')}**",
        f"- Summary: {payload.get('summary', '')}",
        f"- Reason: {payload.get('push_reason', '')}",
        "",
    ]
    issues = payload.get("issues", [])
    if not issues:
        lines.extend(["No notable issues found.", ""])
        return "\n".join(lines)

    lines.extend(["## Issues", ""])
    for issue in issues:
        lines.append(f"- **{issue.get('severity', '')} / {issue.get('category', '')}** at `{issue.get('location', '')}`")
        lines.append(f"  Problem: {issue.get('problem', '')}")
        lines.append(f"  Suggestion: {issue.get('suggestion', '')}")
    lines.append("")
    return "\n".join(lines)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
