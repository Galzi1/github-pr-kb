# Phase 1: Project Foundation - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the uv-managed Python project: `pyproject.toml` with all runtime and dev dependencies, the `src/github_pr_kb/` package structure with stub modules, a `pydantic-settings`-based config module that validates `GITHUB_TOKEN` on import, a `.env.example` template, and a passing smoke test suite. No extraction, classification, or generation logic is built here.

</domain>

<decisions>
## Implementation Decisions

### Project layout
- `src/` layout — code lives in `src/github_pr_kb/`
- Package name: `github_pr_kb`
- Organized by responsibility from day one: `config.py`, `models.py`, `extractor.py`, `classifier.py`, `generator.py`, `cli.py`
- Phase 1 creates stub files for later-phase modules (just a module docstring) so import paths are clean from day one

### Env validation approach
- `pydantic-settings` for environment loading and validation (reads `.env` automatically)
- Settings is instantiated at module level — validation runs on import, failing before any CLI command
- Phase 1 Settings model includes only `GITHUB_TOKEN` (required, no default)
- Fixed `.env` at project root — no path override or ENV_FILE support
- `ANTHROPIC_API_KEY` and other vars deferred to the phases that need them

### Pydantic types scope
- Phase 1 defines **Settings only** in `config.py`
- No PR/Comment data models in Phase 1 — those belong in Phase 2 when extraction is built
- No shared base classes or mixins — keep minimal, avoid premature abstraction

### Dev tooling
- Runtime deps: `PyGithub`, `pydantic`, `pydantic-settings`, `anthropic`, `click`
- Dev deps: `pytest`, `pytest-cov`, `ruff`
- Minimal ruff config in `pyproject.toml`: enable E, F, I (isort) rule sets
- `tests/test_config.py` smoke test: validates that instantiating Settings without `GITHUB_TOKEN` raises a `ValidationError`
- `pytest-mock` is NOT included in Phase 1 — added in Phase 2 when mocked API tests begin

### Claude's Discretion
- Python version target (3.11+ recommended given pydantic v2 + pydantic-settings)
- Exact `pyproject.toml` metadata (description, authors, license)
- pytest config in `pyproject.toml` (testpaths, addopts for coverage thresholds)
- Whether to add a `Makefile` or `justfile` for common dev commands

</decisions>

<specifics>
## Specific Ideas

- The existing `requirements.txt` with `PyGithub==1.55` is superseded by `pyproject.toml` — no `requirements.txt` should remain
- `uv sync` is the canonical install command (not `pip install -e .`)
- The package CLI entry point (`github-pr-kb` command) is wired up in `pyproject.toml` [project.scripts], even though the CLI logic is in Phase 6

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `requirements.txt` (PyGithub==1.55): Only existing artifact — confirms PyGithub is already chosen but version needs updating in pyproject.toml

### Established Patterns
- No existing patterns — this phase establishes them

### Integration Points
- `src/github_pr_kb/config.py` → imported by every later module that needs settings
- `src/github_pr_kb/models.py` → imported by Phase 2 (extraction), Phase 4 (classification), Phase 5 (generation)
- `pyproject.toml [project.scripts]` → wires up the `github-pr-kb` CLI entry point for Phase 6

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-foundation*
*Context gathered: 2026-03-10*
