---
phase: 3
slug: extraction-resilience-cache
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py -x` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_extractor.py -x`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | CORE-03 | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_rate_limit_exhaustion -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 0 | CORE-03 | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_rate_limit_partial_flush -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 0 | CORE-04 | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_outside_window_not_fetched -x` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 0 | CORE-04 | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_inside_window_comments_merged -x` | ❌ W0 | ⬜ pending |
| 3-01-05 | 01 | 0 | CORE-05 | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_no_duplicate_comment_ids -x` | ❌ W0 | ⬜ pending |
| 3-01-06 | 01 | 0 | CORE-05 | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_merge_appends_new_only -x` | ❌ W0 | ⬜ pending |
| 3-01-07 | 01 | 0 | D-06 | unit | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_atomic_write_no_partial_file -x` | ❌ W0 | ⬜ pending |
| 3-01-08 | 01 | 0 | D-06 | unit | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_corrupt_cache_full_fetch -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_extractor.py::test_rate_limit_exhaustion` — covers CORE-03 (mock `RetryError`, assert `RateLimitExhaustedError`)
- [ ] `tests/test_extractor.py::test_rate_limit_partial_flush` — covers CORE-03 (2 PRs processed before error, verify both cache files written)
- [ ] `tests/test_extractor.py::test_outside_window_not_fetched` — covers CORE-04 (PR outside `since`/`until` with existing cache → API not called)
- [ ] `tests/test_extractor.py::test_inside_window_comments_merged` — covers CORE-04 (existing cache + new PR comments → merged file)
- [ ] `tests/test_extractor.py::test_no_duplicate_comment_ids` — covers CORE-05 (identical comment IDs on re-run → count unchanged)
- [ ] `tests/test_extractor.py::test_merge_appends_new_only` — covers CORE-05 (2 existing + 1 new → 3 total, not 4)
- [ ] `tests/test_extractor.py::test_atomic_write_no_partial_file` — covers D-06 (verify write_atomic leaves no .tmp file on success)
- [ ] `tests/test_extractor.py::test_corrupt_cache_full_fetch` — covers Pitfall 4 (put corrupted JSON in cache dir → extractor treats as missing)

*All 8 tests to be added in Wave 0 to `tests/test_extractor.py` (continuing established pattern). No new test files or fixtures required.*

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
