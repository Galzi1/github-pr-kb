---
phase: 6
slug: cli-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_cli.py -x` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_cli.py -x`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CLI-01 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_runs -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | CLI-01 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_missing_repo -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | CLI-02 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_classify_runs -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | CLI-03 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_generate_runs -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | CLI-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py -k "help" -x` | ❌ W0 | ⬜ pending |
| 06-01-06 | 01 | 1 | CLI-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_missing_token -x` | ❌ W0 | ⬜ pending |
| 06-01-07 | 01 | 1 | CLI-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_bad_date -x` | ❌ W0 | ⬜ pending |
| 06-01-08 | 01 | 1 | D-01 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_run_pipelines -x` | ❌ W0 | ⬜ pending |
| 06-01-09 | 01 | 1 | D-10 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_run_fails_fast -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli.py` — stubs for CLI-01 through CLI-04 requirements

*Existing infrastructure covers framework and fixture needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
