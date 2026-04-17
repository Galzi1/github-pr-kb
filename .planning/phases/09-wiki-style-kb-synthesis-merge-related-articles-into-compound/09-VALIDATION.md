---
phase: 9
slug: wiki-style-kb-synthesis-merge-related-articles-into-compound
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
---

# Phase 9 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/ -x -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/ -x -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | D-07, D-08 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x -q --no-cov -k "topic_group or topic_plan"` | ✅ | ⬜ pending |
| 09-01-02 | 01 | 1 | D-08, D-09 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x -q --no-cov -k "manifest_migration or manifest_new or plan_topics or sources_hash"` | ✅ | ⬜ pending |
| 09-02-01 | 02 | 2 | D-01, D-02, D-03, D-04, D-06, D-10 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x -q --no-cov -k "synthesize_topic or collect_in_memory or build_topic or topic_page"` | ✅ | ⬜ pending |
| 09-02-02 | 02 | 2 | D-11 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x -q --no-cov -k "strip_broken_link"` | ✅ | ⬜ pending |
| 09-03-01 | 03 | 3 | D-05, D-12 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x -q --no-cov -k "generate_all_with_synthesis or generate_all_no_synthesis or index_topic_pages"` | ✅ | ⬜ pending |
| 09-03-02 | 03 | 3 | D-05 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py -x -q --no-cov -k "no_synthesize or generate"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Tests are added to existing files:
- [x] `tests/test_generator.py` - topic models, manifest migration, synthesis, cross-refs, index (D-01 through D-12)
- [x] `tests/test_cli.py` - `--no-synthesize` flag (D-05)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Topic page prose quality | D-01, D-04 | Subjective synthesis quality | Read 3 generated topic pages, verify inline citations and natural flow |
| Cross-reference relevance | D-10 | Semantic relevance assessment | Verify linked topics are actually related, not just keyword matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
