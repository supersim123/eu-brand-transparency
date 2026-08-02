from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.apply_verified_research import (
    APPROVED_DEAL_SCHEMA,
    apply_verified_payload,
    persist_raw_output,
    prepare_deal,
)


DEAL_FIELDS = [
    "deal_id",
    "brand",
    "sector",
    "origin_country",
    "buyer",
    "buyer_country",
    "buyer_region",
    "buyer_type",
    "year",
    "deal_date",
    "deal_type",
    "deal_status",
    "direct_owner",
    "ultimate_owner",
    "consumer_score",
    "confidence",
    "complexity",
    "reddit_ready",
    "one_line_summary",
    "ownership_notes",
]

SOURCE_FIELDS = [
    "source_id",
    "deal_id",
    "brand",
    "source_type",
    "publisher",
    "title",
    "url",
    "published_date",
    "accessed_date",
    "reliability_score",
    "summary",
]


def approved_deal(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "deal_id": "example_2024",
        "supersedes_deal_id": None,
        "brand": "Example",
        "sector": "marketplace",
        "origin_country": "Germany",
        "buyer": "Acquirer",
        "buyer_country": "USA",
        "buyer_region": "USA",
        "buyer_type": "public_company",
        "year": 2024,
        "deal_date": "2024-05-03",
        "deal_type": "acquisition",
        "direct_owner": "Example Inc.",
        "ultimate_owner": "Acquirer",
        "consumer_score": 8,
        "complexity": "low",
        "reddit_ready": "yes",
        "one_line_summary": "German marketplace Example was acquired by Acquirer.",
        "ownership_notes": "",
        "approval_reason": "Official closing release confirms control transferred.",
        "sources": [
            {
                "source_type": "official_press_release",
                "publisher": "Acquirer",
                "title": "Acquirer completes acquisition of Example",
                "url": "https://example.com/closing",
                "published_date": "2024-05-03",
                "reliability_score": 5,
                "summary": "The release confirms that the acquisition completed.",
            }
        ],
    }
    item.update(overrides)
    return item


def old_deal() -> dict[str, str]:
    return {
        "deal_id": "example_2020",
        "brand": "Example",
        "sector": "marketplace",
        "origin_country": "Germany",
        "buyer": "Old Owner",
        "buyer_country": "United Kingdom",
        "buyer_region": "Europe",
        "buyer_type": "strategic",
        "year": "2020",
        "deal_date": "2020-01-02",
        "deal_type": "acquisition",
        "deal_status": "completed",
        "direct_owner": "Example Ltd.",
        "ultimate_owner": "Old Owner",
        "consumer_score": "8",
        "confidence": "high",
        "complexity": "low",
        "reddit_ready": "yes",
        "one_line_summary": "Example was acquired by Old Owner.",
        "ownership_notes": "",
    }


class ApplyVerifiedResearchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.deals_path = root / "deals.csv"
        self.sources_path = root / "sources.csv"
        self.write_csv(self.deals_path, DEAL_FIELDS, [])
        self.write_csv(self.sources_path, SOURCE_FIELDS, [])

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_adds_verified_deal_and_source(self) -> None:
        result = apply_verified_payload(
            {"approved_deals": [approved_deal()]}, self.deals_path, self.sources_path
        )

        deals = self.read_csv(self.deals_path)
        sources = self.read_csv(self.sources_path)
        self.assertEqual(result, {"added": 1, "updated": 0, "superseded": 0})
        self.assertEqual(deals[0]["deal_status"], "completed")
        self.assertEqual(deals[0]["confidence"], "high")
        self.assertEqual(sources[0]["source_id"], "src_example_2024_001")
        self.assertEqual(sources[0]["reliability_score"], "5")

    def test_supersedes_existing_public_owner(self) -> None:
        self.write_csv(self.deals_path, DEAL_FIELDS, [old_deal()])
        item = approved_deal(supersedes_deal_id="example_2020")

        result = apply_verified_payload(
            {"approved_deals": [item]}, self.deals_path, self.sources_path
        )

        deals = {row["deal_id"]: row for row in self.read_csv(self.deals_path)}
        self.assertEqual(result["superseded"], 1)
        self.assertEqual(deals["example_2020"]["reddit_ready"], "no")
        self.assertEqual(deals["example_2024"]["reddit_ready"], "yes")

    def test_refuses_competing_owner_without_supersession(self) -> None:
        self.write_csv(self.deals_path, DEAL_FIELDS, [old_deal()])
        original = self.deals_path.read_bytes()

        with self.assertRaisesRegex(ValueError, "supersedes_deal_id"):
            apply_verified_payload(
                {"approved_deals": [approved_deal()]}, self.deals_path, self.sources_path
            )

        self.assertEqual(self.deals_path.read_bytes(), original)

    def test_refuses_weak_source_evidence(self) -> None:
        item = approved_deal()
        item["sources"][0]["reliability_score"] = 3  # type: ignore[index]

        with self.assertRaisesRegex(ValueError, "no reliability 4 or 5 source"):
            prepare_deal(item)

    def test_empty_approval_does_not_rewrite_files(self) -> None:
        before_deals = self.deals_path.read_bytes()
        before_sources = self.sources_path.read_bytes()

        result = apply_verified_payload(
            {"approved_deals": []}, self.deals_path, self.sources_path
        )

        self.assertEqual(result, {"added": 0, "updated": 0, "superseded": 0})
        self.assertEqual(self.deals_path.read_bytes(), before_deals)
        self.assertEqual(self.sources_path.read_bytes(), before_sources)

    def test_openai_schema_requires_iso_calendar_dates(self) -> None:
        properties = APPROVED_DEAL_SCHEMA["properties"]

        self.assertEqual(properties["deal_date"]["format"], "date")
        self.assertEqual(
            properties["sources"]["items"]["properties"]["published_date"]["format"],
            "date",
        )

    def test_raw_verification_output_is_preserved(self) -> None:
        path = Path(self.temp_dir.name) / "weekly_verification_raw.json"

        persist_raw_output('{"decision":"PASS"}', path)

        self.assertEqual(path.read_text(encoding="utf-8"), '{"decision":"PASS"}\n')

    @staticmethod
    def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def read_csv(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
