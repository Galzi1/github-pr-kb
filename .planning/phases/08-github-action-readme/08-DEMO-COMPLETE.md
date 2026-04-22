# Phase 8 demo completion status for `github-pr-kb-demo`

## Final verdict

The **happy-path Phase 8 demo is complete**.

What is now proven in the live consumer repo `Galzi1/github-pr-kb-demo`:

1. a normal feature PR can be opened,
2. human review comments can be added on that PR,
3. merging the feature PR triggers the workflow,
4. the workflow can extract, classify, and generate real KB articles,
5. the workflow opens a rolling KB PR with article files under `kb/<category>/`,
6. that KB PR can be reviewed and merged,
7. the follow-up workflow run succeeds and does **not** open another automation PR,
8. `main` ends with generated KB content, updated `kb/INDEX.md`, updated `kb/.manifest.json`, no open automation PRs, and a green latest settling run.

This is a **bounded claim**: the happy path is demonstrated end to end on a real repo. It does **not** prove broad repeatability across arbitrary review styles, bot ecosystems, or external API conditions.

## Final repo state

At completion, `github-pr-kb-demo` ended with:

- feature PR `#10` merged,
- generated KB PR `#11` merged,
- no open PRs,
- generated KB articles present on `main`,
- `kb/INDEX.md` updated with the new entries,
- `kb/.manifest.json` updated with the new comment-id mappings,
- latest post-KB-merge workflow run `24277477172` green,
- no follow-up automation churn after that run.

## Final successful evidence chain

| Stage | Evidence |
| --- | --- |
| Fresh feature PR opened | PR `#10` — `feat: add minimum charge helper for final demo` |
| Human review comments posted | `#discussion_r3067728940`, `#discussion_r3067728949`, `#discussion_r3067728955` |
| Feature PR merged | PR `#10` merged successfully |
| Fresh content publish run | Manual replay run `24277455924` succeeded and opened KB PR `#11` |
| Generated KB PR reviewed and merged | PR `#11` merged successfully |
| Post-KB-merge steady-state run | Run `24277477172` succeeded and staged no new KB changes |
| Final repo quiet state | No open automation PRs remain |

## What initially blocked the demo

The first fresh content attempt after PR `#3` failed even though the workflow stayed green:

- run `24266078977` extracted comments successfully,
- classification logged repeated `Could not parse classification JSON` warnings,
- classification ended at `0 new / 0 cached / 0 need review / 18 failed`,
- generation had nothing publishable to write,
- no KB PR was opened.

The concrete root cause was **classifier parse mismatch at the model boundary**, not extraction failure and not an Anthropic outage.

## Remediation that made the final demo possible

### 1. Classifier hardening

The tool repository was fixed so classification can recover JSON from:

- bare JSON,
- fenced ```json``` blocks,
- prose-wrapped model output.

The parser was then tightened so only schema-valid classification payloads are accepted.

### 2. Publication-loop hardening

The first successful article-producing rerun exposed a second class of failures: the system could publish knowledge about its own automation loop.

Two extractor-side mitigations were required:

1. **Skip the rolling automation KB PR entirely** by ignoring PRs whose head branch matches `automation/github-pr-kb`.
2. **Ignore all `qodo-code-review[bot]` issue comments** so Qodo summary / status / issue-comment reviews do not become KB input.

This still leaves substantive **review comments** eligible input while removing the specific automation chatter that caused demo churn.

### 3. Consumer-repo workflow pin correction

One late demo replay failed because the consumer workflow was pinned to a mistyped tool SHA.

- failed run: `24277415328`
- failure mode: `Checkout github-pr-kb tool` could not fetch the referenced commit
- fix: correct `KB_TOOL_REF` on `github-pr-kb-demo` `main`
- successful replay after correction: `24277455924`

## Intermediate demo attempts that informed the final result

| Attempt | Outcome | Why it mattered |
| --- | --- | --- |
| PR `#3` -> run `24266078977` | Failed to produce any KB PR or article | Isolated the classifier parse problem |
| Repinned rerun -> KB PR `#4` | First real article-producing success | Proved the classifier fix unlocked content publication |
| PRs `#5` / `#6` | Closed as loop artifacts | Revealed self-ingestion from automation PRs and Qodo issue comments |
| PR `#7` -> KB PR `#8` | Successful content publication but not clean steady state | Confirmed the loop issue on a fresh feature PR |
| PR `#10` -> KB PR `#11` -> run `24277477172` | Final success path | Proved the end-to-end happy path on the final extractor behavior |

## Review comment contract that worked

The successful demos kept using the same core contract:

- plain text only,
- 1-3 sentences,
- one idea per comment,
- tied to a concrete code behavior or business rule,
- explicit about why the point matters,
- written as normal review feedback rather than post-fix narration.

This remained a useful constraint even after the classifier was hardened.

## Triage lessons retained from the failed attempts

The most useful quick diagnostic sequence in the live runs was:

1. **Permissions / environment** — checkout, auth, dependency install, PR creation, cursor persistence
2. **Extraction** — was the expected PR present and were comments cached?
3. **Classification** — did comments classify, or did parse / API errors dominate?
4. **Generation** — were article files written, or only summary files updated?
5. **Dedup / manifest suppression** — were comments skipped because they were already published?
6. **Publication outcome** — did a rolling KB PR actually appear with article files?

This checklist correctly separated:

- the original classifier failure,
- later automation-loop failures,
- a one-off bad tool-ref pin,
- expected dedup behavior on replayed comments.

## Article-fidelity checklist used for merge decisions

Generated articles were treated as acceptable to merge only when they were:

- factually grounded in the source review comment,
- placed in a defensible category,
- titled usefully for a future reader,
- structurally complete for that category,
- honest about missing evidence,
- consistent in frontmatter / index / manifest references,
- free of obvious hallucinated claims.

That rubric was sufficient for the demo purpose.

## Exit criteria status

| Exit criterion | Status | Evidence |
| --- | --- | --- |
| Merged feature PR with knowledge-bearing review comments | Done | PR `#10` |
| Automatic or replayed workflow produces real article output | Done | Run `24277455924` -> PR `#11` |
| KB PR contains article files under `kb/<category>/` | Done | PR `#11` diff |
| Human review accepts the generated KB PR | Done | PR `#11` merged |
| Post-KB-merge workflow succeeds | Done | Run `24277477172` |
| No new automation PR is opened after the KB PR merge | Done | No open PRs remain |
| Repo ends in clean steady state with updated KB artifacts on `main` | Done | `kb/INDEX.md`, `kb/.manifest.json`, article files on `main` |

## Bottom line

Phase 8 now has a real, end-to-end, user-visible demo in `github-pr-kb-demo`.

The final credible claim is:

> **The happy-path GitHub Action + README consumer workflow is demonstrated end to end, including article generation, rolling KB PR publication, merge, and stable post-merge steady state.**

The main residual caution is scope, not blockage: this is a strong happy-path proof, not a guarantee that every future bot ecosystem or comment style will behave identically without further hardening.
