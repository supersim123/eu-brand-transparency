
---

## Contribution

Contributions are welcome. Please do not edit `README.md` directly. The public list is generated from the data files.

Good contributions usually do one of three things:

- add a new source-backed ownership record to `data/deals.csv` and `data/sources.csv`
- update an existing row with better source evidence
- add a research candidate to `data/company_candidates.csv`

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Research Workflow

- Public list generation: `python scripts/generate_readme.py`
- Validation: `python scripts/validate_data.py`
- Weekly GitHub Action: `.github/workflows/weekly-refresh.yml`
- OpenAI news research: `python scripts/openai_news_research.py`

## Trademarks

Brand names, trademarks, logos, and favicons belong to their respective owners. Favicons are shown only as small visual identifiers for research and transparency purposes.

## License

Content and data are released under [CC BY-SA 4.0](LICENSE). Code in this repository may be reused under the same license unless a separate code license is added later.
