# Risk Review: 08-01-PLAN.md

## Verdict

**Not ready as written.** The core idea is good, but the current manual cursor formula appears to contradict the plan's own non-regression goal, and concurrency plus timestamp-source risks are not specified tightly enough yet.

**Overall risk level:** High

## Plan Summary

The plan proposes a small Python helper, `src\github_pr_kb\action_state.py`, plus focused unit tests in `tests\test_action_state.py`, to decide whether the GitHub Action should run, which `extract_since` value to use, and which `next_cursor` value to emit for auto merged-PR runs and manual recovery runs.

The intended benefit is to move skip/cursor logic out of YAML and into pytest-covered Python while leaving repository-variable writes to a later workflow step.

## Assumptions and Evidence

| ID | Assumption | Explicit / Implicit | Justification status | Blast radius if wrong | Early validation |
|---|---|---|---|---|---|
| A1 | Workflow can supply `event_updated_at` and `latest_merged_at` with the same `updated_at` semantics used by the extractor. | Implicit | Partial | High | Lock exact source fields in the workflow contract. |
| A2 | `next_cursor = max(manual_since, latest_merged_at)` is non-regressing for manual runs. | Explicit | Unjustified / contradicted | Critical | Add a test where `stored_cursor` is newer than both values. |
| A3 | Auto `next_cursor = event_updated_at` is safe under burst merges, reruns, and out-of-order completion. | Implicit | Weak | High | Model concurrent merged events against the same stored cursor. |
| A4 | JSON keys alone are a sufficient workflow contract. | Explicit | Partial | Medium | Add malformed-input, null, and exit-code contract tests. |
| A5 | `python -m github_pr_kb.action_state` can run without config/env side effects. | Implicit | Weak | Medium | Run it in a minimal environment with only its own flags. |
| A6 | Unit tests alone are enough for this plan stage. | Explicit | Mostly reasonable but incomplete | Medium | Require a workflow-consumer smoke test in 08-02. |

## Devil's Advocacy

### Inversion

1. Moving logic into Python may reduce YAML complexity while still increasing overall system risk if the real contract is split across Python decision code and underspecified workflow timestamp sourcing.
2. Using `event_updated_at` as the auto cursor may prevent self-skip for one run while still allowing cursor lag or regression when merged-event runs overlap.
3. Manual override may improve recovery ergonomics while also making it easier to corrupt durable state if the emitted cursor can move backward.

### Outsider questions

- Which timestamp is authoritative: event payload time, latest merged PR time, or stored cursor?
- What happens when two merge-triggered runs overlap and finish out of order?
- What prevents a bad `workflow_dispatch` input from regressing or freezing automation state?

### Failure-of-imagination scenarios

- A successful manual backfill with an old `manual_since` lowers the durable cursor and causes old PRs to be reprocessed.
- Two PRs merge close together, both runs read the same stored cursor, and the older event finishes last and writes the smaller cursor.
- The workflow computes `latest_merged_at` from a field that does not match extractor `updated_at` semantics, so helper decisions are internally consistent but operationally wrong.

## Risk Register

| Risk ID | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Operational | Manual backfill can regress the saved cursor because the proposed manual formula ignores a newer `stored_cursor`. | `manual_since` is older than `stored_cursor` and no newer `latest_merged_at` exists. | High | Critical | Critical | Stored cursor decreases after manual success. | Compute manual `next_cursor` as `max(stored_cursor, manual_since, latest_merged_at)` or enforce monotonic writes in workflow. | Repair the repo variable and rerun recovery. | A2 |
| R2 | Operational | Concurrent or out-of-order merged-event runs can regress or lag the cursor because auto `next_cursor` is only the event time. | Multiple merges occur close together and workflows overlap. | Medium | High | High | Cursor moves backward or repeated runs cover the same window. | Add workflow concurrency and monotonic cursor persistence. | Re-run with corrected cursor. | A3 |
| R3 | Technical | Helper decisions can drift from extractor behavior if workflow timestamps use different semantics than extractor `updated_at`. | Workflow uses a different field or timezone treatment. | Medium | High | High | No-op decisions when new PRs exist, or empty extracts after `should_run=true`. | Define exact upstream source fields and add a downstream contract test in 08-02. | Manual backfill while fixing the mapping. | A1 |
| R4 | Technical | Malformed, naive, or future timestamps may produce brittle behavior because tests do not yet lock error/output handling. | Bad workflow input or bad manual dispatch value. | Medium | Medium | Medium | Traceback-like failures or implausible cursor output. | Add explicit malformed-input and normalization tests. | Fail closed and avoid cursor persistence on parse errors. | A4 |
| R5 | Organizational | The helper may accidentally import env-bound config surfaces and fail in contexts that do not need repo/API secrets. | `action_state.py` imports modules that instantiate settings at import time. | Medium | Medium | Medium | `python -m github_pr_kb.action_state` fails before arg parsing. | Keep the module standalone and config-free. | Refactor helper imports. | A5 |
| R6 | Technical | Unit tests can pass while the workflow consumer still breaks on JSON parsing, null handling, or shell quoting. | Later YAML consumer interprets helper output differently. | Medium | Medium | Medium | Workflow step fails despite green unit tests. | Add one workflow-consumer smoke test in 08-02. | Patch the workflow consumer. | A6 |

## Recommended Changes Before Implementation

1. Fix the manual cursor formula so successful manual runs cannot move durable state backward.
2. Add a test where `stored_cursor` is newer than both `manual_since` and `latest_merged_at`.
3. Treat cursor persistence as its own safety contract: workflow writes should be monotonic relative to current stored state.
4. Specify the exact source fields for `event_updated_at` and `latest_merged_at`, including timezone expectations.
5. Lock malformed-input behavior: deterministic error surface, null encoding, and exit behavior.
6. State explicitly that `action_state.py` must remain import-safe without unrelated env vars.

## What the Plan Does Well

- It isolates the hardest decision logic from opaque YAML into a testable Python surface.
- It keeps repository-variable writes out of the helper, which is the right separation of concerns.
- It correctly identifies timestamp parsing and skip logic as the threat-bearing surfaces.
