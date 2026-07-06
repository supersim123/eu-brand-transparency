# Automation

EU Brand Transparency uses GitHub Actions as the public automation path.

## Weekly Refresh

Workflow: `.github/workflows/weekly-refresh.yml`

Schedule: Saturday 04:00 UTC

The workflow:

1. runs OpenAI-assisted news research when `OPENAI_API_KEY` is available
2. validates CSV data
3. regenerates `README.md` and `latest-changes.md`
4. opens a pull request with generated changes

OpenAI research writes review material to:

```text
research/weekly_research_prompt.md
research/weekly_research.json
research/weekly_research_summary.md
```

These files are leads only. OpenAI output is never treated as source evidence and does not automatically add public ownership records to the README.

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
```
