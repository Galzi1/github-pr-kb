# CLI User Guide

`github-pr-kb` is a command-line tool that extracts knowledge from GitHub pull request discussions. It works in three stages: **extract** PR comments from GitHub, **classify** them into knowledge categories using Claude, and **generate** a markdown knowledge base.

## Installation

### Option A: Run directly from GitHub (no clone needed)

If you have [`uv`](https://docs.astral.sh/uv/) installed:

```bash
uvx --from git+https://github.com/Galzi1/github-pr-kb.git github-pr-kb --help
```

Or with [`pipx`](https://pipx.pypa.io/):

```bash
pipx run --spec git+https://github.com/Galzi1/github-pr-kb.git github-pr-kb --help
```

To install it permanently (still without cloning):

```bash
uv tool install git+https://github.com/Galzi1/github-pr-kb.git
# or
pipx install git+https://github.com/Galzi1/github-pr-kb.git
```

### Option B: Clone and install locally

```bash
git clone https://github.com/Galzi1/github-pr-kb.git
cd github-pr-kb
uv sync          # or: pip install -e .
```

### Set up environment variables

   Copy the example file and fill in your tokens:

   ```bash
   cp .env.example .env
   ```

   | Variable | Required by | How to get it |
   |---|---|---|
   | `GITHUB_TOKEN` | `extract` | [GitHub Settings > Tokens](https://github.com/settings/tokens) &mdash; needs `repo` (or `public_repo` for public repos) |
   | `ANTHROPIC_API_KEY` | `classify` | [Anthropic Console](https://console.anthropic.com/) |

   > You can also export them as shell environment variables instead of using a `.env` file.

## Quick start

Run the full pipeline in one command:

```bash
github-pr-kb run --repo owner/repo-name
```

This executes extract, classify, and generate in sequence, printing a green summary after each step.

## Commands

### `extract` &mdash; Fetch PR comments from GitHub

```bash
github-pr-kb extract --repo owner/name [OPTIONS]
```

Downloads PR comments from the GitHub API and caches them locally in `.github-pr-kb/cache/`.

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--repo` | *(required)* | Repository in `owner/name` format |
| `--state` | `all` | Filter PRs: `open`, `closed`, or `all` |
| `--since DATE` | | Only PRs updated on or after this ISO date (e.g. `2024-01-01`) |
| `--until DATE` | | Only PRs updated on or before this ISO date |
| `-v, --verbose` | off | Print per-PR detail during extraction |

**Examples:**

```bash
# Extract all PRs from a repo
github-pr-kb extract --repo pallets/click

# Only closed PRs from 2024 onward
github-pr-kb extract --repo pallets/click --state closed --since 2024-01-01

# Verbose output to see progress per PR
github-pr-kb extract --repo pallets/click -v
```

### `classify` &mdash; Categorize comments with Claude

```bash
github-pr-kb classify [OPTIONS]
```

Reads the cached PR data from `extract` and sends comments to Claude for classification. Results are cached, so re-running skips already-classified comments.

Requires `ANTHROPIC_API_KEY` to be set.

**Options:**

| Flag | Default | Description |
|---|---|---|
| `-v, --verbose` | off | Print per-comment detail during classification |

**Examples:**

```bash
github-pr-kb classify
github-pr-kb classify --verbose
```

### `generate` &mdash; Write the knowledge base

```bash
github-pr-kb generate [OPTIONS]
```

Reads classified comments and produces markdown knowledge base articles in the `kb/` directory (configurable via the `KB_OUTPUT_DIR` environment variable).

**Options:**

| Flag | Default | Description |
|---|---|---|
| `-v, --verbose` | off | Print per-article detail during generation |

**Examples:**

```bash
github-pr-kb generate
github-pr-kb generate --verbose
```

### `run` &mdash; Full pipeline

```bash
github-pr-kb run --repo owner/name [OPTIONS]
```

Runs all three steps (extract, classify, generate) in sequence. If any step fails, the pipeline stops immediately with an error message indicating which step failed.

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--repo` | *(required)* | Repository in `owner/name` format |
| `-v, --verbose` | off | Print per-item detail for each step |

**Example:**

```bash
github-pr-kb run --repo pallets/click --verbose
```

## Typical workflow

```bash
# 1. Extract comments (can be re-run to pick up new PRs)
github-pr-kb extract --repo my-org/my-repo --since 2024-06-01

# 2. Classify the extracted comments
github-pr-kb classify

# 3. Generate the knowledge base
github-pr-kb generate

# 4. Review the output
ls kb/
```

Running the steps individually is useful when you want to extract from multiple repos before classifying, or re-generate the KB without re-classifying.

## File layout

After running the full pipeline, your project will contain:

```
.github-pr-kb/
  cache/
    pr-123.json              # Raw extracted PR data
    classified-pr-123.json   # Classification results
    classification-index.json
kb/
    *.md                     # Generated knowledge base articles
```

## Error handling

The CLI uses two exit codes:

| Exit code | Meaning |
|---|---|
| 1 | Runtime error (missing token, API failure, extraction error) |
| 2 | Usage error (bad flag value, missing required option) |

All errors include an actionable hint. For example, a missing `GITHUB_TOKEN` produces:

```
Error: Configuration error -- missing required environment variable.
Hint: copy .env.example to .env and fill in GITHUB_TOKEN (and ANTHROPIC_API_KEY for classify).
```

## Getting help

Every command supports `--help`:

```bash
github-pr-kb --help
github-pr-kb extract --help
github-pr-kb classify --help
github-pr-kb generate --help
github-pr-kb run --help
```
