# Risk Review: `08-DEMO-COMPLETE.md`

## 1. Plan Summary

**Purpose.** Prove a complete, user-visible Phase 8 demo in `Galzi1/github-pr-kb-demo`, ending with a merged feature PR, a generated KB PR containing at least one real article, a stable post-merge workflow run, and a clean final repo state.

**Key components touched.**

| Component | Role in the plan |
| --- | --- |
| Demo repository `Galzi1/github-pr-kb-demo` | Consumer repo where the Phase 8 workflow is exercised end to end |
| GitHub Actions workflow | Triggers on merge events, runs extract/classify/generate, opens KB PRs, and persists cursor state |
| Extraction / classification / generation pipeline | Converts merged PR comments into KB artifacts |
| Anthropic-backed classifier | Converts raw comment text into one of the supported categories or review-needed output |
| KB output (`kb/<category>/`, `kb/INDEX.md`, `kb/.manifest.json`) | Observable proof that knowledge was generated and published |
| Human review / merge steps | Provide the source review comments, validate article fidelity, and close the loop by merging the KB PR |

**Plan-stated assumptions.**

1. Previous workflow hardening means the plumbing path is already sound enough that the remaining gap is content generation.
2. Existing logs and artifacts from PR `#1` are sufficient to diagnose why all 10 comments failed classification.
3. A new, deliberately small feature PR with high-signal review comments is likely to produce at least one publishable article.
4. One successful curated run is enough to justify calling the demo "100% confidence" complete.

**Theory of success.** The plan succeeds if the current classification failure mode is first understood, then a fresh PR with clearly knowledge-bearing comments is merged, the workflow produces a real KB article, humans confirm the article is faithful, and the system reaches steady state without opening another automation PR.

## 2. Assumptions & Evidence

This plan is strongest where it is explicit about the current gap and weakest where it assumes a single successful rerun will convert uncertainty into confidence.

| ID | Assumption | Explicit / Implicit | Class | Justification status | Blast radius if wrong | How to test before committing fully |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | The PR `#1` failures are diagnosable from existing logs/artifacts without reproducing the run in a different way. | Explicit | Foundational | **Partial.** The plan names this as the first todo, but does not confirm artifact depth or whether failed model outputs were retained. | If false, the team may start a new demo without understanding whether the problem is content quality, classifier robustness, caching, or API behavior. | Pull the exact workflow logs/artifacts for the failed run and verify they reveal concrete failure reasons rather than only aggregate counts. |
| A2 | Workflow mechanics are already sufficiently proven, so the remaining uncertainty is mainly in the content/classifier path. | Implicit | Structural | **Mostly justified.** Multiple runs reportedly validated branch creation, persistence, and steady state. Still, content-path failures can expose workflow-path weaknesses hidden by zero-article runs. | If false, a second demo may fail for both workflow and content reasons, making diagnosis slower and conclusions weaker. | Run a preflight checklist on permissions, refs, secrets, and branch protections immediately before the next live demo. |
| A3 | Better-crafted review comments will classify cleanly. | Explicit | Foundational | **Weak.** The previous outcome was "10 failed" rather than merely "low confidence" or "other," which suggests a possibly systemic issue, not just low-signal input. | If false, the next demo repeats the same failure and consumes manual effort without increasing confidence. | Dry-run representative review comments through the classifier outside the live demo path or inspect the exact prior failure mode first. |
| A4 | Supported categories and prompt behavior are predictable enough that humans can intentionally author comments that land in `gotcha`, `code_pattern`, or `domain_knowledge`. | Explicit | Structural | **Partial.** This is plausible, but only if classifier output is stable and parsing is robust. The current evidence does not show that. | If false, the demo becomes dependent on prompt luck rather than reproducible behavior. | Create 2-3 example comments and validate local classification results before the merge-triggered workflow run. |
| A5 | A single curated successful run is enough to claim "100% confidence in the demo." | Explicit | Structural | **Unjustified.** One scripted success proves the happy path, not robustness across comment phrasing, timing, API variability, or cache state. | If false, the plan may overclaim readiness and hide brittleness that appears immediately after the demo. | Reframe the claim as "happy-path demo complete" unless at least one additional variant or replay also succeeds. |
| A6 | Manual reviewers will provide comments that are both product-realistic and classifier-friendly, then judge article fidelity consistently. | Implicit | Structural | **Weak.** The plan requires manual precision but does not define an authoring rubric or acceptance rubric. | If false, the demo outcome may hinge on ad hoc human choices rather than product behavior. | Provide explicit comment-writing examples and a short article-acceptance checklist before starting the live run. |
| A7 | External dependencies will behave consistently during the next run: GitHub permissions, workflow refs, model availability, API quotas, and repository state. | Implicit | Structural | **Partial.** Prior runs worked, but these are live dependencies outside the plan's control. | If false, a demo failure may be misread as a product failure when it is an environment failure. | Do a same-day preflight against secrets, permissions, tool ref reachability, and API readiness. |
| A8 | "No open PRs" is a valid final exit criterion for the demo repo. | Explicit | Peripheral | **Weak.** It is precise for automation churn, but too broad if unrelated human PRs can exist. | If false, the plan can fail its own exit criteria even when the automation loop worked correctly. | Narrow the criterion to "no open automation PRs created by github-pr-kb." |

**Secrets vs. mysteries.**

- **Secrets:** the exact cause of the 10 failed classifications, whether cache state affects replays, whether example comments classify locally, whether the workflow still has correct permissions and refs.
- **Mysteries:** whether a human reviewer will judge the generated article "useful" enough, whether future non-curated PR comments will produce similarly good output.

The current plan is strongest when it treats unresolved classifier behavior as a **secret** to investigate. It becomes weaker when it treats long-term confidence as if it can be resolved by one curated run, which is closer to a **mystery** that must be managed with bounded claims.

## 3. Ipcha Mistabra - Devil's Advocacy

### 3a. The Inversion Test

**Claim:** A fresh PR with better comments will likely complete the content demo.

**Inversion:** Better comments may not matter at all. "10 failed" classifications points to a parser, prompt, API, schema, or cache defect more than a simple comment-quality issue. In that world, the next PR adds more manual work while reproducing the same opaque failure.

**Why this inversion is compelling:** The prior evidence is not "0 useful comments" but "0 classified, 10 failed." That smells like system behavior, not merely weak content.

---

**Claim:** Once one curated run succeeds, the demo can be called complete with 100% confidence.

**Inversion:** A single curated success could actually reduce epistemic rigor by creating false confidence. It would prove that one carefully staged path worked once under current conditions, not that the system is stable, repeatable, or resilient to minor variation.

**Why this inversion is compelling:** Demo success and product confidence are not the same thing. A curated demo is a marketing-quality proof, not an operational-quality proof.

---

**Claim:** The workflow path is already validated, so the remaining work is mostly content-path verification.

**Inversion:** Content-path verification may be exactly where workflow-path weaknesses reappear. A run that generates real articles can trigger branch, manifest, dedup, PR diff, and post-merge behavior that zero-article runs never exercised in the same way.

**Why this inversion is compelling:** "Real content exists" is not just more of the same path; it can activate new edge cases.

### 3b. The Little Boy from Copenhagen

**A new engineer joining next month** would likely ask: "What exact failure signature distinguishes bad input from broken classification?" The current plan does not define that boundary. It assumes the first diagnosis task will discover it, but the execution plan after that still relies heavily on intuition.

**An SRE or on-call maintainer at 3 AM** would likely ask: "If the next run produces no article, how do I tell in five minutes whether extraction, classification, generation, dedup, or permissions caused it?" The plan has outcome checks, but not a stage-specific observability checklist.

**A repo maintainer** would likely ask: "Why is 'no open PRs' part of success?" If another unrelated PR exists, the plan fails its own exit criteria for a reason that has nothing to do with Phase 8.

**A skeptical user of the product** would likely ask: "How do I know the generated article is actually faithful rather than superficially plausible?" The plan includes human review, which is good, but it does not define what fidelity means.

### 3c. Failure of Imagination Check

1. **Cache poisoning / stale-state scenario.** The next run may reuse cached classification or manifest state in a way that masks improvement or suppresses article generation, making a good comment set look like a product failure.
2. **Parseable-but-wrong scenario.** The classifier may stop "failing" but still return low-confidence or `other` results that technically pass through the pipeline while still not producing the proof the demo needs.
3. **Article-generated-but-filtered scenario.** Classification may succeed, but generation may deduplicate or skip the article because of manifest state, leading to another KB PR that looks empty in the place that matters.
4. **Environment-drift scenario.** The plan assumes the same repo settings, token scopes, action refs, and external model behavior remain stable between prior validation and the next demo. Live systems drift.
5. **Success-but-not-credible scenario.** The demo may succeed only because comments were written in a classifier-optimized way that real reviewers would never write, making the demo impressive but strategically misleading.

## 4. Risk Register

| Risk ID | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption link | Knowledge class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Technical | The real root cause of the PR `#1` "10 failed" outcome is not isolated before running the next demo. | A new feature PR is merged before the failure signature is understood. | High - the plan still lacks the actual cause. | High - the next demo can repeat the same failure and waste the main proving attempt. | High | Another run shows `0 classified` and failed counts without actionable diagnosis. | Make Todo #1 a hard gate: inspect logs/artifacts and, if needed, reproduce locally until the failure mode is concrete. | Pause the demo-completion claim and switch scope to classifier-path repair. | A1, A3 | Unknown known |
| R2 | Technical | The next review comments are human-meaningful but still do not map cleanly to the classifier's expected prompt/schema/category behavior. | Comments are merged without first validating example phrasing. | Medium | High - no article means the demo is still incomplete. | High | Low-confidence, `other`, empty, or failed classifications on otherwise good comments. | Create a short comment-authoring rubric and validate 2-3 samples before the live PR merge. | Open another small PR or adjust classifier robustness before retrying. | A3, A4, A6 | Known unknown |
| R3 | Operational | Observability is too weak to separate extraction, classification, generation, dedup, and permission failures quickly during the live demo. | The next run again produces no article or partial output. | Medium | High - diagnosis becomes slow and confidence claims remain fuzzy. | High | Logs show counts but not decisive per-stage reasons or retained failing payloads. | Add a pre-demo diagnostic checklist and preserve the exact artifacts/log lines needed for stage-level attribution. | Download artifacts immediately and perform a post-mortem before any retry. | A1, A2 | Known unknown |
| R4 | Organizational | A single curated successful run is over-interpreted as "100% confidence," masking fragility and shrinking future learning. | The first successful article-producing run is treated as full proof. | High | Medium - the product story becomes stronger than the evidence. | High | The final write-up contains categorical confidence claims unsupported by repeatability evidence. | Reframe the target as "complete happy-path demo" unless at least one additional variant also works. | Document confidence boundaries explicitly in the completion note. | A5 | Known known |
| R5 | Operational | External dependencies drift between the prior validated runs and the next live demo. | Token scopes, action permissions, refs, branch protections, or model/API behavior change. | Medium | High - a live demo can fail for reasons unrelated to the product logic. | High | Auth errors, checkout/ref errors, API failures, or PR creation failures appear in the workflow. | Perform a same-day environment preflight before merging the new feature PR. | Repair environment issues and rerun without counting the failed attempt as product evidence. | A2, A7 | Known unknown |
| R6 | Organizational | Manual steps are underspecified, so comment authoring and article-fidelity review vary too much between runs or reviewers. | Humans write comments or assess generated content without a shared rubric. | Medium | Medium | Medium | Comments are inconsistent in style/specificity, or reviewers disagree on whether the article is faithful. | Provide exact examples of acceptable review comments and a short fidelity checklist. | Re-review the KB PR or create a fresh demo PR with better source comments. | A6 | Mystery |
| R7 | Technical | Cache or manifest state suppresses article generation even when classification improves. | Prior cache entries or manifest mappings are unexpectedly reused during the next run. | Medium | High - the team may misdiagnose success as failure or failure as success. | High | Nonzero extraction/classification activity but `0 new` generation or unexplained skips. | Inspect cache and manifest behavior explicitly as part of pre-demo readiness. | Reset or isolate demo state, or rerun in a fresh environment with documented cache behavior. | A2, A3 | Unknown unknown |
| R8 | Operational | The exit criterion "no open PRs" blocks success for irrelevant reasons. | Any unrelated PR exists during or after the demo. | Medium | Low | Medium | Core demo behavior succeeds, but the repo still has an open non-automation PR. | Narrow the criterion to automation PRs created by the workflow. | Snapshot repo state and declare success relative to automation artifacts only. | A8 | Known known |

## 5. Verdict & Recommendations

**Overall risk level: High.** The plan is honest, structured, and close to a viable execution checklist, but it rests on one load-bearing uncertainty: whether the prior all-failed classification result was caused by input quality or by a systemic defect. Until that is resolved, the proposed next demo attempt is at meaningful risk of being an expensive repetition rather than a completion.

**Top 3 risks.**

1. **R1 - unresolved classifier failure mode**
2. **R3 - insufficient stage-level observability during the live run**
3. **R4 - overclaiming confidence from one curated success**

**Recommended actions before the next live demo attempt.**

1. **Promote diagnosis to a hard gate.** Do not merge a new feature PR for the "complete demo" path until the PR `#1` failure mode is written down concretely: malformed model output, parse mismatch, API failure, cache interaction, prompt mismatch, or something else.
2. **Add a comment-input contract.** Prepare 2-3 example review comments that are both realistic and intentionally aligned to the supported categories, then validate them before using them in the live demo.
3. **Add a five-minute triage checklist.** Define what evidence distinguishes extraction failure, classification failure, generation failure, dedup/manifest suppression, and permissions/environment failure.
4. **Reduce claim scope.** Replace "100% confidence" with a bounded statement unless you also demonstrate repeatability or at least one meaningful variant.
5. **Tighten exit criteria.** Change "no open PRs" to "no open automation PRs created by the workflow," and define a brief article-fidelity checklist so the manual review step is less subjective.

**Open questions.**

1. What exact error produced the "10 failed" classification result on the prior run?
2. Are the failing classifier outputs retained anywhere inspectable, or do logs only expose aggregate counts?
3. Could cache or manifest state suppress article creation even when classification succeeds?
4. What specific rubric will be used to decide that a generated article is faithful enough to merge?
5. Is the next demo intended to prove only the happy path, or also repeatability?

**What the plan does well.**

- It is unusually honest about the current gap: the missing proof is not workflow plumbing, but real article generation.
- It includes a non-negotiable gate that rejects false completion if the next run still produces no articles.
- It separates automatic and manual responsibilities clearly enough to execute.
- It defines a concrete desired end state in the repo rather than relying on vague notions of "done."

**Bottom line.** This is a credible near-final demo checklist, but not yet a low-risk completion plan. Treat the prior classifier failure as the critical unknown, narrow the confidence language, and add sharper observability and manual rubrics before running the next "complete demo" attempt.
