---
phase: 1
slug: project-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 creates |
| **Quick run command** | `uv run pytest tests/test_config.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_config.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | INFRA-01 | smoke | `uv sync --frozen` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | INFRA-04 | file existence | `uv run pytest tests/test_config.py -k env_example` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | INFRA-01 | unit | `uv run pytest tests/test_config.py::test_settings_requires_github_token -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — empty, makes tests a package
- [ ] `tests/test_config.py` — stubs for INFRA-01 (ValidationError on missing token), INFRA-04 (env example exists)
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `addopts = "--cov=github_pr_kb --cov-report=term-missing"`
- [ ] `[dependency-groups] dev` includes `pytest>=9.0.2`, `pytest-cov>=7.0.0`, `ruff>=0.15.5`

*Framework install: included in `[dependency-groups] dev` — no separate install step needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `uv sync` from fresh clone succeeds | INFRA-01 | Requires actual clone + uv install on clean machine | Clone repo to temp dir, run `uv sync`, verify venv created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
