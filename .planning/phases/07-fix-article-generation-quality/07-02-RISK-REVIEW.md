# Risk Review: 07-02-PLAN.md

**Overall risk: High.** `07-02-PLAN.md` is directionally strong and mostly well-scoped relative to `07-03`, but it currently rests on an unverified prerequisite (`07-01`), leaves the core quality promise too dependent on model obedience, and makes `regenerate` destructive without a rollback story.

## 1. Plan Summary

**Purpose:** replace raw-comment article generation with Claude-synthesized, category-structured KB articles, while adding confidence filtering, synthesis failure handling, regeneration support, and generator-side API-key enforcement.

**Key components touched:** `src\github_pr_kb\generator.py`, `tests\test_generator.py`, with hard dependencies on `07-01` changes to config/result-model contracts and a handoff to `07-03` for CLI exposure of `--regenerate` and reporting.

**Plan’s stated assumptions:**
- `07-01` already added `settings.anthropic_generate_model`, `settings.min_confidence`, and `GenerateResult.filtered`.
- Reusing the `PRClassifier` Anthropic-init pattern is safe in `KBGenerator`.
- Claude output will be available as `response.content[0].text`.
- Prompting plus templates is enough to prevent raw-comment-copy regressions.
- Destructive regeneration is acceptable operationally.

**Theory of success:** if generation becomes LLM-backed, low-confidence items are filtered, failures do not write files or manifest entries, and full regeneration is available, article quality will improve materially without corrupting incremental behavior.

## 2. Assumptions & Evidence

| ID | Assumption | Explicit? | Evidence | Status | Blast radius if wrong | How to validate before execution |
|---|---|---:|---|---|---|---|
| A1 | `07-01` prerequisites are already present | Yes | Current branch still lacks `anthropic_generate_model`, `min_confidence`, and `GenerateResult.filtered`; `07-01-SUMMARY.md` is also missing | **Unverified / false on current tree** | High | Verify `07-01` actually landed, or fold those changes into `07-02` |
| A2 | Anthropic responses will always be `response.content[0].text` | Implicit | Plan handles `anthropic.APIError`, but not empty content, non-text blocks, or blank output | **Weak** | High | Add explicit output-shape validation and tests for empty/non-text responses |
| A3 | Every classified comment contains enough signal to fill forced section templates without invention | Implicit | The templates require sections like “Root Cause” and “Fix or Workaround” even when the source comment may not provide them | **Weak** | High | Prompt Claude to state uncertainty rather than invent; add review samples |
| A4 | Prompt instructions are sufficient to stop raw comment text from reappearing | Implicit | Acceptance criteria prove the code no longer concatenates `comment.body`, but not that the model will avoid quoting/parroting it | **Weak** | High | Add a similarity/repetition guard or a manual evaluation set |
| A5 | `--regenerate` can safely wipe KB state before network synthesis runs | Implicit | `_reset_kb` clears manifest and deletes category dirs before reprocessing | **Partially justified** | Critical | Make rebuild transactional, or preserve a rollback copy until success |
| A6 | Planned tests prove the intended behavior | Explicit | Some planned tests assert the wrong layer: `_write_article()` does not update manifest, and “manifest was cleared” is an intermediate state, not a stable outcome | **Incomplete** | Medium-High | Rewrite tests around `generate_all()` / end-state filesystem results |
| A7 | Filtering after manifest dedup is the right long-term semantic | Implicit | Existing generated articles remain even if `MIN_CONFIDENCE` later increases; only regenerate re-applies the threshold | **Reasonable, but easy to misunderstand** | Medium | Document that prompt/model/threshold changes require `--regenerate` |

## 3. Ipcha Mistabra — Devil’s Advocacy

### Inversion test

The plan says Claude synthesis will make articles more valuable. **The opposite is plausibly true:** it can make them more polished but less trustworthy. Removing the raw comment body improves readability, but it also removes the easiest way to audit whether the article stayed faithful to the source.

The plan says category templates improve structure. **The opposite is plausibly true:** they may force the model to invent structure the comment did not contain. A short reviewer warning can become a fabricated “root cause” or “workaround” simply because the template demands it.

The plan says `regenerate` is the recovery mechanism. **The opposite is plausibly true:** `regenerate` may be the most dangerous operation in the phase, because it destroys the current KB before the replacement KB is known-good.

### Little boy from Copenhagen

A new engineer would likely ask: “How do I know which parts of this article came from the PR comment, and which parts are Claude’s interpretation?” The plan does not answer that.

An SRE or on-call engineer would ask: “What happens if Anthropic is degraded halfway through regenerate?” Right now, the answer appears to be “you may end up with a partially rebuilt KB.”

A skeptical reviewer would also notice that the current branch does not yet show the `07-01` prerequisite changes this plan assumes. That means the plan is not wrong in theory, but it is not execution-safe unless dependency state is verified first.

### Failure of imagination check

The most credible surprise failure is not an API outage; it is **plausible-looking wrong content**. Claude may confidently fill required headings with inferred causes or recommendations that were never in the source comment. That failure is dangerous because it looks like success.

A second overlooked scenario is **blank or malformed-but-non-exceptional output**: the API returns a response object, but the first block is not text, or the text is empty boilerplate. The current plan does not clearly classify that as a failed synthesis path.

A third is **regeneration drift**: after prompt/model changes, the KB becomes a frozen mix of old and new synthesis quality unless users remember to run `--regenerate`. The plan supports that operationally, but does not yet make the consequence obvious.

## 4. Risk Register

| Risk ID | Type | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption link |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Unknown known | Technical | `07-02` assumes `07-01` contracts already exist, but current tree does not show them | Execute plan on current branch | High | High | **High** | Missing attrs/fields, failing tests, missing `07-01-SUMMARY.md` | Gate execution on verified `07-01` completion, or absorb prerequisite changes | Pause `07-02`, repair dependency chain first | A1 |
| R2 | Known unknown | Quality | Forced templates may cause Claude to invent “root cause” / “fix” content not present in the comment | Sparse or ambiguous source comments | Medium-High | High | **High** | Spot checks reveal claims not grounded in source PR comment | Prompt for uncertainty, allow “not stated,” add human review sampling | Skip article when output appears speculative | A3, A4 |
| R3 | Known known | Reliability | Non-exception bad output is not fully handled; code may crash or write junk if response shape is unexpected | Empty/non-text/blank Anthropic response | Medium | High | **High** | IndexError/AttributeError, empty article bodies | Validate response blocks and body text before writing | Treat as synthesis failure and retry on next run | A2 |
| R4 | Known known | Operational | `regenerate` is destructive and non-transactional, so outages can leave the KB partially or fully wiped | API outage, crash, Ctrl+C during regenerate | Medium | Critical | **Critical** | Missing category dirs, empty/partial manifest after failure | Rebuild in temp dir and atomically swap, or keep backup until success | Restore backup / rerun from preserved snapshot | A5 |
| R5 | Unknown known | Testing | Planned tests may pass while missing the real failure modes or asserting the wrong layer | Implement tests exactly as written | High | Medium-High | **High** | Green tests but broken manifest/failure behavior in practice | Test end-state behavior via `generate_all()` and filesystem assertions | Add a follow-up hardening patch before calling the phase done | A6 |
| R6 | Known unknown | Operational | Skipped failures and threshold filtering can create coverage holes that look like normal output | Repeated synthesis failures or higher confidence threshold | Medium | Medium-High | **Medium-High** | Rising failed/filtered counts, fewer articles than expected | Surface counts clearly in `07-03`; document when regenerate is required | Retry failed subset / run full regenerate after tuning | A7 |
| R7 | Mystery | Product/UX | Polished synthesized articles may be trusted more than warranted because raw source text is no longer visible | Users read KB as canonical truth | Medium | High | **High** | Conflicts between article claims and original PR discussion | Preserve strong provenance links and consider reviewer flags | Mark articles for review when confidence/context is weak | A3, A4 |

## 5. Verdict & Recommendations

**Overall risk level: High.** The plan is sound in direction, and its phase split is mostly disciplined, but it is **not yet execution-safe** unless dependency state is verified and two core gaps are closed: **template-driven hallucination risk** and **non-transactional regenerate behavior**.

**Top 3 risks:**
1. **Unverified `07-01` dependency**
2. **Template-driven hallucination / prompt-only anti-copy enforcement**
3. **Destructive regenerate without rollback**

**Recommended actions before proceeding:**
1. **Prove `07-01` landed** before executing `07-02`. If it has not, update this plan so it explicitly owns the missing prerequisite changes instead of assuming them.
2. **Tighten `_build_article()` failure criteria.** Treat empty output, non-text blocks, and suspiciously input-similar output as failure cases, not successes.
3. **Make regenerate transactional.** Rebuild into a temporary KB directory and swap only after synthesis and index generation complete.
4. **Relax template coercion.** Prompt the model to say “not stated in the source comment” rather than inventing a root cause, decision, implication, or workaround.
5. **Fix the test plan.** Validate stable end states, not internal intermediate states or methods that do not own manifest mutation.
6. **Document the semantics of threshold/model/prompt changes.** Users should understand that existing articles are frozen until regenerate runs.

**Open questions:**
- Has `07-01` actually been implemented, or is this plan currently ahead of the branch state?
- Is partial KB loss during `--regenerate` acceptable, or must rollback be guaranteed?
- Should synthesized articles be strictly extractive, or is interpretive summarization acceptable if clearly attributable?
- Should a missing section be rendered as uncertainty rather than forcing all headings to contain substantive claims?

**What the plan does well:**
- It correctly keeps user-facing CLI work in `07-03` rather than overloading `07-02`.
- It has the right instinct to avoid writing files/manifest entries on synthesis failure.
- It reuses established lazy-config and Anthropic-client patterns instead of inventing a new integration style.
- It focuses the phase on the actual quality bottleneck: article generation, not just formatting.