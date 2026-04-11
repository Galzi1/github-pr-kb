# Risk Review: 08-03-PLAN.md

## Plan Summary

The plan aims to rewrite `README.md` and add `tests\test_readme.py` so the shipped merged-PR workflow from 08-02 is documented first, PAT and GitHub App setup are explained, local CLI usage remains viable, and maintainers understand exactly what the automation commits versus what stays out of git.

The key moving parts are:

- the README restructure itself, with automation setup before local usage per D-11
- README contract tests that pin ordering, secret names, commands, and output-path guidance
- the 08-02 workflow contract, especially `.github\workflows\github-pr-kb.yml`, `KB_TOOL_REPOSITORY`, and `KB_TOOL_REF`
- the local config surface from `src\github_pr_kb\config.py` and `.env.example`
- the shipped CLI command surface from `src\github_pr_kb\cli.py`
- repo hygiene guidance for `kb\`, `kb\.manifest.json`, and `.github-pr-kb\cache\`

The plan's theory of success is reasonable: if the README accurately distinguishes workflow auth from local runtime auth, explains the copyable bootstrap model without ambiguity, preserves zero-to-working local setup, and stays aligned with the actual workflow/config/code surfaces, then a maintainer should be able to enable automation correctly and a contributor should still be able to run the tool locally from the docs alone.

## Assumptions & Evidence

| ID | Assumption | Explicit / Implicit | Justification status | Blast radius if wrong | Early validation |
|---|---|---|---|---|---|
| A1 | 08-02 will leave a stable enough workflow contract that 08-03 can document it without chasing moving targets. | Explicit | Partial | High | Read the final `.github\workflows\github-pr-kb.yml` and derive README assertions from it rather than from the plan text alone. |
| A2 | Simply naming `GITHUB_TOKEN`, `KB_VARIABLES_TOKEN`, `KB_VARIABLES_APP_ID`, and `KB_VARIABLES_APP_PRIVATE_KEY` is enough for maintainers to understand which credential is used where. | Implicit | Weak | Critical | Add an explicit credential-role matrix and a test that README separates local CLI auth from repository-variable auth. |
| A3 | The repo-specific command `.venv\Scripts\python.exe -m pytest tests\` belongs in a cross-platform README exactly as written. | Explicit | Unjustified | High | Either scope it as a Windows/local-repo note or provide macOS/Linux equivalents alongside it. |
| A4 | `.env.example` is already consistent with the env surface that README will describe. | Implicit | Contradicted by current evidence | High | Update `.env.example` in the same plan or make it explicitly non-authoritative and test for consistency. |
| A5 | Text-presence README contract tests are sufficient to prove the docs are operationally clear, not just keyword-complete. | Explicit | Partial | High | Add assertions for meaning, not only tokens: role separation, copy-only-workflow guidance, and committed-vs-ignored outputs. |
| A6 | The copyable bootstrap story can be compressed into README prose without readers inferring they need to vendor this repo's source tree. | Explicit | Partial | High | Add a dedicated short section or table saying exactly what consumer repos copy and what stays external. |
| A7 | PAT-first quickstart will not encourage over-scoped or long-lived use of the weaker auth path. | Implicit | Partial | Medium-High | Document the minimum fine-grained PAT permissions and recommend the GitHub App path as the longer-term option. |
| A8 | Prose alone is enough to keep users from confusing published KB artifacts with transient cache data. | Implicit | Partial | Medium-High | Add a compact "Committed vs not committed" table and pin it with tests. |

## Ipcha Mistabra - Devil's Advocacy

### Inversion Test

1. **Automation-first may make the product harder to adopt, not easier.** Front-loading workflow setup, dual auth, and cross-repo bootstrap details can overwhelm a user who just wants to run the CLI locally and inspect output before committing to automation.
2. **README contract tests may increase false confidence, not correctness.** If the tests mostly assert the presence of strings, the docs can satisfy the letter of the contract while still leaving readers confused about token roles, repo boundaries, or what gets committed.
3. **PAT-first quickstart may optimize initial setup while degrading long-term security posture.** Readers often stop at the first working path. If PAT comes first without crisp minimum-scope guidance and an explicit "App is better long-term" message, the quickstart becomes the de facto permanent setup.
4. **"README alone" may be less true than the plan assumes.** With workflow bootstrap, multiple credentials, and git publication rules, a reader may still need to inspect `.env.example` or the workflow file to resolve ambiguity unless the README is unusually explicit.

### The Little Boy from Copenhagen

- A new maintainer will ask: "Why are there multiple tokens here, and why doesn't `${{ github.token }}` cover repository-variable writes?"
- A macOS/Linux contributor will ask: "Why does the README show only `.venv\Scripts\python.exe` as the test command?"
- A security reviewer will ask: "What exact fine-grained PAT permissions are required, and why is PAT the default path instead of the App?"
- A consumer-repo maintainer will ask: "Do I copy only `.github\workflows\github-pr-kb.yml`, or do I also need this repo's source tree, lockfile, or `.env.example`?"

### Failure-of-Imagination Check

- The README becomes accurate, but `.env.example` remains stale, so users copy the wrong template and then distrust the docs when classify/generate behavior does not match what they expected.
- A maintainer stores a PAT in the wrong place because the README names both `GITHUB_TOKEN` and `KB_VARIABLES_TOKEN` without a crisp responsibility split; the workflow then fails only at `gh api` or rolling-PR publication time.
- The docs correctly say `.github-pr-kb\cache\` stays out of git, but the examples do not make the publication boundary concrete enough, so readers still misunderstand the role of `kb\.manifest.json`.
- `KB_TOOL_REF` is documented as a required knob but the README never explains how to upgrade it safely, so copied workflows either stay pinned forever or users switch to a floating branch manually.

## Risk Register

| Risk ID | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption link |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Security / Operational | **Known Unknown:** maintainers may confuse local CLI auth with repository-variable auth because the plan requires secret names but not a crisp explanation of credential roles. | A user follows README setup and reuses `GITHUB_TOKEN` where `KB_VARIABLES_TOKEN` or App credentials were required, or vice versa. | High - the workflow spans several similarly named auth surfaces. | High - setup fails late and can lead to over-scoped credentials. | High | `gh api` variable writes fail, support questions cluster around token setup, or users put PATs in the wrong secret. | Add a README token-role matrix covering local `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `KB_VARIABLES_TOKEN`, App creds, and the workflow's internal `GH_TOKEN` mapping; pin this with tests. | Correct the secret mapping, rotate the credential if it was exposed or over-scoped, and rerun. | A2 |
| R2 | Technical / Documentation | **Known Unknown:** the plan can turn a machine-specific contributor command into universal README guidance. | A macOS/Linux user follows `.venv\Scripts\python.exe -m pytest tests\` literally. | Medium-High | High - the README's "works from zero" promise breaks for a common audience. | High | Reader reports that the documented test command does not exist on their platform. | Provide platform-specific commands or clearly label the Windows command as repo-local guidance and include a Unix equivalent. | Patch the README quickly and point users to the working command pair. | A3 |
| R3 | Organizational / Technical | **Known Known:** README may be updated while `.env.example` remains stale, creating two contradictory onboarding sources. | 08-03 rewrites README but leaves `.env.example` comments or examples lagging behind current behavior. | High - current evidence already shows drift pressure. | High - users commonly copy `.env.example` before reading deeper docs. | High | New users copy `.env.example` and miss or misread variables that README describes differently. | Expand the plan to update `.env.example` too, or explicitly declare one source authoritative and add tests enforcing alignment. | Ship a follow-up fix to `.env.example` and note the correction in README. | A4 |
| R4 | Technical | **Unknown Unknown surfaced by inversion:** string-based README tests can pass while the docs still fail to explain the copyable two-repo bootstrap and secret responsibilities in a way humans can execute correctly. | The README contains all required strings but leaves role boundaries or workflow-copy semantics ambiguous. | Medium | High | High | Green tests but repeated user confusion around "do I need this repo's source tree?" or "which token goes where?" | Add semantic assertions: README must explicitly say consumer repos copy the workflow, not the package source tree; README must separate workflow secrets from local env vars. | Rewrite the affected section without changing product behavior. | A5, A6 |
| R5 | Security | PAT-first quickstart may normalize a broader or more fragile auth setup unless minimum permissions and migration guidance are explicit. | Readers stop at the first working path and never revisit auth hardening. | Medium | High | High | PATs with overly broad permissions appear in setup guidance or support examples. | Document the minimum fine-grained PAT permission set and frame GitHub App as the preferred long-term service-account model. | Keep PAT support, but tighten docs and recommend migration. | A7 |
| R6 | Operational | Published-output guidance may still be too abstract, causing users to misunderstand that `kb\`, `kb\.manifest.json`, and `.github-pr-kb\cache\` have different lifecycle rules. | A maintainer reads the README quickly and infers that all tool-created files are either committed or ignored together. | Medium | Medium-High | High | Cache files appear in commits, or maintainers ask whether `kb\.manifest.json` belongs in git. | Add a short table showing "Committed" vs "Not committed" artifacts and keep the KB tree example concrete. | Clean up the commit, restore the manifest if omitted, and rerun generation. | A8 |
| R7 | Operational / Maintainability | The README may expose `KB_TOOL_REF` without giving maintainers an upgrade story, making the workflow either silently stale or manually unpinned later. | A copied workflow stays on an old immutable ref, or a maintainer changes it to a floating branch for convenience. | Medium | Medium-High | Medium-High | Consumer repos diverge widely in pinned refs or start using floating branches. | Document how to bump `KB_TOOL_REF` intentionally and why it should stay immutable between upgrades. | Publish an update note and restore an immutable ref. | A1, A6 |

## Verdict & Recommendations

**Overall Risk Level:** High

**Verdict:** The plan is close, but it is **not ready as written**. The biggest remaining risks are no longer about workflow mechanics; they are about documentation becoming the new failure point. In particular, the current plan does not yet force clear separation of token roles, treats a Windows-specific test command as if it were README-grade guidance, and ignores the risk of leaving `.env.example` behind as a conflicting onboarding source.

**Top 3 Risks**

1. R1 - credential-role confusion between local runtime auth and repository-variable auth
2. R3 - README and `.env.example` drifting into contradictory onboarding sources
3. R2 - platform-specific local test guidance presented as universal

**Recommended Actions**

1. Expand `files_modified` to include `.env.example`, or explicitly declare it non-authoritative and add tests that prevent README and `.env.example` drift.
2. Add a README contract test that asserts the docs distinguish local `GITHUB_TOKEN` / `ANTHROPIC_API_KEY` from `KB_VARIABLES_TOKEN` or GitHub App credentials, and explain that the workflow maps repository-variable auth to `GH_TOKEN` internally.
3. Replace the single Windows-only pytest command requirement with either paired Windows + macOS/Linux commands or wording that clearly scopes the Windows command to this repo's contributor setup.
4. Add a compact consumer-repo bootstrap explainer: what gets copied (`.github\workflows\github-pr-kb.yml`), what stays external (this tool checkout), and how to update `KB_TOOL_REF`.
5. Add a small table in README for "Committed" (`kb\`, `kb\.manifest.json`) vs "Not committed" (`.github-pr-kb\cache\`) and pin that with tests.
6. Keep automation-first ordering, but add a fast path near the top for readers who only want local CLI usage so the README does not become workflow-only in practice.

**Open Questions**

- Should README be the authoritative onboarding source, or must `.env.example` remain equally authoritative?
- Do we want the README to recommend GitHub App as the preferred long-term setup even while PAT stays the quickstart?
- What is the preferred cross-platform local test guidance for contributors: paired `.venv` commands, or a simpler higher-level instruction?
- Does `KB_TOOL_REF` upgrade guidance belong in the README, in workflow comments, or in both?

**What the Plan Does Well**

- It correctly treats 08-03 as a documentation phase that must reflect the already-shipped workflow rather than re-litigate product shape.
- It anchors the rewrite to real code and config surfaces (`cli.py`, `config.py`, `.env.example`, and the workflow contract) instead of inventing new behavior.
- It preserves the important git-hygiene story around `kb\`, `kb\.manifest.json`, and `.github-pr-kb\cache\`.
- It explicitly removes stale architecture claims from the README instead of quietly layering new guidance on top of old text.
