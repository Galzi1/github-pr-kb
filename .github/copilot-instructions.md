# github-pr-kb Copilot Instructions

## Commands

```powershell
uv sync --all-groups
uv sync --all-groups --frozen    # CI-style install

.\.venv\Scripts\python.exe -m ruff check src tests
uv run pre-commit run --all-files

.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m pytest tests\test_cli.py::test_extract_help -q

$env:RUN_INTEGRATION_TESTS="1"; .\.venv\Scripts\python.exe -m pytest tests\test_extractor_integration.py -v -m integration
$env:RUN_INTEGRATION_TESTS="1"; .\.venv\Scripts\python.exe -m pytest tests\test_classifier_integration.py -v -m integration
```

Use the `.venv` Python for pytest in this repository. On this machine, `uv run pytest` resolves to the wrong interpreter and can fail to import the package.

The pre-commit hook is Ruff-only and runs with `--fix --exit-non-zero-on-fix`, so a failed hook often means Ruff already rewrote files and expects them to be re-staged.

## High-level architecture

- `src\github_pr_kb\cli.py` is a thin Click wrapper around a three-step pipeline: `extract`, `classify`, `generate`, plus `run` to execute all three in order.
- `src\github_pr_kb\extractor.py` uses PyGithub plus `GITHUB_TOKEN` from `config.py` to fetch review comments and issue comments, filter out noise, and write one cache file per PR to `.github-pr-kb\cache\pr-<number>.json`.
- `src\github_pr_kb\classifier.py` reads those cached PR files, sends comment bodies to Anthropic, caches per-body results in `.github-pr-kb\cache\classification-index.json`, and writes `.github-pr-kb\cache\classified-pr-<number>.json`.
- `src\github_pr_kb\generator.py` joins `classified-pr-<number>.json` back to the original `pr-<number>.json`, writes one markdown article per classified comment under `kb\<category>\`, tracks incremental dedup in `kb\.manifest.json`, and rebuilds `kb\INDEX.md` on every run.
- `src\github_pr_kb\models.py` defines the Pydantic schemas shared by every stage. Cache files are expected to round-trip through these models rather than ad hoc dicts.
- `src\github_pr_kb\config.py` loads `.env` via `pydantic-settings`. `GITHUB_TOKEN` is required at settings construction time; `ANTHROPIC_API_KEY` is only required when classification runs; `ANTHROPIC_MODEL` overrides the default classifier model; `KB_OUTPUT_DIR` changes the generator output root.

## Key conventions

- Keep CLI imports lazy. `cli.py` intentionally imports `settings`, `GitHubExtractor`, `PRClassifier`, and `KBGenerator` inside helper functions so `--help` and usage errors still work when required env vars are missing.
- `config.settings` is instantiated at module import time. Tests rely on `tests\conftest.py` setting dummy `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` before collection, so avoid new top-level imports that force settings construction earlier than necessary.
- Persisted artifacts are append-only and incremental. Extraction merges by `comment_id`, classification deduplicates by SHA-256 of comment body, and generation skips comments already present in `kb\.manifest.json`.
- New file writes should follow the existing atomic-write pattern (`tempfile.mkstemp` + `os.replace`) used in extractor, classifier, and generator.
- Noise filtering is intentionally selective: known automation accounts and non-substantive comments are skipped, but substantive bot comments are still valid input. Do not broaden the bot filter blindly.
- The classifier has exactly five categories: `architecture_decision`, `code_pattern`, `gotcha`, `domain_knowledge`, and `other`. Confidence below `0.75` means `needs_review=True`; that flag must stay consistent across classification output, article frontmatter, and `INDEX.md` review markers.
- Generated KB articles use YAML frontmatter, set the first `#` heading from the classifier summary, include the raw comment body, and only include a fenced diff block when the source comment was a review comment with a `diff_hunk`.
- Models use `ConfigDict(extra="ignore")` for forward compatibility. Preserve that behavior when evolving cache schemas.
