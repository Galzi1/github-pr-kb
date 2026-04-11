# Phase 8: GitHub Action + README - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08T21:10:54Z
**Phase:** 08-GitHub Action + README
**Areas discussed:** Incremental boundary, PR state scope, Publication mode, Bot PR behavior, State persistence, External state mechanism, README structure, Cache persistence, Cache reuse mechanism, Trigger model, Recovery cursor role

---

## Incremental boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Any PR updated since the last successful run | Reuses the extractor's current `updated_at` semantics and catches fresh discussion on older PRs | ✓ |
| Only PRs created since the last successful run | Lowest scope, but misses later activity on existing PRs | |
| Only PRs merged/closed since the last successful run | Stable lifecycle boundary, but narrower than current extractor behavior | |

**User's choice:** Any PR updated since the last successful run.
**Notes:** This was selected because it matches the current extractor behavior and avoids missing fresh comments on older PRs.

---

## PR state scope

| Option | Description | Selected |
|--------|-------------|----------|
| Closed/merged only | Focus on stable review history and avoid churn from in-progress PRs | ✓ |
| Open and closed PRs | Capture review knowledge earlier, but includes unstable PRs | |
| Use the extractor default of all states | Minimal workflow opinion, but broader than needed | |

**User's choice:** Closed/merged only.
**Notes:** This keeps automation focused on stable, merged-review knowledge.

---

## Publication mode

| Option | Description | Selected |
|--------|-------------|----------|
| Commit directly to the default branch | Most automatic, but least reviewable | |
| Open or update a bot PR with the KB changes | Keeps updates reviewable and visible | ✓ |
| Upload artifacts only | Avoids repo writes, but does not keep the KB in the repo | |

**User's choice:** Open or update a bot PR with the KB changes.
**Notes:** Reviewability matters more than fully hands-off direct commits.

---

## Bot PR behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Keep one rolling update PR and refresh it over time | One durable review surface for KB automation | ✓ |
| Open a fresh PR for each run with changes | Clear run boundaries, but creates more PR churn | |
| Skip when a KB PR already exists | Simple guard, but can leave the PR stale | |

**User's choice:** Open a PR if absent; otherwise update the existing open PR.
**Notes:** Interpreted as one rolling bot PR that is kept current over time.

---

## State persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Outside the tracked repo in GitHub-managed workflow state | Decouples progress tracking from KB PR merge timing | ✓ |
| In a state file inside the KB update PR | Transparent in git, but delayed until merge | |
| In a state file committed directly to default branch | Accurate cursor, but mixes publication modes | |

**User's choice:** Outside the tracked repo in GitHub-managed workflow state.
**Notes:** This keeps recovery state independent from the bot PR lifecycle.

---

## External state mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Repository variable updated by the workflow | Durable repo-scoped state without committing files | ✓ |
| Artifact file attached to workflow runs | Inspectable, but retention-based and less direct | |
| Actions cache entry | Fast, but less clear as a canonical cursor | |

**User's choice:** Repository variable updated by the workflow.
**Notes:** Chosen as the canonical recovery/backfill cursor.

---

## README structure

| Option | Description | Selected |
|--------|-------------|----------|
| Quickstart-first | Local setup and first run first, then automation | |
| Automation-first | GitHub Action setup first, local CLI usage after | ✓ |
| Reference-first | Concise overview, then full command/env/workflow reference | |

**User's choice:** Automation-first.
**Notes:** The README should lead with automation setup, then cover local usage and reference details.

---

## Cache persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Keep caches outside git using GitHub Actions cache/artifacts; commit only KB output | Matches current gitignore posture and keeps repo output focused | ✓ |
| Include cache files in the rolling KB bot PR too | Maximizes reproducibility, but adds noisy repo churn | |
| Do not persist caches across runs | Simplest, but wastes recomputation and API calls | |

**User's choice:** Keep caches outside git and commit only KB output.
**Notes:** The repo should stay clean; working caches should remain non-git state.

---

## Cache reuse mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Actions cache primary; artifacts only when useful for debugging | Optimizes normal reuse without artifact noise | ✓ |
| Artifacts only | More inspectable, but clunkier for normal reuse | |
| Always write both cache and artifacts on every run | Maximum traceability, but noisy and redundant | |

**User's choice:** Actions cache primary; artifacts only when useful for debugging.
**Notes:** Cache is the default persistence layer; artifacts are secondary.

---

## Trigger model

| Option | Description | Selected |
|--------|-------------|----------|
| Post-merge on merged PRs, plus manual workflow_dispatch | Event-driven automation tied to completed PRs | ✓ |
| Hybrid: post-merge primary, scheduled backstop, plus manual workflow_dispatch | More resilient, but keeps schedule complexity | |
| Keep the roadmap's schedule-based automation | Matches roadmap wording, but not the user's preferred trigger model | |

**User's choice:** Post-merge on merged PRs, plus manual workflow_dispatch.
**Notes:** The user explicitly prefers post-merge execution over a schedule.

---

## Recovery cursor role

| Option | Description | Selected |
|--------|-------------|----------|
| Keep it as a recovery/backfill cursor for manual runs | Normal events use PR context directly; manual runs use the cursor | ✓ |
| Do not use a cursor at all | Simpler, but weaker recovery/backfill story | |
| Use it for every run anyway | Keeps one model, but is unnecessary for event-driven runs | |

**User's choice:** Keep the repository variable as a recovery/backfill cursor for manual runs.
**Notes:** Post-merge events should use event context directly; the variable exists for manual recovery paths.

---

## the agent's Discretion

- Exact YAML event filters and condition expressions
- Exact PR title/branch naming for the rolling bot PR
- Exact manual-dispatch inputs for recovery mode
- Exact README section headings and example formatting

## Deferred Ideas

None
