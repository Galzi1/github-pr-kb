---
phase: 5
slug: kb-generator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | KB-01 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_generate_creates_category_subdirs -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | KB-01 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_article_written_to_category_subdir -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | KB-02 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_article_frontmatter_fields -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | KB-02 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_diff_hunk_in_review_comment -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | KB-02 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_no_diff_hunk_for_issue_comment -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | KB-03 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_index_file_created -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | KB-03 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_index_grouped_by_category -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 1 | KB-03 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_index_review_marker -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | KB-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_incremental_no_duplicate -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 2 | KB-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_incremental_adds_new_articles -x` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 2 | KB-04 | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_manifest_written -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_generator.py` — stubs for KB-01 through KB-04 (entire file is new)
- No new framework or fixture infrastructure needed — `conftest.py` already sets env vars; generator tests use `tmp_path` only

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
