from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.openai_news_research import select_candidate_rows


def candidate(
    index: int,
    priority: str = "medium",
    ownership_status: str = "needs_research",
    acquisition_status: str = "needs_research",
) -> dict[str, str]:
    return {
        "brand": f"Brand {index:03d}",
        "sector": "marketplace",
        "origin_country": "Germany",
        "ownership_status": ownership_status,
        "known_owner": "",
        "research_priority": priority,
        "consumer_score": str(index % 10),
        "acquisition_status": acquisition_status,
    }


class OpenAINewsResearchCandidateSelectionTest(unittest.TestCase):
    def test_selection_rotates_instead_of_taking_first_rows(self) -> None:
        rows = [candidate(index) for index in range(20)]

        selected, note = select_candidate_rows(rows, max_rows=5)

        self.assertEqual(len(selected), 5)
        self.assertNotEqual([row["brand"] for row in selected], [row["brand"] for row in rows[:5]])
        self.assertIn("rotating unresolved candidates", note)

    def test_high_priority_candidates_are_kept_in_priority_share(self) -> None:
        rows = [candidate(index, priority="medium") for index in range(20)]
        rows.extend(candidate(100 + index, priority="high") for index in range(4))

        selected, _ = select_candidate_rows(rows, max_rows=8)

        selected_brands = {row["brand"] for row in selected}
        self.assertTrue({f"Brand {100 + index:03d}" for index in range(4)}.issubset(selected_brands))

    def test_rotation_week_changes_medium_priority_slice(self) -> None:
        rows = [candidate(index) for index in range(30)]

        with patch.dict(os.environ, {"OPENAI_RESEARCH_ROTATION_WEEK": "100"}):
            first, _ = select_candidate_rows(rows, max_rows=6)
            repeated, _ = select_candidate_rows(rows, max_rows=6)
        with patch.dict(os.environ, {"OPENAI_RESEARCH_ROTATION_WEEK": "101"}):
            next_week, _ = select_candidate_rows(rows, max_rows=6)

        self.assertEqual([row["brand"] for row in first], [row["brand"] for row in repeated])
        self.assertNotEqual([row["brand"] for row in first], [row["brand"] for row in next_week])


if __name__ == "__main__":
    unittest.main()
