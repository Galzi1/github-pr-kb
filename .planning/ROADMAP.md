# Roadmap: GitHub PR Knowledge Base Extractor

## Overview

Nine phases build the tool from scratch: a Python project foundation using uv, then a GitHub extractor delivering basic auth and filtered fetching, then extraction resilience with rate-limit backoff and idempotent caching, then a Claude-powered classifier with cost controls, then a markdown KB generator with idempotent merging, then the CLI surface that ties all three together, a GitHub Action with README for automation and hand-off, and finally wiki-style topic synthesis that merges related articles into compounding topic pages.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Foundation** - uv environment, pyproject.toml, Pydantic types, and env configuration
- [x] **Phase 2: GitHub Extraction Core** - basic auth, fetching PR comments, filtering by state and date range
- [x] **Phase 3: Extraction Resilience & Cache** - rate-limit backoff, local cache persistence, idempotency
- [x] **Phase 4: Claude Classifier** - classification, confidence scoring, and cost caching (completed 2026-04-05)
- [x] **Phase 5: KB Generator** - markdown files with frontmatter, index file, and incremental merge (completed 2026-04-06)
- [x] **Phase 6: CLI Integration** - Click commands with --help and actionable error messages (completed 2026-04-06)
- [x] **Phase 7: Fix Article Generation Quality** - fix misleading output, useless articles, and meaningless classification-failed files
- [x] **Phase 8: GitHub Action + README** - workflow YAML, cost guard, state persistence, and README
- [ ] **Phase 9: Wiki-style KB Synthesis** - topic pages with cross-references and chronological awareness

## Phase Details

### Phase 1: Project Foundation
**Goal**: A developer can install and configure the project locally using uv, with all dependencies resolved and environment variables validated before running any commands.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-04
**Success Criteria** (what must be TRUE):
  1. `uv sync` succeeds from a fresh clone with no manual pip steps (uv itself must be installed; venv is created and activated via uv)
  2. All runtime and dev dependencies are declared in `pyproject.toml` with version pins; no `requirements.txt` is needed
  3. `.env.example` lists every required environment variable with a description of what each is for
  4. Missing required environment variable causes an immediate, descriptive error rather than a cryptic downstream failure
  5. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md - pyproject.toml scaffold, package skeleton, stubs, .env.example, config.py with pydantic-settings validation, smoke test

### Phase 2: GitHub Extraction Core
**Goal**: A user can authenticate to GitHub and fetch PR comments from a repository, filtered by state and date range, with results written to local storage.
**Depends on**: Phase 1
**Requirements**: CORE-01, CORE-02

**Planning Note**: Storage format (JSON file structure, schema, local cache mechanism) will be decided together with the user during `/gsd:discuss-phase 2` BEFORE implementation begins.

**Success Criteria** (what must be TRUE):
  1. User can extract all PR comments from a repository using a personal access token, with results written to a local cache
  2. User can filter extraction by PR state (open/closed/all) and an optional date range; only matching PRs are fetched
  3. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md - Pydantic data models (PRRecord, CommentRecord, PRFile) with JSON round-trip tests
- [x] 02-02-PLAN.md - GitHubExtractor with auth, state/date filtering, bot noise detection, and per-PR cache write

### Phase 3: Extraction Resilience & Cache
**Goal**: Extraction survives GitHub rate limits and interrupted runs - already-cached comments are never re-fetched, using PR + comment ID as the immutable dedup key.
**Depends on**: Phase 2
**Requirements**: CORE-03, CORE-04, CORE-05

**Planning Note**: Cache persistence mechanism (file layout, storage schema) will be decided together with the user during `/gsd:discuss-phase 3` BEFORE implementation begins. Cache invalidation strategy is fixed: PR + comment ID is the immutable key - once a comment is cached it is never re-fetched or re-classified.

**Success Criteria** (what must be TRUE):
  1. When the GitHub API returns a 429 or rate-limit header, the tool waits with exponential backoff and resumes without losing already-cached data
  2. Re-running extraction on the same repo does not create duplicate entries in the cache (PR + comment ID is the dedup key)
  3. An interrupted extraction can be resumed; comments already in the cache are skipped entirely on the next run
  4. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 1 plan

Plans:
- [x] 03-01-PLAN.md - TDD: rate-limit retry (GithubRetry total=5), atomic cache writes (mkstemp + os.replace), merge-based re-runs (comment ID dedup)

### Phase 4: Claude Classifier
**Goal**: A user can classify cached PR comments into categories using Claude, with results stored locally, and identical comments never sent to the API twice.
**Depends on**: Phase 3
**Requirements**: CLASS-01, CLASS-02, CLASS-03, CLASS-04

**Planning Note**: Classification result storage schema will be decided together with the user during `/gsd:discuss-phase 4` BEFORE implementation begins.

**Success Criteria** (what must be TRUE):
  1. Cached comments are classified into one of: architecture_decision, code_pattern, gotcha, domain_knowledge, other
  2. Each classification result includes the original comment, category, confidence score, and a one-line summary
  3. Comments with confidence below 75% are flagged for review in the classification output
  4. Re-running classify on already-classified comments results in zero new Claude API calls (cache hit verified by cost staying flat on repeat runs)
  5. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md - ClassifiedComment/ClassifiedFile models, config anthropic_api_key, test scaffolds
- [x] 04-02-PLAN.md - PRClassifier implementation with SHA-256 dedup, atomic writes, and all tests green

### Phase 5: KB Generator
**Goal**: A user can generate an organized markdown knowledge base from classified comments, and re-running generation does not duplicate existing content.
**Depends on**: Phase 4
**Requirements**: KB-01, KB-02, KB-03, KB-04
**Success Criteria** (what must be TRUE):
  1. Running generate produces markdown files organized into per-category subdirectories (e.g., `kb/architecture_decision/`, `kb/gotcha/`)
  2. Each KB article has YAML frontmatter containing: PR link, author, date, category, and confidence score
  3. An index file is produced listing all topics with article counts and one-line summaries
  4. Re-running generate after adding new classified comments merges new articles without duplicating previously-generated entries (PR + comment ID dedup)
  5. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md - KBGenerator core: slugify, article generation with frontmatter, manifest-based incremental dedup
- [x] 05-02-PLAN.md - Index generation: kb/INDEX.md with category groupings, counts, summaries, and review markers

### Phase 6: CLI Integration
**Goal**: A user can drive the full extract -> classify -> generate pipeline through named CLI commands with clear help text and actionable error messages.
**Depends on**: Phase 5
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. `github-pr-kb extract --repo owner/name` runs extraction and writes the local cache
  2. `github-pr-kb classify` reads the cache and writes classification results via Claude
  3. `github-pr-kb generate` reads classification results and writes the markdown KB
  4. Every command responds to `--help` with a description, all options listed, and example usage
  5. Errors (missing token, bad repo name, API failure) print a human-readable message pointing to the fix, not a raw traceback
  6. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md - Click CLI: extract, classify, generate, run commands with lazy imports, colored output, CliRunner tests

### Phase 7: Fix Article Generation Quality
**Goal**: Fix misleading output, useless articles (copied comments without processing), and meaningless classification-failed files so the generated KB contains genuinely useful, well-synthesized knowledge articles.
**Depends on**: Phase 6
**Requirements**: Q-01, Q-02, Q-03, Q-04
**Success Criteria** (what must be TRUE):
  1. CLI output accurately reflects what happened (no misleading messages)
  2. Generated articles synthesize and add value beyond the raw comment text
  3. Classification failures are handled gracefully (no meaningless `classification-failed-*.md` files)
  4. Tests covering this phase's components pass
**Plans**: 3 plans

Plans:
- [x] 07-01-PLAN.md - Fix classifier failure handling, extend config with new settings, extend GenerateResult model
- [x] 07-02-PLAN.md - Replace raw-comment-copy generator with Claude-powered synthesis, add confidence filtering and regeneration
- [x] 07-03-PLAN.md - Fix CLI output accuracy, add --regenerate flag, API key validation for generate

### Phase 8: GitHub Action + README
**Goal**: A repository maintainer can add a provided workflow file and have PR comments automatically extracted after merged PRs or manual recovery runs, with no wasted API calls when nothing is new, and a new user can get from zero to a generated KB by following the README alone.
**Depends on**: Phase 7
**Requirements**: ACTION-01, ACTION-02, ACTION-03, INFRA-03
**Success Criteria** (what must be TRUE):
  1. A ready-to-use GitHub Actions workflow YAML file is included in the repo and can be copied into any target repository
  2. The Action skips extraction entirely when no new PRs exist since the last run (observable: Claude API cost does not increase on no-new-PR runs)
  3. Last-run state is persisted across Action runs so incremental executions only process PRs added since the previous successful run
  4. README contains: setup steps (including uv installation), all required environment variables, CLI command reference, and at least one example of KB output
  5. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 3 plans

Plans:
- [x] 08-01-PLAN.md - testable action-state helper for no-new-PR guard and cursor decisions
- [x] 08-02-PLAN.md - merged-PR workflow with dual-mode variable auth, cache reuse, and rolling KB PR publication
- [x] 08-03-PLAN.md - automation-first README rewrite with PAT quickstart, GitHub App option, and local CLI docs

### Phase 9: Wiki-style KB synthesis - merge related articles into compounding topic pages with cross-references and contradiction detection

**Goal:** The generate command produces topic pages (not per-comment articles) as the primary KB output, grouping related classified comments into synthesized topic pages with inline PR citations, cross-references, and chronological awareness.
**Requirements**: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12
**Depends on:** Phase 8
**Plans:** 3 plans

Plans:
- [ ] 09-01-PLAN.md - TopicGroup/TopicPlan models, python-frontmatter dep, nested manifest with auto-migration, topic planning pass
- [ ] 09-02-PLAN.md - Topic synthesis pass with in-memory articles, inline PR citations, cross-references, broken link stripping
- [ ] 09-03-PLAN.md - Wire synthesis into generate_all(), --no-synthesize CLI flag, INDEX.md links to topic pages

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation | 1/1 | Complete | 2026-03-10 |
| 2. GitHub Extraction Core | 2/2 | Complete | 2026-04-03 |
| 3. Extraction Resilience & Cache | 1/1 | Complete | 2026-04-04 |
| 4. Claude Classifier | 2/2 | Complete   | 2026-04-05 |
| 5. KB Generator | 2/2 | Complete   | 2026-04-06 |
| 6. CLI Integration | 1/1 | Complete   | 2026-04-06 |
| 7. Fix Article Generation Quality | 3/3 | Complete | 2026-04-08 |
| 8. GitHub Action + README | 3/3 | Complete | 2026-04-14 |
| 9. Wiki-style KB Synthesis | 0/3 | Planning complete | - |
