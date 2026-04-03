# Phase 2: GitHub Extraction Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 02-github-extraction-core
**Areas discussed:** Storage format, Data model shape, Extraction scope, Filter behavior

---

## Storage Format

### Q1: How should extracted PR data be organized on disk?

| Option | Description | Selected |
|--------|-------------|----------|
| Single JSON file | One file like .cache/extractions.json with all PRs and comments | |
| Per-PR JSON files | One file per PR like .cache/pr-42.json | |
| Per-repo directory + index | Directory per repo with index.json and individual PR files | |

**User's choice:** Per-PR JSON files — but only after asking how the system interacts with the data store. The pipeline's 3-stage architecture (extract → classify → generate) made per-PR files the natural fit: incrementally written, independently readable, no bloated monolith.
**Notes:** User was concerned about ending up with "a huge JSON file containing tons of redundant information." The per-PR layout directly addresses this.

### Q2: Where should the cache directory live?

| Option | Description | Selected |
|--------|-------------|----------|
| .github-pr-kb/ in project root | Matches tool name, easy to gitignore | ✓ |
| .cache/ in project root | Generic name, might collide | |
| Configurable via Settings | Add cache_dir to pydantic Settings | |

**User's choice:** .github-pr-kb/ in project root

---

## Data Model Shape

### Q3: How much PR metadata should we store alongside comments?

| Option | Description | Selected |
|--------|-------------|----------|
| Lean: PR number + title + comments | Minimal but sufficient for classification and KB | |
| Rich: Full PR context | Labels, reviewers, branch names, diff stats | |
| Minimal: Comments only | Just comment text + author + timestamp | |

**User's choice:** Lean model, plus PR description/body. Rationale: PR description often contains the "why" behind changes, valuable context for classification.

### Q4: What fields per comment?

| Option | Description | Selected |
|--------|-------------|----------|
| Standard set | ID, author, body, timestamp, URL | |
| Standard + diff context | Above, plus file path and diff hunk for review comments | |
| Standard + reactions | Above, plus reaction counts | |

**User's choice:** All three combined — standard + diff context + reactions. Maximum signal for the classifier.

---

## Extraction Scope

### Q5: Which comment types should the extractor capture?

| Option | Description | Selected |
|--------|-------------|----------|
| Review comments (inline) | Comments on specific code lines | ✓ |
| Issue comments (thread) | General PR thread discussion | ✓ |
| Review summaries | Top-level review body (approve/changes) | |
| PR body as a comment | Treat PR description as classifiable | |

**User's choice:** Review comments + issue comments only.

### Q6: Filter out low-value comments during extraction?

| Option | Description | Selected |
|--------|-------------|----------|
| Extract all, classify later | Capture everything, let classifier sort it | |
| Pre-filter obvious noise | Skip bot comments, single-word replies | ✓ |

**User's choice:** Pre-filter, but with an important distinction: skip generic CI/automation bots but KEEP code review agent comments (Copilot reviewer, CodeRabbit, etc.) because they contain real code insights.

---

## Filter Behavior

### Q7: What should "date range" filter on?

| Option | Description | Selected |
|--------|-------------|----------|
| PR updated_at | Catches PRs with recent activity | ✓ |
| PR created_at | Simple mental model but misses old PRs with new discussion | |
| Comment created_at | Most precise but requires fetching PR first | |

**User's choice:** PR updated_at

### Q8: API-level or fetch-then-filter?

| Option | Description | Selected |
|--------|-------------|----------|
| API-level filtering | Use PyGithub params, stop at date boundary | ✓ |
| Fetch all, filter locally | Simpler code but wastes API quota | |

**User's choice:** API-level filtering

---

## Claude's Discretion

- JSON schema field names and nesting
- Pydantic models vs plain dicts for serialization
- Edge case handling (zero comments, deleted comments, long bodies)
- pytest-mock vs unittest.mock
- Specific bot account filter list

## Deferred Ideas

None — discussion stayed within phase scope.
