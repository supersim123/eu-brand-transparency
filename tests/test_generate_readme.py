from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GenerateReadmeTest(unittest.TestCase):
    def test_generate_readme_completes_and_keeps_core_sections(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/generate_readme.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("EU Brand Transparency", readme)
        self.assertIn("## Contents", readme)
        self.assertIn("## Research Candidates", readme)
        self.assertIn("Wrote README.md", result.stdout)
        self.assertIn("https://investors.globalpayments.com/news-events/press-releases/detail/498/", readme)
        self.assertIn("https://blogs.microsoft.com/blog/2023/10/13/", readme)
        self.assertIn("https://adevinta.com/press-releases/adevinta-asa-ade-completion-of-the-voluntary-offer", readme)
        self.assertIn("https://www.catalannews.com/business/item/south-koreas-naver-completes-acquisition-of-wallapop", readme)
        self.assertIn("https://www.videogameschronicle.com/news/sega-has-completed-its-acquisition-of-rovio/", readme)


if __name__ == "__main__":
    unittest.main()
