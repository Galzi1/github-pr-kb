---
phase: 8
slug: github-action-readme
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
updated: 2026-04-11
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest tests\test_action_state.py tests\test_action_workflow.py tests\test_readme.py -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~3.59s targeted / ~6.67s full (observed on 2026-04-11) |

---

## Sampling Rate

- **After every task commit:** Run the targeted pytest file for the touched Phase 8 surface (`test_action_state.py`, `test_action_workflow.py`, or `test_readme.py`).
- **After every plan wave:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** ~7 seconds for the full pytest audit in this repository.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | ACTION-02, ACTION-03 | T-08-01, T-08-02 | Auto and manual cursor decisions are deterministic, reject malformed timestamps, and no-op repeated auto events instead of rerunning expensive work. | unit | `.\.venv\Scripts\python.exe -m pytest tests\test_action_state.py -x -q` | ✅ | ✅ green |
| 08-01-02 | 01 | 1 | ACTION-02, ACTION-03 | T-08-01, T-08-02, T-08-03 | `python -m github_pr_kb.action_state` stays import-safe, emits candidate-only cursor JSON, and preserves non-regressing manual state. | unit | `.\.venv\Scripts\python.exe -m pytest tests\test_action_state.py -x -q` | ✅ | ✅ green |
| 08-02-01 | 02 | 2 | ACTION-01, ACTION-02, ACTION-03 | T-08-04, T-08-07, T-08-08, T-08-09 | The shipped workflow is copyable, pinned, concurrency-safe, and correctly wired to helper execution plus workflow auth paths. | contract | `.\.venv\Scripts\python.exe -m pytest tests\test_action_workflow.py -x -q` | ✅ | ✅ green |
| 08-02-02 | 02 | 2 | ACTION-01, ACTION-02, ACTION-03 | T-08-05, T-08-06, T-08-08, T-08-10 | Publication stages only KB artifacts, reuses the rolling automation PR, and persists `KB_LAST_SUCCESSFUL_CURSOR` only after successful publication with monotonic max semantics. | contract | `.\.venv\Scripts\python.exe -m pytest tests\test_action_workflow.py -x -q` | ✅ | ✅ green |
| 08-03-01 | 03 | 3 | INFRA-03 | T-08-08-docs, T-08-09-docs, T-08-10-docs | README and `.env.example` stay aligned with the shipped workflow, local config surface, and committed-vs-not-committed guidance. | docs contract | `.\.venv\Scripts\python.exe -m pytest tests\test_readme.py -x -q` | ✅ | ✅ green |
| 08-03-02 | 03 | 3 | INFRA-03 | T-08-11 | Local onboarding remains platform-aware and documents install, env vars, CLI commands, and KB output examples. | docs contract | `.\.venv\Scripts\python.exe -m pytest tests\test_readme.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Field Validation Evidence

Phase 8 also has live consumer-repo validation in `Galzi1/github-pr-kb-demo`, which supplements the automated Nyquist map above:

| Behavior | Evidence | Result |
|----------|----------|--------|
| Fresh feature PR with human review comments is ingested into the pipeline | Demo PR `#10` | Pass |
| Final workflow replay on corrected tool SHA | Run `24277455924` | Pass |
| Generated KB PR opened with real article files | Demo PR `#11` | Pass |
| Generated KB PR merged cleanly | Demo PR `#11` merged | Pass |
| Post-merge steady-state run completes without automation churn | Run `24277477172` | Pass |

This supports the strongest claim that Phase 8 is validated as a **happy-path end-to-end consumer workflow**, while the Nyquist audit confirms every planned requirement already has automated verification in-repo.

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Audit notes:

- `workflow.nyquist_validation` is enabled.
- Existing `08-VALIDATION.md` evidence was audited and converted into the structured Nyquist format.
- Automated coverage remains green via:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_action_state.py tests\test_action_workflow.py tests\test_readme.py -q`
  - `.\.venv\Scripts\python.exe -m pytest tests -q`

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-11
