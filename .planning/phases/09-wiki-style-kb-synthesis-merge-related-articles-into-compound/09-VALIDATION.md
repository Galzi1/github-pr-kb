---
phase: 9
slug: wiki-style-kb-synthesis-merge-related-articles-into-compound
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 09-01-01 | 01 | 1 | D-08 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "manifest"` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | D-09 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "migration"` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | D-05, D-06 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "topic_plan"` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | D-01, D-02 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "synthesize"` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | D-10, D-11 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "cross_ref"` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 2 | D-12 | - | N/A | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "index"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_topic_synthesis.py` - stubs for D-01 through D-07 (topic planning and synthesis)
- [ ] `tests/test_manifest_v2.py` - stubs for D-08, D-09 (manifest format and migration)
- [ ] `tests/test_cross_references.py` - stubs for D-10, D-11 (cross-ref generation and validation)
- [ ] `tests/test_index_topics.py` - stubs for D-12 (index generation with topic pages)

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
