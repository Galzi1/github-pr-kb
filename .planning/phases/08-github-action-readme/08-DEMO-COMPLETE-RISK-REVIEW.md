# Risk Review: `08-DEMO-COMPLETE.md` (Post-execution addendum)

## Outcome summary

The Phase 8 happy-path demo is now complete, but the execution surfaced additional real risks that were not fully explicit in the original plan:

1. classifier parse robustness,
2. self-ingestion of the rolling automation PR,
3. ingestion of Qodo issue comments on non-automation PRs,
4. workflow pin correctness / tool-ref reachability.

The final successful path required fixing all four.

## What the original risk review got right

The original review correctly identified the most important pre-demo concerns:

- unresolved classifier failure mode,
- weak stage-level observability,
- overclaim risk from a single curated success,
- need to narrow the final claim to a happy-path demo rather than broad confidence.

Those concerns all mattered in the real execution.

## Risks that materialized

| Risk | What actually happened | Resolution |
| --- | --- | --- |
| Classifier parse mismatch | The demo failed at `0 new / 18 failed` even though extraction worked. | Hardened the classifier to recover wrapped JSON and reject schema-invalid payloads. |
| Automation self-ingestion | After the first article-producing rerun, the workflow opened follow-up KB PRs based on comments on its own automation PRs. | Skip PRs whose head branch matches `automation/github-pr-kb`. |
| Qodo issue-comment churn | Late Qodo issue comments on a normal feature PR were re-ingested and produced another unwanted KB PR. | Ignore all `qodo-code-review[bot]` issue comments while still allowing non-issue review comments. |
| Tool-ref reachability | One final replay failed because the consumer repo used a mistyped pinned SHA. | Corrected `KB_TOOL_REF` and replayed the workflow successfully. |

## Assumptions updated by real execution

| Assumption | Pre-execution view | Post-execution reality |
| --- | --- | --- |
| Better-crafted comments alone might unblock the demo | Weakly justified | False. The first blocker was systemic classifier parsing, not comment quality alone. |
| One successful content publish is enough to call the demo complete | Overstated | False. The first publish success still left publication-loop churn unresolved. |
| No open automation PRs is the right final quiet-state criterion | Reasonable | Correct. It was the most useful final steady-state check. |
| A bounded happy-path claim is the right confidence level | Recommended | Correct. The final result supports a strong happy-path claim, not broad repeatability. |

## Residual risk after completion

| Area | Residual risk | Why it still matters |
| --- | --- | --- |
| Bot ecosystems beyond Qodo | Medium | The extractor now handles the concrete bot chatter that broke this demo, but other bots may introduce similar issue-comment or review-comment noise later. |
| Review-comment categorization | Medium | Articles are good enough for the demo, but category placement is still model-driven and not perfectly deterministic. |
| Consumer pin hygiene | Low-Medium | The workflow still depends on a valid `KB_TOOL_REF`; bad pins will fail fast. |
| Broader repeatability | Medium | The final proof is a real happy path, but still based on curated PRs and comments. |

## Final verdict

**Post-execution risk level: Medium.**

That is a major improvement from the original pre-demo assessment because the core blockers were found and fixed. The remaining risk is no longer "can the demo be completed?" but rather "how far can the result be generalized without more variation testing?"

## Final recommendation

Treat Phase 8 as **demo-complete** with this exact wording:

> The happy-path end-to-end consumer workflow is proven, including real article generation, rolling KB PR publication, merge, and stable post-merge steady state.

Do **not** extend that claim to universal repeatability without additional runs that vary:

- reviewer phrasing,
- bot presence,
- repo state / cache state,
- publication timing,
- tool-ref / consumer upgrade paths.
