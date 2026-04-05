---
phase: 4
slug: claude-classifier
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/ -x -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/ -x -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CLASS-01 | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py -k "test_classify" -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CLASS-02 | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py -k "test_confidence" -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | CLASS-03 | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py -k "test_cache" -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | CLASS-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py -k "test_output" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_classifier.py` — stubs for CLASS-01 through CLASS-04
- [ ] `tests/conftest.py` — add `ANTHROPIC_API_KEY` env var (same pattern as GITHUB_TOKEN)

*Existing pytest infrastructure covers framework needs.*

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
