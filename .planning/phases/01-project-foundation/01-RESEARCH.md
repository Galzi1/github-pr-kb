# Phase 1: Project Foundation - Research

**Researched:** 2026-03-10
**Domain:** Python project packaging (uv, pyproject.toml, pydantic-settings)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Project layout:**
- `src/` layout — code lives in `src/github_pr_kb/`
- Package name: `github_pr_kb`
- Organized by responsibility from day one: `config.py`, `models.py`, `extractor.py`, `classifier.py`, `generator.py`, `cli.py`
- Phase 1 creates stub files for later-phase modules (just a module docstring) so import paths are clean from day one

**Env validation approach:**
- `pydantic-settings` for environment loading and validation (reads `.env` automatically)
- Settings is instantiated at module level — validation runs on import, failing before any CLI command
- Phase 1 Settings model includes only `GITHUB_TOKEN` (required, no default)
- Fixed `.env` at project root — no path override or ENV_FILE support
- `ANTHROPIC_API_KEY` and other vars deferred to the phases that need them

**Pydantic types scope:**
- Phase 1 defines **Settings only** in `config.py`
- No PR/Comment data models in Phase 1 — those belong in Phase 2 when extraction is built
- No shared base classes or mixins — keep minimal, avoid premature abstraction

**Dev tooling:**
- Runtime deps: `PyGithub`, `pydantic`, `pydantic-settings`, `anthropic`, `click`
- Dev deps: `pytest`, `pytest-cov`, `ruff`
- Minimal ruff config in `pyproject.toml`: enable E, F, I (isort) rule sets
- `tests/test_config.py` smoke test: validates that instantiating Settings without `GITHUB_TOKEN` raises a `ValidationError`
- `pytest-mock` is NOT included in Phase 1 — added in Phase 2 when mocked API tests begin

**Specific implementation notes:**
- The existing `requirements.txt` with `PyGithub==1.55` is superseded by `pyproject.toml` — no `requirements.txt` should remain
- `uv sync` is the canonical install command (not `pip install -e .`)
- The package CLI entry point (`github-pr-kb` command) is wired up in `pyproject.toml` [project.scripts], even though the CLI logic is in Phase 6

### Claude's Discretion
- Python version target (3.11+ recommended given pydantic v2 + pydantic-settings)
- Exact `pyproject.toml` metadata (description, authors, license)
- pytest config in `pyproject.toml` (testpaths, addopts for coverage thresholds)
- Whether to add a `Makefile` or `justfile` for common dev commands

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Project ships with `pyproject.toml` declaring all runtime and dev dependencies with version pins | uv + uv_build backend; `[dependency-groups]` for dev deps; pinned versions in findings below |
| INFRA-04 | `.env.example` template documents all required environment variables | Simple file with one entry (`GITHUB_TOKEN`); pydantic-settings reads `.env` by default |
</phase_requirements>

---

## Summary

Phase 1 establishes the entire project scaffold: a `src/`-layout Python package managed by uv, all runtime and dev dependencies declared with version pins in `pyproject.toml`, a pydantic-settings-based config module that validates `GITHUB_TOKEN` on import, stub modules for future phases, and a smoke test that proves the validation fires.

The toolchain is stable and well-understood. uv is the canonical package manager; its native `uv_build` backend handles pure-Python `src/` layout without additional configuration. pydantic-settings v2 makes the validation pattern trivial: a required field with no default raises `ValidationError` at instantiation time, and instantiating at module level means the error surfaces on import — before any CLI logic runs.

The key execution risk is getting the `pyproject.toml` shape right the first time (build backend, dependency group syntax, scripts entry point) so later phases never need to revisit packaging setup.

**Primary recommendation:** Use `uv_build` as the build backend, `[dependency-groups]` for dev deps (PEP 735, natively supported by uv), and instantiate `Settings()` at module scope in `config.py`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uv | latest (CLI tool) | Virtualenv, dependency resolution, `uv sync` | Fastest Python package manager; canonical for this project |
| uv_build | >=0.6.0 | Build backend for packaging | Native uv backend; zero-config for pure-Python src layout |
| pydantic | >=2.12.5 | Data validation (Settings base) | Industry standard; v2 is current |
| pydantic-settings | >=2.13.1 | BaseSettings + .env reading | Official pydantic env-var integration; separate package since pydantic v2 |
| PyGithub | >=2.5.0 | GitHub REST API client | Declared chosen by project; v2.x is current (1.55 in old requirements.txt is stale) |
| anthropic | >=0.84.0 | Claude API SDK | Official Anthropic Python SDK |
| click | >=8.3.1 | CLI framework | De facto Python CLI standard |

### Supporting (dev)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0.2 | Test runner | All tests |
| pytest-cov | >=7.0.0 | Coverage reporting | `--cov` flag in addopts |
| ruff | >=0.15.5 | Linter + formatter | E, F, I rule sets; replaces flake8 + isort |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv_build | hatchling | hatchling needed only if build scripts or non-standard layout required; uv_build is simpler |
| uv_build | setuptools | More boilerplate; no advantage for pure-Python packages |
| `[dependency-groups]` | `[project.optional-dependencies]` | optional-dependencies become package extras (published metadata); dependency-groups are dev-only and never published |

**Installation (after cloning):**
```bash
uv sync
```

**Adding dependencies:**
```bash
# Runtime
uv add PyGithub pydantic pydantic-settings anthropic click

# Dev group
uv add --group dev pytest pytest-cov ruff
```

---

## Architecture Patterns

### Recommended Project Structure
```
github-pr-kb/
├── src/
│   └── github_pr_kb/
│       ├── __init__.py       # empty or version marker
│       ├── config.py         # Settings (pydantic-settings); instantiated at module level
│       ├── models.py         # stub — populated in Phase 2
│       ├── extractor.py      # stub — populated in Phase 2
│       ├── classifier.py     # stub — populated in Phase 4
│       ├── generator.py      # stub — populated in Phase 5
│       └── cli.py            # stub — populated in Phase 6
├── tests/
│   ├── __init__.py
│   └── test_config.py        # smoke test: missing GITHUB_TOKEN raises ValidationError
├── pyproject.toml            # single source of truth for project metadata + deps
├── uv.lock                   # committed; exact resolved versions
├── .env.example              # documents GITHUB_TOKEN (and future vars)
├── .env                      # gitignored; actual secrets
├── .gitignore
├── LICENSE
└── README.md
```

### Pattern 1: pyproject.toml Complete Shape
**What:** Single file declaring build system, project metadata, runtime deps, dev deps, scripts entry point, pytest config, and ruff config.
**When to use:** This is the entire project configuration — nothing goes in setup.py, setup.cfg, or requirements.txt.

```toml
# Source: https://docs.astral.sh/uv/concepts/build-backend/
[build-system]
requires = ["uv_build>=0.6.0,<0.7.0"]
build-backend = "uv_build"

[project]
name = "github-pr-kb"
version = "0.1.0"
description = "Extract and preserve knowledge from GitHub PR discussions"
requires-python = ">=3.11"
dependencies = [
    "PyGithub>=2.5.0",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.13.1",
    "anthropic>=0.84.0",
    "click>=8.3.1",
]

[project.scripts]
github-pr-kb = "github_pr_kb.cli:cli"

# Source: https://docs.astral.sh/uv/concepts/projects/dependencies/
[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    "ruff>=0.15.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=github_pr_kb --cov-report=term-missing"

[tool.ruff]
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

### Pattern 2: pydantic-settings Config with Module-Level Instantiation
**What:** `Settings` class with required fields (no defaults) that raises `ValidationError` on missing env vars; instantiated at module scope so validation fires on import.
**When to use:** This is the entire pattern for `config.py` in Phase 1.

```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    github_token: str  # Required — no default; maps to GITHUB_TOKEN env var

# Module-level instantiation: ValidationError raised on import if GITHUB_TOKEN missing
settings = Settings()
```

**Import from anywhere:**
```python
from github_pr_kb.config import settings
```

### Pattern 3: Stub Module
**What:** Minimal Python file that satisfies imports without implementing any logic.
**When to use:** `models.py`, `extractor.py`, `classifier.py`, `generator.py`, `cli.py` in Phase 1.

```python
"""
github_pr_kb.extractor
~~~~~~~~~~~~~~~~~~~~~~
PR comment extraction from GitHub API. Implemented in Phase 2.
"""
```

### Anti-Patterns to Avoid
- **Importing from pydantic directly:** `from pydantic import BaseSettings` fails in pydantic v2. Use `from pydantic_settings import BaseSettings`.
- **Lazy instantiation:** Instantiating `Settings()` inside functions defeats early-failure validation. Always instantiate at module scope.
- **requirements.txt alongside pyproject.toml:** The existing `requirements.txt` must be deleted. Having both creates confusion about which is authoritative.
- **`pip install -e .` workflow:** This project uses `uv sync`. Do not document or use pip install.
- **`[project.optional-dependencies]` for dev deps:** These become package extras in published metadata. Use `[dependency-groups]` instead for internal dev tooling.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env file reading | Custom `os.environ` parsing | pydantic-settings `env_file` in `SettingsConfigDict` | Handles encoding, type coercion, nested values, multiple sources |
| Missing-var error messages | Custom `if not os.getenv(...)` checks | pydantic-settings `ValidationError` | Provides field-level error details automatically |
| Import sorting | Manual import ordering | ruff `I` ruleset | Consistent, deterministic, zero-config |
| Lockfile generation | Hand-editing versions | `uv lock` / `uv sync` | Cross-platform resolution with conflict detection |

**Key insight:** pydantic-settings handles every validation edge case (type coercion, missing required fields, .env merging with OS env) that a hand-rolled os.environ checker will get wrong the first time.

---

## Common Pitfalls

### Pitfall 1: PyGithub Version — v1.x vs v2.x API Differences
**What goes wrong:** The existing `requirements.txt` pins `PyGithub==1.55`. The v2.x API changed significantly (e.g., pagination, rate limit access). Code written against v1 docs will fail on v2.
**Why it happens:** PyGithub had a major version bump with breaking changes.
**How to avoid:** Use `PyGithub>=2.5.0` in `pyproject.toml`. When Phase 2 writes extraction code, reference v2.x documentation, not v1.x examples found online.
**Warning signs:** Import errors, changed method signatures on `Github`, `Repository`, `PaginatedList`.

### Pitfall 2: pydantic v1 vs v2 Import Paths
**What goes wrong:** `from pydantic import BaseSettings` raises `PydanticImportError` in pydantic v2. Many online examples still show the v1 import.
**Why it happens:** pydantic moved `BaseSettings` to a separate `pydantic-settings` package in v2.
**How to avoid:** Always `from pydantic_settings import BaseSettings, SettingsConfigDict`. This is verified against current pydantic-settings v2 docs.
**Warning signs:** `PydanticImportError: BaseSettings has been moved to the pydantic-settings package`.

### Pitfall 3: uv_build Version Pinning
**What goes wrong:** Pinning `uv_build` to a too-narrow version range (e.g., exact match) causes install failures when uv itself updates.
**Why it happens:** `uv_build` version tracks uv releases closely.
**How to avoid:** Use a minor-version range: `requires = ["uv_build>=0.6.0,<0.7.0"]` and update when uv updates. Alternatively, leave loose: `requires = ["uv_build"]`.
**Warning signs:** `build-system.requires` resolution failures during `uv sync`.

### Pitfall 4: pytest --cov with src Layout
**What goes wrong:** `--cov=src` or `--cov=.` in addopts reports coverage for the wrong paths and may inflate or deflate numbers.
**Why it happens:** The package is installed as `github_pr_kb` (not `src/github_pr_kb`), so coverage must target the package name.
**How to avoid:** Use `--cov=github_pr_kb` in addopts — this is the installed package name, which pytest-cov resolves correctly via the installed editable package.
**Warning signs:** 0% coverage despite tests running, or coverage reported on test files themselves.

### Pitfall 5: .env File Missing Causes Silent Success
**What goes wrong:** If `GITHUB_TOKEN` is already set in the OS environment (e.g., from a CI secret or shell profile), the smoke test that checks for `ValidationError` on missing token will pass even without `.env`, masking whether pydantic-settings is actually reading the file.
**Why it happens:** pydantic-settings prioritizes OS environment variables over `.env` file values.
**How to avoid:** In `test_config.py`, use `monkeypatch.delenv("GITHUB_TOKEN", raising=False)` to guarantee the variable is absent during the test, regardless of OS state.
**Warning signs:** Smoke test passes on CI but fails locally (or vice versa).

---

## Code Examples

Verified patterns from official sources:

### Complete config.py
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    github_token: str
    # Future vars added here in their respective phases:
    # anthropic_api_key: str  (Phase 4)


settings = Settings()
```

### Smoke test: test_config.py
```python
# Source: pydantic-settings ValidationError behavior
import pytest
from pydantic import ValidationError


def test_settings_requires_github_token(monkeypatch):
    """Settings instantiation without GITHUB_TOKEN must raise ValidationError."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    # Re-import Settings class directly to avoid cached module-level instance
    from importlib import import_module
    import importlib
    import sys

    # Remove cached module to force fresh instantiation
    sys.modules.pop("github_pr_kb.config", None)

    with pytest.raises(ValidationError):
        from github_pr_kb.config import settings  # noqa: F401
```

**Alternative cleaner pattern (avoids module cache issues):**
```python
def test_settings_requires_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class IsolatedSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env")
        github_token: str

    with pytest.raises(ValidationError):
        IsolatedSettings()
```

The isolated class approach is simpler and avoids module cache concerns.

### .env.example
```bash
# Required: GitHub Personal Access Token with repo read permissions
# Generate at: https://github.com/settings/tokens
# Scopes needed: repo (or public_repo for public repos only)
GITHUB_TOKEN=your_github_token_here

# Future variables (added in their respective phases):
# ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Phase 4: Classification
```

### Stub module pattern
```python
"""
github_pr_kb.extractor
~~~~~~~~~~~~~~~~~~~~~~
Extracts PR comments from GitHub API using PyGithub.
Implemented in Phase 2.
"""
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip install -e .` + `requirements.txt` | `uv sync` + `pyproject.toml` only | 2023-2024 | Delete requirements.txt; no pip steps |
| `from pydantic import BaseSettings` | `from pydantic_settings import BaseSettings` | pydantic v2 (2023) | Separate package required |
| `setup.py` / `setup.cfg` | `pyproject.toml` only | PEP 517/518 (fully adopted ~2022) | No setup.py needed |
| `[project.optional-dependencies]` for dev | `[dependency-groups]` (PEP 735) | uv adopted ~2024 | Dev deps not published as package extras |
| PyGithub 1.x | PyGithub 2.x | 2023 | Breaking API changes; v1 docs are stale |
| flake8 + isort + black | ruff | 2022-2024 | Single tool replaces three; much faster |

**Deprecated/outdated:**
- `PyGithub==1.55` in requirements.txt: superseded by pyproject.toml with v2.x
- `from pydantic import BaseSettings`: removed in pydantic v2; import from `pydantic_settings`
- `pytest.ini` / `setup.cfg` for pytest config: use `[tool.pytest.ini_options]` in `pyproject.toml`

---

## Open Questions

1. **uv_build exact version range**
   - What we know: `uv_build` is the native backend; version tracks uv releases
   - What's unclear: Exact stable version number at time of writing (uv releases frequently)
   - Recommendation: Use `requires = ["uv_build"]` without version pin, or check `uv --version` at project init time and use the corresponding uv_build version

2. **pytest 9 requires Python >=3.10**
   - What we know: pytest 9.0.2 requires Python >=3.10; target is 3.11+ anyway
   - What's unclear: Nothing — 3.11+ satisfies this constraint
   - Recommendation: Confirm `requires-python = ">=3.11"` in pyproject.toml; this satisfies both pytest and pydantic v2

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 creates |
| Quick run command | `uv run pytest tests/test_config.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `uv sync` succeeds; all deps resolvable | smoke | `uv sync --frozen` | Wave 0 (pyproject.toml) |
| INFRA-04 | `.env.example` exists and documents GITHUB_TOKEN | file existence | `uv run pytest tests/test_config.py -k env_example` | Wave 0 |
| (Phase goal) | Missing GITHUB_TOKEN raises ValidationError | unit | `uv run pytest tests/test_config.py::test_settings_requires_github_token -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_config.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — empty, makes tests a package
- [ ] `tests/test_config.py` — covers INFRA-01 (config validation), INFRA-04 (env example exists)
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` section with `testpaths` and `addopts`
- [ ] Framework install: included in `[dependency-groups] dev` — no separate step

---

## Sources

### Primary (HIGH confidence)
- https://docs.astral.sh/uv/concepts/projects/dependencies/ — dependency-groups syntax, uv sync behavior
- https://docs.astral.sh/uv/concepts/build-backend/ — uv_build backend, src layout, minimal pyproject.toml
- https://docs.pydantic.dev/latest/concepts/pydantic_settings/ — BaseSettings, SettingsConfigDict, required fields, .env reading
- https://docs.astral.sh/ruff/configuration/ — [tool.ruff.lint] select syntax
- https://docs.pytest.org/en/stable/reference/customize.html — [tool.pytest.ini_options] configuration

### Secondary (MEDIUM confidence)
- https://pypi.org/project/PyGithub/ — confirmed v2.8.1 is current stable (verified PyPI directly)
- https://pypi.org/project/pydantic/ — confirmed v2.12.5
- https://pypi.org/project/pydantic-settings/ — confirmed v2.13.1
- https://pypi.org/project/anthropic/ — confirmed v0.84.0
- https://pypi.org/project/click/ — confirmed v8.3.1
- https://pypi.org/project/pytest/ — confirmed v9.0.2
- https://pypi.org/project/pytest-cov/ — confirmed v7.0.0
- https://pypi.org/project/ruff/ — confirmed v0.15.5

### Tertiary (LOW confidence)
- None — all claims verified against official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI directly on 2026-03-10
- Architecture: HIGH — pyproject.toml shape verified against uv official docs; pydantic-settings pattern verified against official docs
- Pitfalls: HIGH — PyGithub v1→v2 and pydantic BaseSettings import change verified against official sources; test isolation pitfall is a well-known pytest pattern

**Research date:** 2026-03-10
**Valid until:** 2026-06-10 (90 days — uv and pydantic-settings release frequently but APIs are stable)
