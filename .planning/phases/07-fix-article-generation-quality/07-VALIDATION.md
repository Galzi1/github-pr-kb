---
phase: 7
slug: fix-article-generation-quality
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_generator.py tests/test_classifier.py tests/test_cli.py -x -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_classifier_integration.py --ignore=tests/test_extractor_integration.py -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_generator.py tests/test_classifier.py tests/test_cli.py -x -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_classifier_integration.py --ignore=tests/test_extractor_integration.py -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 0 | D-01/D-04 | unit (mock) | `pytest tests/test_generator.py::test_article_body_is_synthesized -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 0 | D-02 | unit (mock) | `pytest tests/test_generator.py::test_category_sections_in_article -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 0 | D-06 | unit | `pytest tests/test_generator.py::test_generate_model_env_var -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 0 | D-07 | unit | `pytest tests/test_classifier.py::test_parse_failure_returns_none -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 0 | D-08 | unit | `pytest tests/test_classifier.py::test_load_index_filters_failed -x` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 0 | D-10 | unit | `pytest tests/test_cli.py::test_generate_cli_filtered_count -x` | ❌ W0 | ⬜ pending |
| 07-01-07 | 01 | 0 | D-11 | unit | `pytest tests/test_cli.py::test_classify_cli_failed_count -x` | ❌ W0 | ⬜ pending |
| 07-01-08 | 01 | 0 | D-14 | unit | `pytest tests/test_generator.py::test_low_confidence_filtered -x` | ❌ W0 | ⬜ pending |
| 07-01-09 | 01 | 0 | D-15 | unit (mock) | `pytest tests/test_generator.py::test_synthesis_failure_skipped -x` | ❌ W0 | ⬜ pending |
| 07-01-10 | 01 | 0 | D-16 | unit | `pytest tests/test_generator.py::test_regenerate_flag -x` | ❌ W0 | ⬜ pending |
| 07-01-11 | 01 | 0 | D-17 | unit | `pytest tests/test_generator.py::test_generate_requires_api_key -x` | ❌ W0 | ⬜ pending |
| 07-01-12 | 01 | 0 | D-04 | unit update | `pytest tests/test_generator.py::test_article_body_contains_comment -x` | ✅ (update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_generator.py::test_article_body_is_synthesized` — D-01/D-04 stub
- [ ] `tests/test_generator.py::test_category_sections_in_article` — D-02 stub
- [ ] `tests/test_generator.py::test_generate_model_env_var` — D-06 stub
- [ ] `tests/test_generator.py::test_low_confidence_filtered` — D-14 stub
- [ ] `tests/test_generator.py::test_synthesis_failure_skipped` — D-15 stub
- [ ] `tests/test_generator.py::test_regenerate_flag` — D-16 stub
- [ ] `tests/test_generator.py::test_generate_requires_api_key` — D-17 stub
- [ ] `tests/test_classifier.py::test_parse_failure_returns_none` — D-07 stub
- [ ] `tests/test_classifier.py::test_load_index_filters_failed` — D-08 stub
- [ ] `tests/test_cli.py::test_generate_cli_filtered_count` — D-10 stub
- [ ] `tests/test_cli.py::test_classify_cli_failed_count` — D-11 stub
- [ ] Update `tests/test_generator.py::test_article_body_contains_comment` — D-04 invalidates current assertion

*Existing infrastructure covers framework and fixtures. Only new test functions needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
