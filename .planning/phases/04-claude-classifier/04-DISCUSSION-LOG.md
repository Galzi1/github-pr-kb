# Phase 4: Claude Classifier - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 04-claude-classifier
**Areas discussed:** Classification storage, API call strategy, Content hash dedup, Review flagging

---

## Classification Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Inline on CommentRecord | Add optional fields (category, confidence, summary) to existing CommentRecord in pr-N.json | |
| Separate classification files | Write per-PR classified-pr-N.json alongside cache. New ClassifiedComment model. | ✓ |
| Separate flat index | One classifications.json file indexing all comments by composite key | |

**User's choice:** Separate classification files
**Notes:** Keeps extraction and classification data independent. Phase 5 joins two file sets.

### Follow-up: File Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror PR cache | One classified-pr-N.json per PR, same directory | ✓ |
| Separate directory | Write to .github-pr-kb/classified/ | |

**User's choice:** Mirror PR cache (same directory)

---

## API Call Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One comment per call | Simple, reliable, easy to cache and retry. Higher cost but MVP-appropriate. | ✓ |
| Batch N comments per call | Lower cost, harder to retry and match results | |
| You decide | Claude picks approach | |

**User's choice:** One comment per call
**Notes:** Aligns with CLASS-03 per-comment caching philosophy.

---

## Content Hash Dedup

| Option | Description | Selected |
|--------|-------------|----------|
| Exact body hash (SHA-256) | Only truly identical comments share classification. No false positives. | ✓ |
| Comment ID only, skip content hash | Drop CLASS-03 requirement. Each comment classified independently. | |
| You decide | Claude picks approach | |

**User's choice:** Exact body hash (SHA-256)

### Follow-up: Hash Index Location

| Option | Description | Selected |
|--------|-------------|----------|
| Single index file | classification-index.json mapping body_hash -> classification result | ✓ |
| Embedded in classified files | Store hash inside each ClassifiedComment, scan all files for lookups | |

**User's choice:** Single index file (classification-index.json)

---

## Review Flagging

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean field + CLI output | needs_review: bool on ClassifiedComment, summary printed by classify command | ✓ |
| Separate review file | Low-confidence items written to dedicated review file | |
| You decide | Claude picks approach | |

**User's choice:** Boolean field + CLI output
**Notes:** Phase 5 can decide whether to include/exclude low-confidence items from KB.

---

## Claude's Discretion

- Prompt design (system prompt structure, output format)
- Claude model selection (cost vs quality tradeoff)
- Error handling for failed API calls

## Deferred Ideas

None — discussion stayed within phase scope
