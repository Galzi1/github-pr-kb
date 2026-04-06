# Phase 6: CLI Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 06-cli-integration
**Areas discussed:** Command scope, Flag design, Output & feedback, Error handling, Pipeline command behavior

---

## Command Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Three commands only | Just extract, classify, generate. Matches requirements exactly. | |
| Three + run command | Add a 'run' command that calls all three in sequence. | :heavy_check_mark: |
| You decide | Claude picks what fits best. | |

**User's choice:** Three + run command
**Notes:** None

### Follow-up: Run command flags

| Option | Description | Selected |
|--------|-------------|----------|
| --repo only | run --repo owner/name uses defaults for everything else. | :heavy_check_mark: |
| Pass-through all flags | run accepts all flags from sub-commands and forwards them. | |
| You decide | Claude picks the right balance. | |

**User's choice:** --repo only
**Notes:** Keep it dead simple for the common case.

---

## Flag Design

### Extract command flags

| Option | Description | Selected |
|--------|-------------|----------|
| All three filters | --repo (required), --state, --since, --until. Matches CORE-02. | :heavy_check_mark: |
| --repo only | Minimal -- just --repo. Filters added later. | |
| You decide | Claude picks based on extractor support. | |

**User's choice:** All three filters
**Notes:** None

### Directory flags for classify/generate

| Option | Description | Selected |
|--------|-------------|----------|
| Config-only | Cache dir and output dir stay as Settings defaults via .env. | :heavy_check_mark: |
| Expose as flags | --cache-dir on classify/generate, --output-dir on generate. | |
| You decide | Claude picks what fits project conventions. | |

**User's choice:** Config-only
**Notes:** Less flag clutter for the common case.

---

## Output & Feedback

### Verbosity

| Option | Description | Selected |
|--------|-------------|----------|
| Quiet + summary | Minimal during execution, summary at end. | |
| Verbose by default | Log each item as processed. | |
| Silent + --verbose flag | No output by default, --verbose for detail. | :heavy_check_mark: |

**User's choice:** Silent + --verbose flag, BUT always print a summary line at the end even when not in verbose mode.
**Notes:** User specifically requested the summary line always appears regardless of verbose setting.

### Colored output

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with Click styling | Use click.style() with terminal detection. | :heavy_check_mark: |
| No colors | Plain text only. | |
| You decide | Claude picks based on Click conventions. | |

**User's choice:** Yes, with Click styling
**Notes:** None

---

## Error Handling

### Module-level Settings crash

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy import Settings | Import inside each command function, catch ValidationError. | :heavy_check_mark: |
| Top-level try/except | Wrap cli group in try/except at module level. | |
| You decide | Claude picks the cleanest approach. | |

**User's choice:** Lazy import Settings
**Notes:** None

### Runtime error style

| Option | Description | Selected |
|--------|-------------|----------|
| Error + fix hint | Print error and a one-line hint pointing to the fix. No traceback. | :heavy_check_mark: |
| Error only | Print just the error message, no hints. | |
| You decide | Claude picks the right balance for CLI-04. | |

**User's choice:** Error + fix hint
**Notes:** None

---

## Pipeline Command Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Stop immediately | Fail fast, print what succeeded and what failed, exit non-zero. | :heavy_check_mark: |
| Continue with partial results | Skip failed step and continue. | |
| You decide | Claude picks what makes sense. | |

**User's choice:** Stop immediately
**Notes:** Cached data from earlier steps is preserved for re-runs.

---

## Claude's Discretion

- Help text detail level and example usage
- Whether --verbose wires into Python logging or CLI-level prints
- Click group structure
- Exact summary message format

## Deferred Ideas

None -- discussion stayed within phase scope
