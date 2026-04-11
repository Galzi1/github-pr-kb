# Phase 8: GitHub Action + README - Research

**Researched:** 2026-04-09
**Domain:** GitHub Actions / GitHub REST API / gh CLI / uv / existing github-pr-kb CLI
**Confidence:** MEDIUM-HIGH

## Summary

Phase 8 should reuse the existing CLI pipeline, but **not** the `github-pr-kb run` command as-is.
`run` currently hardcodes the full pipeline, while `extract` already exposes the exact incremental
controls this phase needs: `--state`, `--since`, and `--until`. For automated runs after merge, the
workflow should drive `extract --state closed --since <cursor>` followed by `classify` and
`generate`, then publish `kb/` changes through one rolling bot PR.

The biggest implementation constraint is state persistence. The phase context already locks the
last-successful-run cursor to a repository variable, and GitHub's current REST docs show that both
fine-grained PATs and GitHub App installation tokens can read/write repository variables when they
have **Variables** repository permission. That makes the safest product shape a **dual-mode auth**
workflow: PAT-first quickstart in the README, GitHub App as the advanced path.

The workflow must also preserve two existing incremental mechanisms already built into the tool:
`.github-pr-kb/cache/` for extractor/classifier reuse and `kb/.manifest.json` for generator-side
dedup. The latter is especially important: if the automation commits `kb/*.md` but skips
`kb/.manifest.json`, fresh runners can generate duplicate `-2` / `-3` articles even when the KB
already contains the prior content.

**Primary recommendation:** plan the phase around three deliverables:
1. workflow/auth/state publication mechanics,
2. automation-supporting code/tests for incremental state decisions,
3. a README rewrite that documents both automation auth paths and local usage accurately.

---

<user_constraints>
## User Constraints (from CONTEXT.md + follow-up clarification)

### Locked Decisions

#### Trigger Model
- **D-01:** Workflow triggers on merged PRs, not on a schedule.
- **D-02:** `workflow_dispatch` exists for manual recovery/backfill.
- **D-03:** Normal automated runs process merged/closed PRs only.

#### Incremental Boundary & Recovery
- **D-04:** Recovery/backfill uses the extractor's `updated_at` semantics.
- **D-05:** Repository variable is a recovery/backfill cursor, not the normal trigger driver.

#### Publication Mode
- **D-06:** Publish KB updates through one rolling bot PR.
- **D-07:** Commit generated KB output only; keep extraction/classification working data out of git.

#### Cache & State Persistence
- **D-08:** Store the last-successful-run marker in a repository variable.
- **D-09:** Persist `.github-pr-kb/cache` outside git via Actions cache.
- **D-10:** Use workflow artifacts only for debugging, not normal persistence.

#### README Shape
- **D-11:** README is automation-first.
- **D-12:** README still documents local setup, env vars, CLI usage, and KB examples.

#### State Auth Setup
- **D-13:** Support both a fine-grained PAT path and a GitHub App path for repository-variable auth.
- **D-14:** PAT is the default quickstart; GitHub App is the optional advanced path.

### The Agent's Discretion
- Exact helper surface for state/cost-guard logic (YAML-only vs small Python helper vs both)
- PR branch name, PR title, commit message, and idempotent update mechanics
- Manual dispatch inputs (date cursor, force run, target PR range, or simplified recovery toggle)
- Exact README section names and example snippets

### Deferred Ideas (OUT OF SCOPE)
- Scheduled polling runs
- Multi-repo automation
- Publishing working cache files into git
</user_constraints>

---

## Standard Stack

### Existing tools to reuse

| Tool / Surface | Status | Why it matters |
|----------------|--------|----------------|
| `src/github_pr_kb/cli.py` | Existing | Reuse `extract`, `classify`, and `generate` entry points instead of inventing new automation-only commands |
| `src/github_pr_kb/extractor.py` | Existing | Already supports `state`, `since`, `until`, cache merge, and `updated_at` boundaries |
| `src/github_pr_kb/generator.py` | Existing | Already performs KB generation and manifest-based dedup |
| `.github/workflows/ci.yml` | Existing | Canonical repo pattern for checkout + setup-uv + dependency install |
| `gh` CLI / GitHub REST API | Available in Actions | Practical way to update a rolling PR and repository variable |

### No new libraries are required

The repo already contains the Python surfaces needed for the pipeline. The likely implementation
needs are workflow YAML, small Python support code and tests if the planner chooses that route, and
README updates. Avoid adding action-specific Python dependencies unless the final plan proves a real
need.

---

## Architecture Patterns

### Pattern 1: Use subcommands, not `github-pr-kb run`

`github-pr-kb run` is convenient for humans, but automation needs a cost-aware boundary before the
pipeline starts. The workflow should:

1. compute whether new merged PRs exist since the stored cursor,
2. skip the pipeline entirely if none exist,
3. otherwise run:
   - `github-pr-kb extract --repo <owner/name> --state closed --since <cursor>`
   - `github-pr-kb classify`
   - `github-pr-kb generate`

This keeps the workflow aligned with the extractor's existing `updated_at` behavior and avoids
smuggling event-specific logic into the `run` command.

### Pattern 2: Commit `kb/.manifest.json` with `kb/*.md`

`KBGenerator` uses `kb/.manifest.json` as its dedup source of truth. If the automation publishes the
markdown articles but not the manifest, the next fresh runner will rebuild state from disk
imperfectly and may create duplicate slug variants. Phase 8 plans should treat the manifest as part
of the published KB output.

### Pattern 3: Repository variable stores the cursor; cache stores working data

Use the repository variable only for the **last successful incremental boundary**. Keep
`.github-pr-kb/cache/` in Actions cache so the extractor/classifier can reuse previous work without
putting transient data in git. This cleanly separates:

- durable workflow state: repository variable
- transient pipeline cache: Actions cache
- published artifact: `kb/` plus `kb/.manifest.json`

### Pattern 4: Dual-mode auth for repository-variable writes

GitHub's current REST docs for repository variables allow both:
- fine-grained PATs with **Variables: write**
- GitHub App installation tokens with **Variables: write**

That supports a dual-mode workflow:

1. **PAT quickstart path**
   - simplest README onboarding
   - one secret such as `KB_VARIABLES_TOKEN`
2. **GitHub App path**
   - workflow mints an installation token from app credentials
   - better long-term service-account model

The workflow should define deterministic precedence if both are configured (for example: prefer app
credentials, otherwise fall back to PAT), and fail clearly if neither path is configured.

### Pattern 5: Rolling PR update should be idempotent

The publication path needs one stable branch/PR pair. Typical flow:

1. create/update branch
2. commit KB output if files changed
3. create PR if none exists
4. update existing PR if it already exists

This is a better fit for `gh` CLI or a purpose-built PR action than for ad hoc git-only shell
snippets, because the workflow must detect existing open PRs and avoid PR spam.

### Pattern 6: Keep decision logic testable

The riskiest business logic in this phase is not YAML syntax; it is the incremental decision logic:

- has anything new arrived since the stored cursor?
- what cursor should be persisted after success?
- how do manual backfill overrides interact with the saved cursor?

If that logic lives only in YAML/github-script, it becomes harder to test in the repo's normal
pytest suite. A small helper module or script can make Phase 8 easier to verify and less brittle.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Python environment bootstrapping | Custom install shell | `astral-sh/setup-uv` + `uv sync --all-groups --frozen` | Matches existing CI |
| Incremental PR filtering | Custom event-only heuristics | Existing extractor `--since` / `updated_at` behavior | Keeps semantics consistent with cache layer |
| KB dedup reconstruction | Markdown-only dedup guesswork | `kb/.manifest.json` | Existing generator contract |
| Repo variable CRUD | Hand-maintained state file in git | GitHub Actions repository variables API | Matches locked phase decision |

---

## Runtime State Inventory

### Existing mutable state

| State | Location | Owner | Notes |
|-------|----------|-------|-------|
| Extract/classify cache | `.github-pr-kb/cache/` | local runner / Actions cache | ignored by git; safe to persist via cache |
| KB output | `kb/` | git-tracked output | published result |
| KB manifest | `kb/.manifest.json` | generator | must be published with KB files |
| Workflow cursor | repository variable | GitHub repo settings | new Phase 8 automation state |

### State transitions Phase 8 must preserve

1. no-new-PR run -> do not call extract/classify/generate -> do not advance cursor incorrectly
2. successful incremental run -> update KB + persist new cursor
3. failed run -> do not advance success cursor
4. manual backfill/recovery -> allow explicit override without corrupting normal automation state

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| `astral-sh/setup-uv` | workflow setup | Yes | already used in `.github/workflows/ci.yml` |
| GitHub-hosted Ubuntu runner | workflow | Yes | repo already uses `ubuntu-latest` |
| `gh` CLI | PR / API automation | Likely available on hosted runners | still validate in plan execution |
| `.venv/Scripts/python.exe -m pytest` | local validation | Yes | project instruction requires venv Python directly |

No missing local dependencies were found in the repo itself. The external setup burden will be in
GitHub credentials and repo settings, which README must explain clearly.

---

## Validation Architecture

> `workflow.nyquist_validation` is enabled in `.planning/config.json`, so this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_cli.py tests/test_extractor.py tests/test_generator.py -x -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/ -q` |

### Phase Requirements -> Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACTION-01 | Workflow file exists, is wired for merged PR + manual dispatch, and documents required inputs/secrets | unit / file assertion | `.venv/Scripts/python.exe -m pytest tests/ -k "workflow or action" -q` | Likely Wave 0 |
| ACTION-02 | No-new-PR runs short-circuit before extract/classify/generate | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "no_new_pr or cost_guard" -q` | Likely Wave 0 |
| ACTION-03 | Successful run persists repository-variable cursor correctly; failed run does not advance it | unit | `.venv/Scripts/python.exe -m pytest tests/ -k "cursor or state" -q` | Likely Wave 0 |
| INFRA-03 | README documents setup, env vars, CLI usage, and KB example | unit / doc assertion | `.venv/Scripts/python.exe -m pytest tests/ -k "readme" -q` | Likely Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/ -k "workflow or action or readme or cursor" -q`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Phase gate:** full suite green before verification

### Wave 0 Gaps

- [ ] Workflow-focused tests for trigger/auth/state decision logic
- [ ] README contract tests if docs assertions are not already covered

Existing pytest infrastructure is sufficient; Phase 8 should add targeted tests rather than new test
tooling.

---

## Common Pitfalls

### Pitfall 1: Advancing the cursor on failure
If the workflow updates the repository variable before the pipeline fully succeeds, failed runs can
permanently skip PRs. Persist the cursor only after extract/classify/generate and PR publication
finish successfully.

### Pitfall 2: Treating post-merge event time as the extraction boundary
The extractor already uses `pr.updated_at`. If the workflow instead uses merge event timestamps or
raw PR numbers as the incremental boundary, manual recovery and normal automation can drift apart.

### Pitfall 3: Publishing KB markdown without the manifest
This silently breaks dedup expectations on fresh runners and leads to duplicate article slugging on
later runs.

### Pitfall 4: Supporting both PAT and GitHub App without deterministic precedence
If both auth methods are configured and the workflow does not define which wins, troubleshooting
becomes unpredictable. The plan should choose a single precedence rule and document it.

### Pitfall 5: Hiding too much logic in YAML
YAML is fine for orchestration, but state/cost-guard logic becomes hard to test and reason about if
it is embedded only in long shell/github-script blocks.

---

## Likely File Touch Points

- `.github/workflows/` — add the reusable KB automation workflow
- `README.md` — rewrite for automation-first onboarding and dual auth setup
- `src/github_pr_kb/cli.py` or a new helper module — only if planner chooses to extract reusable automation logic from YAML
- `src/github_pr_kb/extractor.py` — only if small supporting hooks are needed for cost/state alignment
- `tests/` — add workflow/state/doc contract coverage

---

## Recommendation to Planner

Split Phase 8 into at least two plans:

1. **Automation mechanics plan** — workflow trigger/auth/cursor/cache/bot-PR behavior, plus any
   helper code and tests needed to make the decision logic reliable.
2. **Documentation plan** — README rewrite that reflects the final shipped workflow, PAT quickstart,
   GitHub App alternative, local CLI usage, env vars, and KB example output.

If the workflow logic becomes too dense, a third plan for state/cost-guard helper code is warranted.
