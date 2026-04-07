# Phase 7: Fix Article Generation Quality - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 07-fix-article-generation-quality
**Areas discussed:** Article synthesis, Classification failures, CLI output accuracy, Low-value filtering, Synthesis error handling, Existing KB cleanup, Generator API key requirement

---

## Article Synthesis

| Option | Description | Selected |
|--------|-------------|----------|
| Claude rewrites into article | Send raw comment + PR context to Claude to produce a well-structured KB article with context, explanation, and actionable takeaways | ✓ |
| Light formatting only | Keep original comment text but add section headers, clean up markdown, prepend Context section | |
| You decide | Claude picks the best approach | |

**User's choice:** Claude rewrites into article
**Notes:** Additional API call per article, but produces genuinely useful knowledge articles

---

| Option | Description | Selected |
|--------|-------------|----------|
| During generate step | KBGenerator calls Claude to synthesize each article at generation time | ✓ |
| During classify step | Classifier produces full article text alongside category/confidence | |

**User's choice:** During generate step
**Notes:** Keeps separation of concerns clean — classify is lightweight, generate is the "smart" step

---

| Option | Description | Selected |
|--------|-------------|----------|
| Category-specific templates | Each category gets a tailored structure (gotcha: Symptom/Cause/Fix, etc.) | ✓ |
| Uniform template | All articles use same Context/Key Insight/Recommendation structure | |

**User's choice:** Category-specific templates
**Notes:** gotcha → Symptom/Root Cause/Fix; architecture_decision → Context/Decision/Consequences; code_pattern → Pattern/When to Use/Example; domain_knowledge → Context/Key Insight/Implications

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, append as collapsed section | Include raw comment in <details> block at bottom | |
| No, synthesized only | Article is purely Claude-synthesized version | ✓ |
| You decide | Claude picks based on article length | |

**User's choice:** No, synthesized only
**Notes:** Raw comment remains in cache JSON for provenance

---

| Option | Description | Selected |
|--------|-------------|----------|
| Comment + PR title | Send comment body plus PR title for context | ✓ |
| Comment + PR title + other comments | Send full PR discussion thread | |
| Comment only | Just the raw comment text | |

**User's choice:** Comment + PR title
**Notes:** Minimal extra tokens (~300-500 input tokens per article), gives Claude enough to frame properly

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, manifest-based dedup | Existing manifest tracks comment_id → article path; skip if exists | ✓ |
| Separate synthesis cache | Store synthesized text in separate cache file keyed by content hash | |

**User's choice:** Yes, manifest-based dedup
**Notes:** No extra caching layer needed — just add Claude call before write

---

| Option | Description | Selected |
|--------|-------------|----------|
| Same model as classifier | Use settings.anthropic_model (defaults to claude-haiku-4-5) | |
| Separate config for generator | Add new ANTHROPIC_GENERATE_MODEL env var | ✓ |
| You decide | Claude picks | |

**User's choice:** Separate config for generator
**Notes:** Users can use smarter model for synthesis while keeping Haiku for classification

---

## Classification Failures

| Option | Description | Selected |
|--------|-------------|----------|
| Skip entirely — no record created | Log warning, increment failed count, return None | ✓ |
| Retry once, then skip | Retry Claude API call once on JSON parse failure | |
| Keep as 'other' but mark unfixable | Create record with special flag for generator to skip | |

**User's choice:** Skip entirely — no record created
**Notes:** The fake fallback record (category='other', confidence=0.0, summary='classification failed') is removed

---

| Option | Description | Selected |
|--------|-------------|----------|
| Re-classify on next run | Remove 'classification failed' entries from index on startup | ✓ |
| Leave as-is, only fix going forward | Don't touch existing cache entries | |
| You decide | Claude picks | |

**User's choice:** Re-classify on next run
**Notes:** Self-healing behavior — failed entries get fresh API calls automatically

---

| Option | Description | Selected |
|--------|-------------|----------|
| Regenerate classified files too | classify_pr() already overwrites — cleaning index is sufficient | ✓ |
| Only clean the index | Leave classified-pr-N.json as-is | |

**User's choice:** Regenerate classified files too
**Notes:** Existing overwrite behavior handles it naturally

---

## CLI Output Accuracy

| Option | Description | Selected |
|--------|-------------|----------|
| Detailed breakdown | Show new/skipped/filtered/failed separately | ✓ |
| Simple summary | Short: 'Generated 12 new articles, 8 unchanged.' | |
| You decide | Claude picks detail level | |

**User's choice:** Detailed breakdown
**Notes:** Users see exactly what happened for both classify and generate commands

---

| Option | Description | Selected |
|--------|-------------|----------|
| Exit 0 with warnings | Partial failures are normal; exit 1 only for total pipeline failure | ✓ |
| Non-zero on any failure | Exit 1 if any article failed | |

**User's choice:** Exit 0 with warnings
**Notes:** Warnings printed to stderr for partial failures

---

## Low-Value Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Skip 'other' entirely | Don't generate articles for 'other' category | |
| Generate but in separate folder | Put 'other' in kb/other/ directory | |
| Generate all categories equally | Keep current behavior — all categories get articles | ✓ |

**User's choice:** Generate all categories equally
**Notes:** No category-based filtering

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, skip below threshold | Don't generate for confidence < 0.5, configurable via MIN_CONFIDENCE | ✓ |
| No threshold — generate all | Generate all regardless of confidence | |
| You decide | Claude picks | |

**User's choice:** Yes, skip below threshold
**Notes:** Default 0.5 threshold; >= 0.75 normal, 0.50-0.74 article + [review], < 0.50 filtered

---

## Synthesis Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip and report | Don't write article, don't add to manifest; retried next run | ✓ |
| Retry once, then skip | Retry API call once on failure | |
| Fall back to raw comment | Write raw comment body (current behavior) | |

**User's choice:** Skip and report
**Notes:** No fallback to raw copy — that's the problem we're fixing

---

## Existing KB Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Force-regenerate flag | Add --regenerate flag to clear manifest and re-synthesize all | ✓ |
| Auto-detect raw articles | Check if existing articles lack structure, re-synthesize automatically | |
| Manual cleanup only | Users delete kb/ folder manually | |

**User's choice:** Force-regenerate flag
**Notes:** Lets users upgrade KB after this phase ships without re-classifying

---

## Generator API Key Requirement

| Option | Description | Selected |
|--------|-------------|----------|
| Require API key | Fail fast with clear error if missing | ✓ |
| Optional — fallback to raw | Fall back to old raw-copy behavior with warning | |
| You decide | Claude picks | |

**User's choice:** Require API key
**Notes:** Same pattern as classify command

---

## Claude's Discretion

- Synthesis prompt engineering (exact wording, max_tokens, temperature)
- Error message wording for missing API key in generate
- How --regenerate cleans up existing files

## Deferred Ideas

None — discussion stayed within phase scope
