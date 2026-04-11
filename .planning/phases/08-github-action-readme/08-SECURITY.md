---
phase: 8
slug: github-action-readme
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-11
updated: 2026-04-11
---

# Phase 8 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| workflow inputs -> action_state helper | GitHub event payload fields and manual dispatch inputs drive skip/cursor decisions | `pull_request.updated_at`, `latest_merged_at`, `manual_since`, `force`, stored cursor |
| action_state helper -> workflow outputs | Helper output decides whether the pipeline runs and what cursor candidate may be persisted | `should_run`, `extract_since`, `next_cursor`, `reason` |
| workflow job -> repository variable API | The workflow writes durable incremental state outside git | `KB_LAST_SUCCESSFUL_CURSOR` |
| workflow job -> rolling PR branch | The workflow can publish tracked KB output to a dedicated branch and PR | `kb/INDEX.md`, `kb/**/*.md`, `kb/.manifest.json` |
| README guidance -> maintainer setup | Documentation influences token setup, workflow bootstrap, and repo hygiene in consumer repos | workflow file path, secret names, `KB_TOOL_REPOSITORY`, `KB_TOOL_REF`, token roles |
| README env docs -> local CLI usage | Users populate local config and run commands from the documented env surface | `.env.example`, local tokens, CLI commands, platform-specific test commands |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-08-01 | T | `src/github_pr_kb/action_state.py` timestamp parsing and input contract | mitigate | `action_state.py` normalizes timestamps to UTC, rejects malformed or timezone-naive input, and `tests/test_action_state.py` locks deterministic CLI failure behavior. | closed |
| T-08-02 | D | manual dispatch skip/cursor logic | mitigate | Manual no-new-PR short-circuit, `force` bypass, and non-regressing `next_cursor` behavior are implemented in `action_state.py` and covered by `tests/test_action_state.py`. | closed |
| T-08-03 | R | helper output -> workflow persistence handoff | mitigate | `action_state.py` documents `next_cursor` as candidate-only, and `.github/workflows/github-pr-kb.yml` re-reads the stored cursor and persists the monotonic max under workflow concurrency. | closed |
| T-08-04 | S | variable-auth token selection | mitigate | `.github/workflows/github-pr-kb.yml` prefers the GitHub App path when app secrets are present, falls back to `KB_VARIABLES_TOKEN`, and fails closed when neither auth path is configured; `tests/test_action_workflow.py` covers the contract. | closed |
| T-08-05 | T | cursor persistence step | mitigate | The workflow writes `KB_LAST_SUCCESSFUL_CURSOR` only after extract/classify/generate and publication steps succeed, preventing premature state advancement. | closed |
| T-08-06 | I | git publication scope | mitigate | The workflow stages only `kb/INDEX.md`, `kb/.manifest.json`, and `kb/**/*.md`; it does not stage `.github-pr-kb/cache/`, and workflow tests verify the staging contract. | closed |
| T-08-07 | D | rerun/no-new-PR behavior | mitigate | The workflow invokes `python -m github_pr_kb.action_state` before the CLI pipeline and exits early on no-op runs; helper and workflow tests both cover this guard. | closed |
| T-08-08 | T | out-of-order workflow completion | mitigate | Workflow-level concurrency plus post-publication fresh-read/max-write cursor persistence prevent overlapping runs from regressing durable state. | closed |
| T-08-09 | S | external workflow/tool refs | mitigate | `.github/workflows/github-pr-kb.yml` pins third-party actions by full commit SHA and treats `KB_TOOL_REF` as an immutable pinned tool reference; tests assert the pinned contract. | closed |
| T-08-10 | D | rolling PR branch drift/conflict | mitigate | The workflow uses dedicated branch `automation/github-pr-kb`, updates it with a bounded safe strategy, and performs cursor persistence only after publication succeeds. | closed |
| T-08-08-docs | S | auth setup documentation | mitigate | `README.md` documents PAT quickstart before the GitHub App path, names the exact workflow-only secrets, separates local/runtime auth from repository-variable auth, and explains the internal `GH_TOKEN` mapping; `tests/test_readme.py` verifies those promises. | closed |
| T-08-09-docs | T | repo hygiene documentation | mitigate | `README.md` includes explicit committed-vs-not-committed guidance covering `kb/` output, `kb/.manifest.json`, and `.github-pr-kb/cache/`; `tests/test_readme.py` enforces it. | closed |
| T-08-10-docs | I | README and `.env.example` examples | mitigate | `README.md` and `.env.example` align on the local config surface and explicitly keep workflow-only secrets out of `.env`; README review shows no stale architecture/setup claims remain. | closed |
| T-08-11 | D | platform-specific local guidance | mitigate | `README.md` provides distinct Windows and macOS/Linux setup and test commands so the onboarding path does not assume one platform as universal. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-11 | 14 | 14 | 0 | Copilot |

No `## Threat Flags` sections were present in the Phase 8 summary artifacts, so the audit was based on the plan threat models plus the implemented workflow, helper, docs, and tests.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-11
