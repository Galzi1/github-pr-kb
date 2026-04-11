# Phase 8 demo completion status for `github-pr-kb-demo`

## Goal

Reach a **complete end-to-end demo** of Phase 8 in `Galzi1/github-pr-kb-demo` and stop only when we have evidence for the full user-visible loop:

1. a normal feature PR is opened in the demo repo,
2. review comments are added on that PR,
3. the PR is merged,
4. the Phase 8 workflow automatically extracts/classifies/generates KB output,
5. the workflow opens a KB PR that contains at least one real article under `kb/<category>/`,
6. that KB PR is reviewed and merged,
7. the follow-up workflow run succeeds and does **not** create another KB PR,
8. `main` ends with the generated article, updated `kb/INDEX.md`, updated `kb/.manifest.json`, no open automation PRs, and a successful latest workflow run.

## What is already done

| Status | Item | Owner | Evidence |
| --- | --- | --- | --- |
| Done | Public demo repo `Galzi1/github-pr-kb-demo` was created and scaffolded with the copied workflow. | Copilot | Repo exists and workflow is installed on `main`. |
| Done | Source workflow was hardened for real-world demo use. | Copilot | Fixed parse-safe secret checks, corrected `KB_TOOL_REPOSITORY` to `Galzi1/github-pr-kb`, and fixed cursor persistence. |
| Done | Demo PR `#1` was opened, reviewed, updated, and merged. | Copilot + user flow | PR `#1` merged successfully. |
| Done | Manual no-op path was validated. | Automatic GitHub Actions flow | Run `24242554122` succeeded. |
| Done | Real merged-PR publish path was validated. | Automatic GitHub Actions flow | Run `24245335864` reached KB publication and opened PR `#2`; later fixes removed its final cursor failure. |
| Done | Full publish-and-persist path was validated after fixes. | Automatic GitHub Actions flow | Run `24245538002` succeeded. |
| Done | Steady-state loop after merging the generated KB PR was validated. | Automatic GitHub Actions flow | Run `24245767479` succeeded and did not open another KB PR. |
| Done | New demo PR `#3` was opened, reviewed with explicit plain-text comments, and merged. | Copilot | PR `#3` merged at `2026-04-10T21:58:37Z`. |
| Blocked | Fresh content-demo attempt after PR `#3` did **not** produce a KB PR or article. | Automatic GitHub Actions flow + Copilot diagnosis | Run `24266078977` succeeded mechanically, but classification logged `0 new / 18 failed`, generation logged `0 new`, and no automation PR was opened. |

## Important current limitation

The demo is **not yet a complete content demo**.

What we proved so far is:

- the workflow boots correctly in a consumer repo,
- merged PR events trigger the pipeline,
- the automation branch / rolling KB PR flow works,
- cursor persistence works,
- the workflow settles cleanly after a generated KB PR is merged.

What we **did not** prove yet is:

- a merged demo PR with review comments results in **at least one generated KB article** under `kb/<category>/`.

The latest attempt with PR `#3` did **not** close that gap. It reproduced the same high-level failure mode in a cleaner demo setup:

- PR `#3` was merged successfully,
- the merged-PR workflow run `24266078977` started automatically and finished `success`,
- no KB PR was opened,
- `main` still contains only `kb/.manifest.json` and `kb/INDEX.md`,
- the run logs showed `Extracted 2 PRs, 8 comments cached.`, `Classified 0 new, 0 cached, 0 need review, 18 failed.`, and `Generated 0 new, 0 skipped, 0 filtered, 0 failed.`.

So the demo is now blocked not on setup or review-comment quality alone, but on the classifier/content path itself.

For the PR `#1` demo data in workflow run `24245335864`, the preserved logs and debug artifact showed:

- `Extracted 1 PRs, 10 comments cached.`
- nine `Could not parse classification JSON for comment ...` warnings during classification,
- `Classified 1 new, 0 cached, 0 need review, 9 failed.`
- `Generated 1 new, 0 skipped, 0 filtered, 0 failed.`

However, the rolling KB PR `#2` that was ultimately merged still only contained:

- `kb/.manifest.json`
- `kb/INDEX.md`

So the workflow mechanics were validated, but the repo still did **not** finish with a published article on `main`, which is why the content demo remains incomplete.

## Remaining work required for a COMPLETE demo

### Mandatory gates before the next live demo attempt

The next feature-PR demo attempt must **not** start until all of the following are true:

1. **Done:** we have a short written diagnosis of the PR `#1` classification failure that names the concrete failure mode from logs/artifacts.
2. **Done:** we know which prior evidence is still inspectable and what fallback to use if deeper payload-level evidence is needed.
3. **Done:** we have a **comment-input contract** with realistic example review comments intentionally aligned to `gotcha`, `code_pattern`, and `domain_knowledge`.
4. **Done:** we have a **five-minute triage checklist** that distinguishes:
   - extraction failure,
   - classification failure,
   - generation failure,
   - dedup / manifest suppression,
   - permissions / environment failure.
5. **Done:** we have a brief **article-fidelity checklist** for the human review step so "looks good" is not purely ad hoc.

### PR `#1` classification diagnosis

The concrete failure mode for the PR `#1` demo data was **malformed model output / parse mismatch at the classifier boundary**, not extraction failure and not an Anthropic API outage.

Evidence from run `24245335864` and its uploaded `github-pr-kb-debug` artifact:

- extraction succeeded and cached all 10 comments for `pr-1.json`,
- the classifier emitted nine log lines of the form `Could not parse classification JSON for comment <id>`,
- the current classifier only increments `failed` for two paths: `anthropic.APIError` or `json.loads(...)` failure, and the logs showed the JSON-parse path rather than the API-error path,
- one plain-text issue comment (`4223530384`) classified successfully as `domain_knowledge` and produced a generated article in the failure artifact,
- the nine failed comments therefore represent responses that came back from the model but were not valid bare JSON for the current parser contract.

Short diagnosis: **the dominant PR `#1` classification failure was non-parseable classifier output, especially across the longer/more formatted comment set, so the next demo should not assume better review comments alone will fix the problem.**

What is still unknown from existing evidence is the exact raw malformed payload for each failed comment, because the workflow logs did not preserve the model response text at info level. If we need payload-level examples, the fastest fallback is a focused reproduction against the saved `pr-1.json` comment bodies with response capture enabled.

### Artifact and fallback status

The prior failure evidence is still inspectable enough to support the next step.

What is still available right now:

- the workflow job logs for run `24245335864` are still downloadable and still show the stage-level evidence, including the nine `Could not parse classification JSON` warnings,
- the uploaded debug artifact `github-pr-kb-debug` (artifact `6371844189`, not expired as of this update) is still downloadable,
- that artifact still contains the key preserved files we need for replay and inspection: `.github-pr-kb/cache/pr-1.json`, `.github-pr-kb/cache/classified-pr-1.json`, `.github-pr-kb/cache/classification-index.json`, and the generated `kb/` output snapshot.

What is **not** preserved in the current artifact set:

- the raw malformed model responses for the nine failed comments,
- enough logging detail to tell whether the malformed outputs were wrapped in prose, fenced code blocks, partial JSON, or some other near-miss shape.

Fastest reliable fallback if we need deeper evidence:

- replay classification locally or in a one-off debug run against the saved `pr-1.json` comments,
- capture the raw Claude response text before `json.loads(...)`,
- compare the successful plain-text comment path with one or two failed heavily formatted comments to isolate the output-shape mismatch quickly.

### Comment-input contract for the next demo PR

Use **plain human review comments** for the live demo. Each comment should be:

- plain text only, with no HTML, screenshots, copied bot templates, or fenced code blocks,
- 1-3 sentences focused on one idea,
- tied to a concrete code behavior or business rule,
- explicit about **why** the point matters, not just what changed,
- written before merge as normal review feedback, not as a post-fix status update like "fixed in commit ...".

Recommended example comments for the next demo run:

1. **Gotcha**
   `We should reject negative discount_amount values explicitly. Otherwise this helper turns a "discount" path into a surcharge path, which is easy to miss in tests because the math still looks valid at a glance.`

2. **Code pattern**
   `I would keep a small pattern here: validate discount inputs first, normalize the discounted subtotal once, then delegate to calculate_total for tax and rounding. That keeps every pricing path using the same calculation flow instead of duplicating rounding rules in multiple helpers.`

3. **Domain knowledge**
   `Please document that this helper applies an absolute discount before tax, not after tax and not as a percentage. That ordering is a pricing rule the business will care about, so it should be explicit in the code or docstring rather than implied by the implementation.`

These examples are intentionally shaped to be:

- realistic code-review comments a human could naturally leave on a small pricing helper PR,
- short enough to stay readable in GitHub,
- knowledge-bearing enough to publish if the classifier and generator path works correctly.

### Five-minute triage checklist for the next run

When the next merged-PR workflow runs, inspect the latest `update-kb` job in this order and stop as soon as one row matches the evidence:

| Area | Check in the run | Positive signal | Failure signal | Next action |
| --- | --- | --- | --- | --- |
| 1. Permissions / environment | Look first at `Validate repository-variable auth configuration`, `Checkout github-pr-kb tool`, `Install tool dependencies`, `Create or reuse rolling KB pull request`, and `Persist KB_LAST_SUCCESSFUL_CURSOR`. | These steps are `success` or intentionally `skipped`. | Missing secrets, checkout failure, dependency install failure, `gh` auth failure, push/PR creation failure, or cursor-persist failure. | Treat as workflow/environment breakage before reasoning about content quality. |
| 2. Extraction | Read the `Extract PR comments` step summary and, if needed, the uploaded debug artifact's `.github-pr-kb/cache/pr-<n>.json`. | Expected merged PR is present and the log shows nonzero comments cached. | Step fails, target PR is absent from cache, or comment count is unexpectedly zero. | Diagnose extractor input scope, repo/token access, or comment filtering before looking at classify/generate. |
| 3. Classification | Read the `Classify extracted comments` step summary and warnings. | Nonzero `new` or `cached`, with failures at zero or low enough to still leave publishable output. | `failed > 0`, repeated `Could not parse classification JSON`, Anthropic/API errors, or `0 classified` when extracted comments were clearly substantive. | Treat as classifier/content-path failure; inspect `classified-pr-<n>.json`, `classification-index.json`, and raw-response fallback if needed. |
| 4. Generation | Read the `Generate knowledge base` step summary and inspect `kb/` output or the KB PR diff. | At least one article file appears under `kb/<category>/`, plus matching `kb/INDEX.md` and `kb/.manifest.json` updates. | Generate step fails, or classify succeeded but no article file is produced. | Treat as generation failure unless the next row proves it was intentional dedup suppression. |
| 5. Dedup / manifest suppression | Compare generate output with `.manifest.json`, staged diff, and whether `Stage generated KB output` reports changes. | Existing manifest mapping explains why a repeated comment produced no new article. | `Generated 0 new` / no staged changes even though the PR introduced truly new review comments and no manifest entry already maps them. | If the manifest does not already explain the skip, escalate back to generation or classification diagnosis. |
| 6. Publication outcome | Check whether `Stage generated KB output`, `Commit and push KB update branch`, and `Create or reuse rolling KB pull request` actually produce a KB PR with article files. | Open or updated KB PR contains one or more `kb/<category>/*.md` files. | Only `kb/.manifest.json` and `kb/INDEX.md`, or no KB PR despite expected content. | Do **not** claim demo success; capture the artifact and continue diagnosis from the earliest failed stage above. |

Fast rule of thumb for this demo:

- **Extraction failure:** wrong or missing PR/comment data.
- **Classification failure:** comments were extracted, but classifier warnings/errors prevent usable classifications.
- **Generation failure:** classifications exist, but article files are not created from them.
- **Dedup / manifest suppression:** the system is behaving as designed because the comment was already published.
- **Permissions / environment failure:** the workflow cannot read, write, authenticate, or persist state even before content logic is trustworthy.

### Article-fidelity checklist for human review of the KB PR

When the generated KB PR is open, review each article against this checklist before merging:

| Check | What to confirm | Merge only if... |
| --- | --- | --- |
| 1. Factual fidelity | The article stays grounded in the PR title and source review comment. | It does **not** invent causes, decisions, implications, or fixes that are missing from the source. |
| 2. Category fit | The article category matches the original comment's intent. | A warning/pitfall lands in `gotcha`, a reusable implementation approach lands in `code_pattern`, and a business/project rule lands in `domain_knowledge` (or another category only if clearly justified). |
| 3. Useful summary | The `#` heading and article framing capture the actual insight. | The title is specific and useful to a future reader, not vague, misleading, or broader than the source comment. |
| 4. Required structure | The article body uses the expected section headings for its category and fills unsupported sections honestly. | Missing evidence is rendered as `Not stated in the source comment.` rather than hallucinated prose. |
| 5. Source handling | The article paraphrases rather than echoing or bloating the original review text. | It preserves the meaning without copying large spans of the source comment verbatim. |
| 6. Metadata integrity | Frontmatter and cross-file references match the source. | `pr_url`, `comment_url`, `author`, `category`, `comment_id`, `needs_review`, `kb/INDEX.md`, and `kb/.manifest.json` all point to the same article and source comment. |
| 7. Review flag visibility | Low-confidence content stays visibly reviewable. | If `needs_review: true`, the article and `kb/INDEX.md` make that visible rather than hiding it. |
| 8. Diff hunk relevance | Review-comment articles include code context only when it helps. | Any included fenced diff block is the source diff hunk for that comment and is relevant to the article's point. |

Practical merge rule for this demo:

- merge if the article is faithful, correctly categorized, structurally complete, and useful to a teammate who did not read the original PR,
- do **not** merge if the article hallucinates, miscategorizes the insight, or turns a narrow review comment into a broader claim than the source supports.

### Prepared next demo PR

The next small feature PR is now ready for review in `github-pr-kb-demo`.

- PR: `#3` — `feat: add percentage discount helper for demo review`
- URL: `https://github.com/Galzi1/github-pr-kb-demo/pull/3`
- Branch: `demo/percentage-discount-helper`
- Change scope: one small change to `demo_app.py` adding `calculate_total_with_percentage_discount(...)`
- Why this is a good demo candidate: it is small, easy to review on one screen, and naturally invites the exact kinds of comments we want for the next step — bounds/validation (`gotcha`), reuse of calculation flow (`code_pattern`), and business-rule clarity about tax/stacking semantics (`domain_knowledge`).

### Review comments posted on the demo PR

PR `#3` now contains the intended human-written review comments aligned to the comment-input contract:

- `gotcha`: `https://github.com/Galzi1/github-pr-kb-demo/pull/3#discussion_r3066907088`
- `code_pattern`: `https://github.com/Galzi1/github-pr-kb-demo/pull/3#discussion_r3066907115`
- `domain_knowledge`: `https://github.com/Galzi1/github-pr-kb-demo/pull/3#discussion_r3066907152`

These are plain-text review comments on the changed lines in `demo_app.py`, and they are ready for the merge step that will trigger the workflow.

### Current live status after merging PR `#3`

- PR `#3` merged successfully.
- Automatic workflow run `24266078977` started from that merge and completed `success`.
- `Commit and push KB update branch` and `Create or reuse rolling KB pull request` were both skipped because the workflow staged no KB changes.
- There is currently **no open automation PR** in `github-pr-kb-demo`.
- The latest run therefore failed the content-demo goal even though the workflow itself stayed green.

### PR `#3` run diagnosis

The new demo attempt confirms that the next task is **not** another review/merge exercise. It is a classifier/content-path fix.

Evidence from run `24266078977`:

- extraction worked (`Extracted 2 PRs, 8 comments cached.`),
- the classifier emitted repeated `Could not parse classification JSON for comment ...` warnings,
- classification ended at `Classified 0 new, 0 cached, 0 need review, 18 failed.`,
- generation then had nothing publishable to work with (`Generated 0 new, 0 skipped, 0 filtered, 0 failed.`),
- no KB files changed, so no KB PR was opened.

Short conclusion: **the next demo should not continue until the classifier/content path is fixed or hardened enough to turn these comments into parseable classifications.**

### Current remediation status in `github-pr-kb`

The classifier/content-path fix is now in progress in the tool repository itself:

- the local `github-pr-kb` classifier has been hardened to recover JSON objects from bare JSON, fenced ```json``` output, and prose-wrapped output instead of only accepting a raw top-level JSON string,
- regression tests were added for fenced JSON and prose-wrapped JSON classifier responses,
- local validation passed (`ruff check src tests` and the full pytest suite).

Important scope note: run `24266078977` still reflects the **pre-fix** shipped tool behavior because the demo workflow is pinned to the older `KB_TOOL_REF`. The next live demo attempt should use the hardened classifier build, not the previous pinned commit.

### Exit criteria

We can claim the **happy-path Phase 8 demo is complete** only after all of the following are true at the same time:

1. A new merged feature PR in `github-pr-kb-demo` has review comments that carry knowledge worth publishing.
2. The automatic merged-PR workflow succeeds.
3. The resulting KB PR contains:
   - at least one article file under `kb/<category>/`,
   - an updated `kb/INDEX.md` linking to that article,
   - an updated `kb/.manifest.json` mapping the comment id to the article path.
4. The article content is reviewed and accepted as faithful to the source PR comment.
5. The KB PR is merged.
6. The automatic post-KB-merge workflow succeeds and does not open another KB PR.
7. The demo repo ends with no open **automation** PRs and the generated article committed on `main`.

This is a **bounded claim**: it proves the intended end-to-end demo path on a real example. By itself it does **not** prove broad repeatability across varied comment styles, repo states, or external API conditions.

### Todo checklist

| # | Todo | Owner | Why this is required | Completion signal |
| --- | --- | --- | --- | --- |
| 1 | **Done:** inspect the current classification failures from the PR `#1` demo data and identify the exact failure mode (for example: malformed model output, empty output, API issue, parse mismatch, cache interaction, or prompt mismatch). Treat this as a **hard gate**, not a nice-to-have. | Copilot | We need to know whether the next demo should focus on better review-comment input, classifier robustness, cache handling, or both. | We have a short written diagnosis with the concrete failure reason from logs/artifacts, or a focused reproduction that isolates it. |
| 2 | **Done:** confirm whether the failing classifier outputs and related artifacts are still inspectable. If not, decide the fastest reliable fallback for reproducing the failure signal. | Copilot | Aggregate counts alone are not enough for a confidence-grade next step. | We know exactly what evidence we have and what fallback we will use if logs are insufficient. |
| 3 | **Done:** prepare a **comment-input contract**: 2-3 example review comments that are realistic, clearly knowledge-bearing, and intentionally aligned to supported categories such as `gotcha`, `code_pattern`, or `domain_knowledge`. | Copilot | The next live demo should not depend on vague human intuition about what "good comments" look like. | We have a short set of example comments ready to use as the review standard. |
| 4 | **Done:** define a **five-minute triage checklist** for the next run that distinguishes extraction failure, classification failure, generation failure, dedup / manifest suppression, and permissions / environment failure. | Copilot | If the next run still produces no article, we need rapid stage-level diagnosis instead of another ambiguous post-mortem. | We have a compact checklist or decision tree for reading the next run. |
| 5 | **Done:** define a brief **article-fidelity checklist** for human review of the generated KB PR. | Copilot + you | The final merge decision should use a consistent standard rather than a vague "looks good." | We have a small rubric covering factual fidelity, category fit, and usefulness. |
| 6 | **Done:** prepare a **new small feature PR** in `github-pr-kb-demo` that is easy to review and likely to produce one or more high-signal review comments. | Copilot | We need a fresh PR because PR `#1` has already been merged and its comments produced no article. | A new demo PR exists and is ready for review. |
| 7 | **Done:** add **clear, explicit review comments** on that new PR using the comment-input contract. | You (manual) | This is the actual user input the product is supposed to learn from. For a confidence-grade demo, the review comments should be intentionally high-signal and human-readable in GitHub itself. | The PR contains at least 2-3 substantive review comments that match the agreed examples/rubric. |
| 8 | **Done:** merge the new feature PR after the review comments are in place. | You (manual) | The workflow triggers from a merged PR, so this is the start of the real automatic demo path. | PR `#3` merged into `main`. |
| 9 | **Done:** run the Phase 8 workflow automatically from that merge. | Automatic GitHub Actions flow | This is the core Phase 8 behavior under demo. | Run `24266078977` started automatically from the PR `#3` merge and completed successfully. |
| 10 | **Failed / diagnosed:** verify that the automatic workflow produces a KB PR containing at least one real article file under `kb/<category>/`. If it does not, stop and diagnose instead of pretending the demo is complete. | Copilot | This is the missing proof from the current demo. Without an actual article, we only proved plumbing, not the content path. | Run `24266078977` produced no KB PR, no article files, and a classification-failure-only result (`18 failed`). |
| 11 | Review the generated article(s) against the article-fidelity checklist. | You (manual) | A complete demo needs human confirmation that the published knowledge is actually correct and useful, not just mechanically generated. | You are satisfied that the article reflects the source review comment accurately enough to merge. |
| 12 | Merge the generated KB PR. | You (manual) | This proves the publication loop closes successfully on real article content. | The KB PR is merged into `main`. |
| 13 | Let the post-KB-merge workflow run automatically and verify that it succeeds without opening another KB PR. | Automatic GitHub Actions flow | This proves the system reaches a stable steady state after publication. | Latest workflow run succeeds and no new automation PR is opened. |
| 14 | Perform the final repo-state verification: article exists on `main`, `kb/INDEX.md` links to it, `.manifest.json` maps it, latest workflow is green, and there are no open automation PRs created by this workflow. | Copilot | This is the final proof that the demo finished cleanly and left the repo in the expected end state. | All exit criteria above are satisfied simultaneously. |

## Non-negotiable gate

If the next merged demo PR again produces:

- no article files,
- only `kb/.manifest.json` and `kb/INDEX.md`, or
- another classification-failure-only run,

then the demo is **not complete** and we must not claim the happy-path demo is done. In that case, the next task is to diagnose and fix the classifier/content path before continuing.

## Expected final repo state when the demo is truly complete

`github-pr-kb-demo` should end with all of the following:

- the feature PR merged,
- the generated KB PR merged,
- at least one article file under `kb/<category>/`,
- `kb/INDEX.md` linking to the article,
- `kb/.manifest.json` containing the article mapping,
- no open automation PRs created by this workflow,
- latest relevant workflow runs green,
- no follow-up automation churn after the KB PR merge.

Only then should this demo be considered fully complete as a **happy-path end-to-end demonstration**.
