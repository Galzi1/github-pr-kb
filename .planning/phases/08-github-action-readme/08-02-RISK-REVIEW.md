# Risk Review: 08-02-PLAN.md

## Plan Summary

The plan aims to ship a reusable, copy-ready GitHub Actions workflow that runs after merged PRs or on manual dispatch, bootstraps this tool from a dedicated checkout, uses the 08-01 `action_state` helper to decide whether to run, publishes generated `kb/` output through one rolling bot PR, reuses `.github-pr-kb/cache/`, and persists `KB_LAST_SUCCESSFUL_CURSOR` only after successful publication.

The key moving parts are:

- the consumer repository checkout plus a second checkout of the tool repository
- `uv`-based bootstrap and command execution from the tool checkout
- the 08-01 `github_pr_kb.action_state` helper
- repository-variable reads/writes through `gh api`
- dual-mode auth (`KB_VARIABLES_TOKEN` or GitHub App credentials)
- Actions cache for `.github-pr-kb/cache/`
- explicit staging and publication of `kb/INDEX.md`, `kb/**/*.md`, and `kb/.manifest.json`
- one stable publication branch and one rolling PR

The plan's theory of success is sound in outline: if the workflow can bootstrap the tool deterministically, invoke the helper in the correct environment, skip no-op runs early, publish only the generated KB outputs, and persist cursor state monotonically after success, then merged PRs should keep the KB current without cron, duplicate PRs, or cache files leaking into git.

## Assumptions & Evidence

| ID | Assumption | Explicit / Implicit | Justification status | Blast radius if wrong | Early validation |
|---|---|---|---|---|---|
| A1 | A copy-ready workflow can bootstrap from `.github-pr-kb-tool` while still invoking `python -m github_pr_kb.action_state` successfully in consumer repos. | Implicit | Weak | Critical | Require the helper to run through the same tool environment as the CLI (`uv run --project ... python -m ...`) or add a workflow smoke test in a repo without this source tree. |
| A2 | "Persist after success" is enough to prevent cursor corruption under overlapping merged-event runs. | Implicit | Weak | Critical | Add workflow-level concurrency and a final re-read/max-write of the repository variable just before persistence. |
| A3 | The GitHub App auth path is fully specified by `KB_VARIABLES_APP_ID` and `KB_VARIABLES_APP_PRIVATE_KEY`. | Implicit | Weak | High | Specify the exact token-minting action/API and how installation selection works for the current repo. |
| A4 | Defaulting `KB_TOOL_REPOSITORY` / `KB_TOOL_REF` is safe for consumer repos from both reliability and supply-chain perspectives. | Explicit | Partial | High | Pin the default ref to an immutable release tag or SHA and document the upgrade path. |
| A5 | Text-based workflow contract tests are sufficient to catch real execution failures in shell quoting, pathspecs, auth wiring, and JSON/null handling. | Explicit | Partial | High | Add at least one execution-oriented smoke test for the helper invocation and publication path. |
| A6 | The workflow can stage `kb/INDEX.md`, nested KB markdown, and `kb/.manifest.json` deterministically without accidentally depending on shell-specific glob behavior. | Implicit | Partial | High | Use explicit git pathspecs or enumerated file lists and assert the exact command shape. |
| A7 | One stable branch and one rolling PR will remain operable in repos with branch protection, merge conflicts, or pre-existing automation branches. | Implicit | Weak | Medium-High | Define expected behavior when the branch already exists, cannot be pushed, or has conflicting changes. |
| A8 | Introducing additional GitHub Actions for cache, artifact upload, or app token minting without pinning is acceptable in this repo. | Implicit | Weak | High | Follow the existing repo convention of pinning third-party actions by commit SHA. |

## Ipcha Mistabra — Devil's Advocacy

### Inversion Test

1. **The copy-ready bootstrap may reduce portability rather than improve it.** A second checkout plus project-scoped `uv` commands makes the workflow more reusable in principle, but it also creates a two-repo runtime model with ref management, environment separation, and failure modes that do not exist when the code is local or packaged. If the helper invocation is not routed through that same environment, copied workflows will fail immediately in the exact repos they were meant to support.

2. **The cursor design may still skip or replay work even though 08-01 is correct.** The helper can emit a correct candidate cursor and still lose the race operationally if two merged-event runs read the same stored cursor, do work in parallel, and the older event writes last. In other words, moving logic out of YAML does not remove the need for concurrency control in YAML.

3. **A rolling PR may reduce PR spam while increasing operational brittleness.** One long-lived branch is tidy, but it is also a single choke point for merge conflicts, stale branch state, protection rules, and manual tampering. The cleaner UX for reviewers can come at the cost of harder automation recovery.

4. **Dual auth may increase setup burden more than it increases robustness.** Supporting PAT and App paths sounds flexible, but it also doubles the number of credentials, precedence branches, and failure modes. If the App path is underspecified, the documented "advanced" option becomes a support trap.

### The Little Boy from Copenhagen

- A maintainer copying this workflow into another repo will ask a simple question: "Why does `uv run --project .github-pr-kb-tool github-pr-kb ...` work, but `python -m github_pr_kb.action_state` also somehow work?" If the answer is "because the environment happens to be activated," the workflow is not actually copy-ready.
- A security reviewer will ask why a consumer repo is executing code from an external repository ref and possibly unpinned third-party actions. "It is our own repo" is not a sufficient supply-chain argument if the ref floats.
- An on-call engineer will ask what prevents two close-together merges from racing each other and writing cursor state out of order.
- A new maintainer will ask what happens when `automation/github-pr-kb` already exists, has conflicts, or is protected.

### Failure-of-Imagination Check

- A copied workflow defaults to a floating `KB_TOOL_REF`, the upstream tool changes behavior, and many consumer repos silently start generating different KB output without any repo-local code change.
- The App credentials are present but the app is not installed on the current repo, or the token action resolves the wrong installation; the workflow treats a failed variable read as "no cursor" and performs an unexpectedly broad extraction.
- Workflow text tests pass, but `git add kb/**/*.md` behaves differently than expected on the runner shell, so nested articles are not staged while `kb/INDEX.md` is, creating a publication state that looks valid in the PR but breaks dedup on later runs.
- A merged-event run and a manual backfill both succeed; the later finisher writes the smaller cursor, and the system appears healthy until future runs repeat or skip windows.

## Risk Register

| Risk ID | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption link |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Technical | **Known Unknown:** the workflow may fail in copied consumer repos because the helper is described as `python -m github_pr_kb.action_state` even though the plan's portability model depends on a separate tool checkout and project-scoped environment. | The workflow runs in a repo that does not contain this package source tree. | High — the plan text currently points in two different execution directions. | Critical — the workflow fails before skip logic, extraction, or publication. | Critical | Early workflow failure with `ModuleNotFoundError` or import-path errors. | Make helper invocation explicit and environment-consistent: `uv run --project .github-pr-kb-tool python -m github_pr_kb.action_state` or an equivalent tool-scoped command. Add a consumer-repo smoke test. | Patch the workflow to route the helper through the tool checkout and rerun manually. | A1 |
| R2 | Operational | **Known Unknown:** overlapping merged-event or manual runs can still regress or stall durable state because the plan does not yet require workflow concurrency plus a final monotonic write against the freshest stored cursor. | Two runs overlap and finish out of order. | Medium-High — merged PR workflows naturally overlap in active repos. | Critical — skipped or replayed PR windows undermine the whole incremental contract. | Critical | Cursor value moves backward, repeated "already processed" skips appear unexpectedly, or later runs repeat older windows. | Add workflow/job concurrency, re-read `KB_LAST_SUCCESSFUL_CURSOR` immediately before writing, and persist `max(current_stored, candidate_next_cursor)`. | Repair the variable manually, run backfill, and temporarily serialize the workflow. | A2 |
| R3 | Security / Operational | **Known Unknown:** the GitHub App path is underspecified; minting or selecting the installation token may fail or target the wrong installation. | App credentials are configured, but installation resolution is ambiguous or incorrect. | Medium | High — repository-variable reads/writes and PR operations fail or act on the wrong auth path. | High | `gh api` returns auth/permission errors, or App path behaves differently across repos/orgs. | Specify the exact action/API for App token minting, pin it, and define installation lookup for the current repository. Consider requiring an installation identifier if automatic lookup is unreliable. | Fall back to PAT quickstart path and document the limitation until App flow is proven. | A3 |
| R4 | Security | **Unknown Unknown surfaced by inversion:** consumer repos may inherit supply-chain drift because the plan allows external tool checkout and likely new third-party actions without requiring immutable pins. | `KB_TOOL_REF` or an added action references a mutable branch/tag that later changes. | Medium | High — behavior can change across repos without local review, and compromised upstream refs expand blast radius. | High | Workflow behavior changes without repo-local code changes; diffs show unexpected action/tool versions. | Pin `KB_TOOL_REF` to a release tag or SHA by default, pin all third-party actions by commit SHA, and document version upgrade steps explicitly. | Freeze to a known-good ref and publish a hotfix README/workflow update. | A4, A8 |
| R5 | Technical | **Known Unknown:** text-only workflow tests can pass while shell quoting, JSON parsing, null handling, or publication commands still fail at runtime. | YAML contains expected strings but actual step execution differs from the intended contract. | Medium | High — false confidence leads to broken shipped automation. | High | Green contract tests but failed Actions runs in real repos; helper output not parsed as expected. | Add at least one execution-oriented smoke test around helper invocation and publication-step command construction. Keep string tests, but do not rely on them alone. | Fix the workflow step wiring and rerun without changing product behavior. | A5 |
| R6 | Operational | Explicit staging of generated KB output may still be brittle if the implementation relies on shell globbing rather than git pathspec semantics. | The workflow uses `kb/**/*.md` in a shell-sensitive way or forgets to include `kb/.manifest.json` and `kb/INDEX.md` together. | Medium | High — publication can become silently incomplete and later cause duplicate generation. | High | PR branch is missing nested KB files or manifest/index drift after a "successful" run. | Use git pathspecs like `:(glob)kb/**/*.md` or explicit file enumeration, and assert the exact staging command shape. | Repair the branch contents and rerun generation from the last good cursor. | A6 |
| R7 | Operational | A single rolling branch/PR may deadlock on merge conflicts, branch protection, or stale manual edits. | `automation/github-pr-kb` already exists with conflicting history or protected push rules. | Medium | Medium-High — updates stall and repeated runs keep failing. | High | Push rejection, repeated PR-update failures, or a permanently stale open KB PR. | Define branch recovery behavior, expected bot ownership, and whether force-with-lease is permitted. Document how maintainers reset the branch safely. | Close/reset the automation branch and recreate the rolling PR. | A7 |

## Verdict & Recommendations

**Overall Risk Level:** High

**Verdict:** The plan is strong on product shape and much better grounded than 08-01, but it is **not ready as written** because several operationally load-bearing details are still implicit. The biggest issue is that the workflow's portability story and the helper invocation story are currently inconsistent, and the 08-01 handoff requirement for concurrency-aware monotonic persistence is not yet turned into an explicit 08-02 implementation/test contract.

**Top 3 Risks**

1. R1 — helper execution path breaks in copied consumer repos
2. R2 — out-of-order runs corrupt or stall cursor state
3. R3 — GitHub App auth path is underspecified and may fail in real repos

**Recommended Actions**

1. Make the helper execution path explicit and single-source: every invocation of project code, including `action_state`, should run through the `.github-pr-kb-tool` environment.
2. Promote concurrency and monotonic persistence from "background expectation" to a first-class acceptance criterion and test target in 08-02.
3. Specify the GitHub App token implementation in concrete terms: which action/API, how installation is selected, and what exact scopes are required.
4. Pin every third-party action by commit SHA and default `KB_TOOL_REF` to an immutable versioned ref rather than a floating branch.
5. Replace shell-dependent staging language with exact git pathspec language and verify nested KB files, `kb/INDEX.md`, and `kb/.manifest.json` move together while `.github-pr-kb/cache/` never enters git.
6. Add one execution-level smoke test or fixture that proves the helper, env wiring, and publication command structure behave correctly outside pure string assertions.

**Open Questions**

- Will `KB_TOOL_REF` default to a floating branch, a release tag, or a full SHA?
- How exactly will the workflow mint and select a GitHub App installation token for the current repository?
- What concurrency group will serialize or supersede overlapping runs?
- What is the intended recovery path if `automation/github-pr-kb` cannot be pushed or is manually modified?
- Is the workflow expected to tolerate branch protection on the automation branch, or is that explicitly unsupported?

**What the Plan Does Well**

- It correctly assumes 08-01 exists and reuses that helper rather than re-embedding decision logic in YAML.
- It makes the workflow copy-ready as a first-class requirement instead of quietly depending on the source tree being present.
- It is explicit about auth separation (`GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `GH_TOKEN`) and about staging the manifest and top-level index with the KB content.
- It preserves the right high-level invariant: publish first, then persist the cursor.
