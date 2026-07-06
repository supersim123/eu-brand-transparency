# Contribution Guidelines

Thanks for helping improve EU Brand Transparency.

## Golden Rules

- Do not edit `README.md` directly. It is generated.
- Ownership claims need sources.
- OpenAI output is never a source. It can only suggest leads.
- Prefer official sources over media summaries.
- Keep uncertain or complex cases marked as `medium` or `low` confidence.

## Source Priority

Use the strongest available source:

1. Competition authority or regulator decision
2. Company press release or investor relations page
3. SEC filing, annual report, takeover document, or company registry
4. Reputable media such as Reuters, Financial Times, Sifted, TechCrunch, or major local business press
5. Blogs and listicles only as discovery leads, not as final proof

## Add an Ownership Record

Edit:

- `data/deals.csv`
- `data/sources.csv`

Every new `deal_id` in `data/deals.csv` must have at least one matching source row in `data/sources.csv`.

Then run:

```bash
python scripts/validate_data.py
python scripts/generate_readme.py
```

## Weekly OpenAI News Research

The weekly GitHub Action may generate:

```text
research/weekly_research_prompt.md
research/weekly_research.json
research/weekly_research_summary.md
```

Review those files manually. Move only verified, source-backed items into `data/deals.csv`.
OpenAI output is never source evidence.

## Add a Research Candidate

If ownership is not confirmed yet, add the brand to:

```text
data/company_candidates.csv
```

Use `ownership_status = needs_research` unless current ownership is already sourced.

## Pull Requests

One pull request should focus on one theme where possible:

- one brand update
- one sector expansion
- one source-quality cleanup
- one generator/workflow change

Pull requests should pass validation and tests before merge.

By participating, you agree to follow the project [Code of Conduct](.github/CODE_OF_CONDUCT.md).
