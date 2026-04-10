---
status: testing
phase: 08-github-action-readme
source:
  - 08-01-SUMMARY.md
  - 08-02-SUMMARY.md
  - 08-03-SUMMARY.md
started: 2026-04-10T09:49:16Z
updated: 2026-04-10T09:49:16Z
---

## Current Test

number: 1
name: Copyable workflow bootstrap
expected: |
  The shipped `.github/workflows/github-pr-kb.yml` can be copied into another repository, triggers on merged PRs plus `workflow_dispatch`, and bootstraps this tool from `.github-pr-kb-tool` using `KB_TOOL_REPOSITORY` and `KB_TOOL_REF` instead of assuming the consumer repo vendors this package.
awaiting: user response

## Tests

### 1. Copyable workflow bootstrap
expected: The shipped workflow is copy-ready for consumer repos and bootstraps the tool from `.github-pr-kb-tool` via `KB_TOOL_REPOSITORY` and `KB_TOOL_REF`.
result: pending

### 2. No-new-PR guard and cursor contract
expected: Repeated merged events and manual no-new-PR runs skip before extract/classify/generate, and successful runs use `KB_LAST_SUCCESSFUL_CURSOR` as a monotonic state boundary.
result: pending

### 3. Workflow auth and publication contract
expected: The workflow clearly separates CLI/runtime auth from repository-variable auth, stages only `kb/` output plus `kb/.manifest.json`, and uses one rolling PR on `automation/github-pr-kb`.
result: pending

### 4. README local onboarding
expected: README leads with automation, then gives local uv install, env vars, CLI commands, KB output example, and committed-vs-not-committed guidance that matches the shipped workflow.
result: pending

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

None yet.
