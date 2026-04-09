---
phase: 8
slug: github-action-readme
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/ -k "workflow or action or readme or cursor" -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/ -k "workflow or action or readme or cursor" -q`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 0 | ACTION-01 | unit / file assertion | `.venv/Scripts/python.exe -m pytest tests/ -k "workflow and trigger" -q` | Likely W0 | pending |
| 08-01-02 | 01 | 0 | ACTION-02 | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "no_new_pr or cost_guard" -q` | Likely W0 | pending |
| 08-01-03 | 01 | 0 | ACTION-03 | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "cursor or state" -q` | Likely W0 | pending |
| 08-01-04 | 01 | 0 | ACTION-01/ACTION-03 | integration-lite | `.venv/Scripts/python.exe -m pytest tests/ -k "cache or manifest" -q` | Likely W0 | pending |
| 08-02-01 | 02 | 1 | INFRA-03 | doc contract | `.venv/Scripts/python.exe -m pytest tests/ -k "readme" -q` | Likely W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] Workflow/state decision tests for merged-only trigger, cursor handling, and cost guard
- [ ] README contract coverage if docs expectations are not already asserted elsewhere

*Existing infrastructure covers framework and fixtures. Phase 8 should add tests, not new tooling.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rolling bot PR is created once and updated on subsequent successful runs | ACTION-01 | Requires live GitHub PR behavior | Run `workflow_dispatch` in a test repo twice and confirm one open KB PR is updated rather than duplicated |
| No-new-PR run skips extract/classify/generate work in a real repository | ACTION-02 | Requires live workflow/event context | Trigger the workflow with the saved cursor newer than all merged PRs and confirm the pipeline exits without KB changes |
| Dual auth setup docs are understandable for maintainers | INFRA-03 | Human readability / setup burden | Follow the README once with PAT path and once with GitHub App path in a test repo |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
