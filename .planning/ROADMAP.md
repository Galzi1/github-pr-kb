# Roadmap: GitHub PR Knowledge Base Extractor

## Overview

Seven phases build the tool from scratch: a Python project foundation using uv, then a GitHub extractor delivering basic auth and filtered fetching, then extraction resilience with rate-limit backoff and idempotent caching, then a Claude-powered classifier with cost controls, then a markdown KB generator with idempotent merging, then the CLI surface that ties all three together, and finally a GitHub Action with README for automation and hand-off.

Storage format decisions (DB type, schema, cache mechanism) for Phases 2, 3, and 4 are deferred to the `/gsd:discuss-phase` session for each phase, before any implementation begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Foundation** - uv environment, pyproject.toml, Pydantic types, and env configuration
- [x] **Phase 2: GitHub Extraction Core** - basic auth, fetching PR comments, filtering by state and date range
- [x] **Phase 3: Extraction Resilience & Cache** - rate-limit backoff, local cache persistence, idempotency
- [x] **Phase 4: Claude Classifier** - classification, confidence scoring, and cost caching (completed 2026-04-05)
- [ ] **Phase 5: KB Generator** - markdown files with frontmatter, index file, and incremental merge
- [ ] **Phase 6: CLI Integration** - Click commands with --help and actionable error messages
- [ ] **Phase 7: GitHub Action + README** - workflow YAML, cost guard, state persistence, and README

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
- [x] 01-01-PLAN.md — pyproject.toml scaffold, package skeleton, stubs, .env.example, config.py with pydantic-settings validation, smoke test

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
- [x] 02-01-PLAN.md — Pydantic data models (PRRecord, CommentRecord, PRFile) with JSON round-trip tests
- [x] 02-02-PLAN.md — GitHubExtractor with auth, state/date filtering, bot noise detection, and per-PR cache write

### Phase 3: Extraction Resilience & Cache
**Goal**: Extraction survives GitHub rate limits and interrupted runs — already-cached comments are never re-fetched, using PR + comment ID as the immutable dedup key.
**Depends on**: Phase 2
**Requirements**: CORE-03, CORE-04, CORE-05

**Planning Note**: Cache persistence mechanism (file layout, storage schema) will be decided together with the user during `/gsd:discuss-phase 3` BEFORE implementation begins. Cache invalidation strategy is fixed: PR + comment ID is the immutable key — once a comment is cached it is never re-fetched or re-classified.

**Success Criteria** (what must be TRUE):
  1. When the GitHub API returns a 429 or rate-limit header, the tool waits with exponential backoff and resumes without losing already-cached data
  2. Re-running extraction on the same repo does not create duplicate entries in the cache (PR + comment ID is the dedup key)
  3. An interrupted extraction can be resumed; comments already in the cache are skipped entirely on the next run
  4. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: 1 plan

Plans:
- [x] 03-01-PLAN.md — TDD: rate-limit retry (GithubRetry total=5), atomic cache writes (mkstemp + os.replace), merge-based re-runs (comment ID dedup)

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
- [x] 04-01-PLAN.md — ClassifiedComment/ClassifiedFile models, config anthropic_api_key, test scaffolds
- [x] 04-02-PLAN.md — PRClassifier implementation with SHA-256 dedup, atomic writes, and all tests green

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
- [x] 05-01-PLAN.md — KBGenerator core: slugify, article generation with frontmatter, manifest-based incremental dedup
- [ ] 05-02-PLAN.md — Index generation: kb/INDEX.md with category groupings, counts, summaries, and review markers

### Phase 6: CLI Integration
**Goal**: A user can drive the full extract → classify → generate pipeline through named CLI commands with clear help text and actionable error messages.
**Depends on**: Phase 5
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. `github-pr-kb extract --repo owner/name` runs extraction and writes the local cache
  2. `github-pr-kb classify` reads the cache and writes classification results via Claude
  3. `github-pr-kb generate` reads classification results and writes the markdown KB
  4. Every command responds to `--help` with a description, all options listed, and example usage
  5. Errors (missing token, bad repo name, API failure) print a human-readable message pointing to the fix, not a raw traceback
  6. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: TBD

### Phase 7: GitHub Action + README
**Goal**: A repository maintainer can add a provided workflow file and have PR comments automatically extracted and the KB updated on a schedule, with no wasted API calls when nothing is new, and a new user can get from zero to a generated KB by following the README alone.
**Depends on**: Phase 6
**Requirements**: ACTION-01, ACTION-02, ACTION-03, INFRA-03
**Success Criteria** (what must be TRUE):
  1. A ready-to-use GitHub Actions workflow YAML file is included in the repo and can be copied into any target repository
  2. The Action skips extraction entirely when no new PRs exist since the last run (observable: Claude API cost does not increase on no-new-PR runs)
  3. Last-run state is persisted across Action runs so incremental executions only process PRs added since the previous successful run
  4. README contains: setup steps (including uv installation), all required environment variables, CLI command reference, and at least one example of KB output
  5. Tests covering this phase's components pass (mocked external APIs where applicable)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation | 1/1 | Complete | 2026-03-10 |
| 2. GitHub Extraction Core | 2/2 | Complete | 2026-04-03 |
| 3. Extraction Resilience & Cache | 1/1 | Complete | 2026-04-04 |
| 4. Claude Classifier | 2/2 | Complete   | 2026-04-05 |
| 5. KB Generator | 1/2 | In Progress|  |
| 6. CLI Integration | 0/TBD | Not started | - |
| 7. GitHub Action + README | 0/TBD | Not started | - |
