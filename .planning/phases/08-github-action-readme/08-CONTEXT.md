# Phase 8: GitHub Action + README - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a reusable GitHub Actions workflow and an updated README so maintainers can automatically update the PR knowledge base after merged PRs, manually backfill when needed, avoid unnecessary API calls, and onboard from the docs alone.

</domain>

<decisions>
## Implementation Decisions

### Trigger Model
- **D-01:** The workflow runs primarily on post-merge PR events, not on a cron schedule.
- **D-02:** A `workflow_dispatch` entry point is also included for recovery and backfill runs.
- **D-03:** Normal automated runs process merged/closed PRs only, not open PRs.

### Incremental Boundary & Recovery
- **D-04:** When a manual recovery/backfill run needs a cursor, it is based on PRs updated since the last successful backfill point. This intentionally aligns with the extractor's existing `updated_at` filtering semantics.
- **D-05:** The repository variable is a recovery/backfill cursor for manual runs, not the primary driver of normal post-merge execution.

### Publication Mode
- **D-06:** KB updates are published through one rolling bot PR that is created if absent and updated in place if it already exists.
- **D-07:** The workflow commits only generated KB output to that PR. Extraction/classification working data stays out of git.

### Cache & State Persistence
- **D-08:** The last-successful-run marker lives outside the tracked repo as a repository variable.
- **D-09:** Extraction/classification caches persist outside git, with GitHub Actions cache as the primary reuse mechanism.
- **D-10:** Workflow artifacts are optional and used only when helpful for debugging, not as the normal persistence channel.

### README Shape
- **D-11:** The README is automation-first: GitHub Action setup comes before local CLI usage.
- **D-12:** Local setup, environment variables, command reference, and KB output examples are still included after the automation guidance so users can run and inspect the tool manually.

### the agent's Discretion
- Exact event syntax and guard conditions for merged-only PR triggers
- Bot PR title/branch naming, commit message wording, and update mechanics
- Whether manual dispatch supports explicit PR targeting, date-range backfill, or both
- Exact README section naming and example formatting

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/ROADMAP.md` — Phase 8 goal, dependency chain, and success criteria
- `.planning/REQUIREMENTS.md` — ACTION-01, ACTION-02, ACTION-03, and INFRA-03
- `.planning/PROJECT.md` — project vision, single-repo MVP scope, and CLI + GitHub Action product direction

### Existing Pipeline
- `src/github_pr_kb/cli.py` — current CLI entry points (`extract`, `classify`, `generate`, `run`) and existing pipeline wiring
- `src/github_pr_kb/extractor.py` — extraction entry point, `updated_at` filtering semantics, and merge-on-rerun cache behavior
- `src/github_pr_kb/generator.py` — KB output, manifest behavior, and generation entry point
- `src/github_pr_kb/config.py` — environment/config surface the workflow and README must document
- `.env.example` — current documented environment variables and defaults

### Existing Automation & Repo Conventions
- `.github/workflows/ci.yml` — established GitHub Actions setup pattern (`setup-uv`, dependency install, test invocation)
- `.github/workflows/claude.yml` — existing bot-oriented workflow pattern and permissions structure
- `.gitignore` — `.github-pr-kb/` is ignored, which constrains what automation should commit vs persist externally
- `README.md` — current documentation baseline to replace/restructure for Phase 8

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/github_pr_kb/cli.py`: Existing commands already compose the full pipeline; the workflow can reuse CLI entry points rather than inventing parallel Python entrypoints.
- `src/github_pr_kb/extractor.py`: `extract()` already supports `since` / `until` filtering and merge-based cache reuse, which is useful for manual backfill behavior.
- `src/github_pr_kb/generator.py`: `generate_all()` already handles manifest-based incremental KB output and is the natural workflow generation step.
- `.github/workflows/ci.yml`: Existing Action setup shows the repo's preferred `uv` installation flow and Python execution pattern.

### Established Patterns
- `.github-pr-kb/` is local working data and is currently gitignored.
- Generated KB content lives under `kb/` and is treated as repo-visible output.
- Existing GitHub workflows already use checkout + setup-uv conventions; Phase 8 should stay consistent with those patterns.
- The tool is single-repo and sync-first for v1; Phase 8 should not introduce multi-repo or async orchestration.

### Integration Points
- New workflow logic will live alongside existing `.github/workflows/*.yml` automation.
- The workflow must bridge GitHub event context to the existing CLI pipeline and/or underlying Python entry points.
- Repository-variable reads/writes and Actions-cache restore/save become part of the workflow contract.
- README updates must align with the actual env vars, CLI flags, and workflow file shipped in the repo.

</code_context>

<specifics>
## Specific Ideas

- The user explicitly wants the automation to run after PR merges rather than on a schedule.
- The bot should maintain a single rolling KB update PR instead of creating a new PR every run.
- Repo cleanliness matters: commit KB output, but keep extraction/classification working data outside git.
- Manual runs should exist for recovery/backfill, with repository-variable state supporting that path.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-github-action-readme*
*Context gathered: 2026-04-08*
