# Automation

EU Brand Transparency uses GitHub Actions as the public automation path.

## Weekly Refresh

Workflow: `.github/workflows/weekly-refresh.yml`

Schedule: Saturday 04:00 UTC

The workflow:

1. validates CSV data
2. runs OpenAI-assisted news research for new leads
3. independently verifies every lead with a second OpenAI web-search pass
4. adds only verified, completed ownership changes to `data/deals.csv` and `data/sources.csv`
5. validates the updated CSV data and regenerates `README.md` and `latest-changes.md`
6. audits the generated README with OpenAI
7. stops before pull-request creation when either OpenAI gate returns `STOP`
8. runs the repository tests
9. opens a pull request and enables automatic squash merge

OpenAI research writes review material to:

```text
research/weekly_research_prompt.md
research/weekly_research.json
research/weekly_research_summary.md
```

The first research pass produces leads only. The independent verification pass writes:

```text
research/weekly_verification.json
research/weekly_verification_raw.json
research/weekly_verification_summary.md
```

The verifier opens source links and searches for independent evidence. It approves only completed deals with current-owner evidence and at least one source rated 4 or 5. Approved records are normalized and added automatically; rejected or uncertain records remain in the research report and do not reach the README. The raw structured response is retained separately so schema or deterministic-validation failures can be diagnosed without weakening the publication gate.

The weekly research prompt is built from:

```text
data/deals.csv
data/company_candidates.csv
data/buyer_watchlist.csv
data/seed_lists.csv
```

The README audit writes:

```text
reports/readme_audit.json
reports/readme_audit.md
```

The README audit is a separate final quality gate. It checks visible issues such as malformed tables, missing flags, broken favicon markup, very long owner names, and suspicious source mismatches visible from the available source evidence.

The weekly job merges its pull request only after both OpenAI gates, CSV validation, and the full test suite pass. A failed gate leaves `main` unchanged.

For a non-publishing manual test, run the workflow with `dry_run` enabled. It executes the full pipeline and uploads the generated README, data, research, and audit reports as the `weekly-refresh-dry-run` artifact without creating or merging a pull request.

## Secret Safety

Store the API key as a repository secret:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
Name: OPENAI_API_KEY
```

The public pull-request validation workflow does not use OpenAI and does not receive this secret.

Manual OpenAI runs are limited in the workflow to the repository owner account `supersim123`. Scheduled runs execute from the default branch.

The repository does not use `pull_request_target`. Do not add it unless you are deliberately reviewing the security implications, because it can expose secrets to untrusted pull request code.

Optional repository variable:

```text
OPENAI_MODEL=gpt-5.5
OPENAI_VERIFY_MODEL=gpt-5.5
OPENAI_AUDIT_MODEL=gpt-5.5
```
