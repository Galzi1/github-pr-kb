# github-pr-kb

Extract durable knowledge from GitHub pull request discussions, classify the useful comments, and publish the result as a markdown knowledge base.

## Automate with GitHub Actions

The shipped workflow lives at `.github/workflows/github-pr-kb.yml`. It runs after merged PRs (`pull_request` with `types: [closed]` and a merged-only guard) and also supports `workflow_dispatch` for recovery and backfill runs.

### Copy the workflow into a consumer repository

1. Copy `.github/workflows/github-pr-kb.yml` into the target repository.
2. Add the required repository secrets.
3. Merge the workflow and let future merged PRs update the KB automatically.

Consumer repositories **copy only the workflow file**. They **do not need this tool's source tree checked into your repository** because the workflow performs a second checkout of this repo into `.github-pr-kb-tool`, installs the tool there, and runs every `github-pr-kb` command from that checkout.

### Tool bootstrap and upgrades

The workflow is intentionally copyable across repositories and uses two explicit bootstrap settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `KB_TOOL_REPOSITORY` | `Galzi1/github-pr-kb` | Which repository to checkout for the CLI and helper code |
| `KB_TOOL_REF` | immutable full commit SHA | Which exact tool version to run |

`KB_TOOL_REF` should stay pinned to an immutable release tag or full commit SHA. Treat it like any other supply-chain pin: update it intentionally, review the diff, and commit the workflow change when you want to upgrade.

### Credential roles

The docs separate **local/runtime credentials** from **workflow repository-variable credentials** because they do different jobs:

| Credential | Used by | Where it belongs |
| --- | --- | --- |
| `GITHUB_TOKEN` | Local CLI extraction, or the workflow's extract/classify/generate steps via `${{ github.token }}` | Local `.env` for manual runs; GitHub-provided token inside Actions |
| `ANTHROPIC_API_KEY` | Local `classify` and `generate`, plus workflow classification/generation | Local `.env` and repository secret |
| `KB_VARIABLES_TOKEN` | Quickstart auth for workflow `gh api` and `gh pr` calls | Repository secret only |
| `KB_VARIABLES_APP_ID` + `KB_VARIABLES_APP_PRIVATE_KEY` | Advanced GitHub App auth for workflow `gh api` and `gh pr` calls | Repository secrets only |

Inside the workflow, the resolved repository-variable credential is mapped to `GH_TOKEN` for `gh api` and `gh pr`, while the CLI steps receive `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` separately.

### PAT quickstart

Set these repository secrets in the consumer repository:

| Secret | Why |
| --- | --- |
| `ANTHROPIC_API_KEY` | Required for comment classification and article generation |
| `KB_VARIABLES_TOKEN` | Auth for repository variable reads/writes and rolling PR publication |

For a fine-grained PAT quickstart, grant the token the minimum repository permissions needed for this workflow:

- `Variables: Read and write`
- `Contents: Read and write`
- `Pull requests: Read and write`

This is the fastest setup path and is documented first on purpose.

### GitHub App

For a longer-lived service-account setup, configure these repository secrets instead of `KB_VARIABLES_TOKEN`:

| Secret | Why |
| --- | --- |
| `KB_VARIABLES_APP_ID` | GitHub App identifier |
| `KB_VARIABLES_APP_PRIVATE_KEY` | Private key used to mint an installation token |

The workflow prefers the GitHub App path when both the app secrets and `KB_VARIABLES_TOKEN` are present, and falls back to `KB_VARIABLES_TOKEN` otherwise.

### Manual recovery and backfill

Use `workflow_dispatch` when you need to recover from a failed run or backfill older merged PRs.

| Input | Meaning |
| --- | --- |
| `since` | Optional ISO-8601 `updated_at` cursor override for backfill |
| `force` | Run even when no newer merged PRs are detected |

### Committed vs not committed

The workflow keeps publication output and working cache separate:

| Path | Git status | Why |
| --- | --- | --- |
| `kb/INDEX.md` | committed | Top-level KB index |
| `kb/**/*.md` | committed | Generated KB articles |
| `kb/.manifest.json` | committed | Generator dedup state required for incremental correctness |
| `.github-pr-kb/cache/` | not committed | Transient extract/classify cache for local runs and Actions cache reuse |

## Run locally

You can also run the tool directly without GitHub Actions.

### Install uv

Install uv first. Official docs: https://docs.astral.sh/uv/getting-started/installation/

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configure local environment

Copy `.env.example` to `.env`. `.env.example` documents the local config surface only; it is not a workflow secret template.

| Variable | Required | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | yes | GitHub API auth for extraction |
| `ANTHROPIC_API_KEY` | for `classify`/`generate` | Anthropic API auth |
| `ANTHROPIC_MODEL` | no | Override the classifier model |
| `ANTHROPIC_GENERATE_MODEL` | no | Override the article-generation model |
| `KB_OUTPUT_DIR` | no | Output directory for generated KB content |
| `MIN_CONFIDENCE` | no | Minimum confidence threshold for generated articles |

Workflow-only secrets such as `KB_VARIABLES_TOKEN`, `KB_VARIABLES_APP_ID`, and `KB_VARIABLES_APP_PRIVATE_KEY` belong in repository secrets, not in `.env`.

### Install dependencies

```bash
uv sync --all-groups --frozen
```

### Run tests

Use the venv Python directly:

```powershell
.venv/Scripts/python.exe -m pytest tests/
```

```bash
.venv/bin/python -m pytest tests/
```

### CLI commands

```bash
github-pr-kb extract --repo owner/name
github-pr-kb extract --repo owner/name --state closed --since 2024-01-01
github-pr-kb classify
github-pr-kb generate
github-pr-kb run --repo owner/name
```

### Example KB output

```text
kb/
  INDEX.md
  .manifest.json
  architecture_decision/
    prefer-monotonic-cursor-updates.md
  code_pattern/
    keep-cli-imports-lazy.md
```

## Development

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

The pre-commit hook is Ruff-only and may rewrite files before asking you to re-stage them.
