from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ValidateDataTest(unittest.TestCase):
    def test_validate_data_passes_current_csv_files(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_data.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("Validation passed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
