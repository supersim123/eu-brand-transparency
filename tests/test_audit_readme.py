from __future__ import annotations

import unittest

from scripts.audit_readme import normalize_payload


class AuditReadmeTest(unittest.TestCase):
    def test_false_future_date_stop_is_downgraded(self) -> None:
        payload = {
            "has_issues": True,
            "summary": "Date issue",
            "push_decision": "STOP",
            "push_reason": "Future-dated evidence",
            "issues": [
                {
                    "severity": "error",
                    "category": "possible_data_error",
                    "location": "Deliveroo",
                    "problem": "Source dated 2000-01-01 is after the current date?",
                    "suggestion": "Remove the row.",
                }
            ],
        }

        normalized = normalize_payload(payload)

        self.assertEqual(normalized["push_decision"], "PASS")
        self.assertEqual(normalized["issues"][0]["severity"], "warning")


if __name__ == "__main__":
    unittest.main()
