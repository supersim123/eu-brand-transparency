# Automation

EU Brand Transparency uses GitHub Actions as the public automation path.

## Weekly Refresh

Workflow: `.github/workflows/weekly-refresh.yml`

Schedule: Saturday 04:00 UTC

The workflow:

1. validates CSV data
2. regenerates `README.md` and `latest-changes.md`
3. runs OpenAI-assisted news research for new leads
4. audits the generated README with OpenAI
5. stops before pull-request creation when the audit returns `STOP`
6. runs the repository tests
7. opens a pull request with generated changes

OpenAI research writes review material to:

```text
research/weekly_research_prompt.md
research/weekly_research.json
research/weekly_research_summary.md
```

These files are leads only. OpenAI output is never treated as source evidence and does not automatically add public ownership records to the README.

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

The audit is a quality gate for the generated public list. It checks visible README issues such as malformed tables, missing flags, broken favicon markup, very long owner names, and suspicious source mismatches visible from the available source evidence.

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
OPENAI_AUDIT_MODEL=gpt-5.5
```
