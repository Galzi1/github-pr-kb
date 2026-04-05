# Requirements: GitHub PR Knowledge Base Extractor

**Defined:** 2026-03-07
**Core Value:** Preserve and make discoverable the architectural decisions, code patterns, gotchas, and domain knowledge that naturally emerge in PR discussions but typically get lost in closed PR threads.

## v1 Requirements

### Core Extraction

- [x] **CORE-01**: User can extract all PR comments from a GitHub repository using a personal access token
- [ ] **CORE-02**: User can filter extraction by PR state (open/closed/all) and optional date range
- [x] **CORE-03**: Tool handles GitHub API rate limits with exponential backoff and resumes without data loss
- [x] **CORE-04**: Extracted comments are cached locally (JSON) so re-runs avoid redundant API calls
- [x] **CORE-05**: Extraction is idempotent — re-running does not duplicate cached data (PR+comment ID as key)

### Classification

- [x] **CLASS-01**: User can classify PR comments into categories: architecture_decision, code_pattern, gotcha, domain_knowledge, other
- [x] **CLASS-02**: Each classification includes a confidence score; items below 75% threshold are flagged for review
- [x] **CLASS-03**: Identical comments (matched by content hash) reuse cached classifications to minimize Claude API costs
- [x] **CLASS-04**: Classification output includes: original comment, category, confidence score, and one-line summary

### Knowledge Base

- [ ] **KB-01**: User can generate a markdown knowledge base organized into per-category subdirectories
- [ ] **KB-02**: Each KB article includes YAML frontmatter: PR link, author, date, category, confidence score
- [ ] **KB-03**: Generator produces an index file listing all topics with article counts and summaries
- [ ] **KB-04**: Incremental KB generation merges new content without duplicating existing entries (PR+comment ID dedup)

### CLI

- [ ] **CLI-01**: User can run `github-pr-kb extract --repo owner/name` to extract and cache PR comments
- [ ] **CLI-02**: User can run `github-pr-kb classify` to classify cached comments via Claude
- [ ] **CLI-03**: User can run `github-pr-kb generate` to write the markdown knowledge base from classifications
- [ ] **CLI-04**: All commands provide clear `--help` output and actionable error messages

### GitHub Action

- [ ] **ACTION-01**: User can trigger automated extraction via a provided GitHub Actions workflow file
- [ ] **ACTION-02**: GitHub Action only runs extraction when new PRs exist since the last run (cost-aware guard)
- [ ] **ACTION-03**: GitHub Action persists last-run state so incremental runs skip already-processed PRs

### Infrastructure

- [x] **INFRA-01**: Project ships with `pyproject.toml` declaring all runtime and dev dependencies with version pins
- [ ] **INFRA-02**: Test suite covers extractor, classifier, and generator using mocked GitHub and Claude APIs
- [ ] **INFRA-03**: README documents setup, environment variables, CLI usage, and includes example KB output
- [x] **INFRA-04**: `.env.example` template documents all required environment variables

## v2 Requirements

### Automation & Scale
- **SCALE-01**: Multi-repo aggregation with deduplication across repositories
- **SCALE-02**: Incremental extraction using GitHub webhooks for real-time capture
- **SCALE-03**: Async/concurrent PR fetching for processing 10+ repositories

### Discoverability
- **DISC-01**: Full-text search index over the knowledge base (SQLite or similar)
- **DISC-02**: Tag-based navigation with multiple tags per KB article
- **DISC-03**: Relationship mapping linking similar findings across PRs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard | CLI covers the use case; deployment complexity not justified for MVP |
| Real-time webhook processing | Scheduled/manual extraction sufficient; webhooks add complexity |
| Multi-repo support | Single repo validates core logic first |
| OAuth / multi-tenant auth | Single token, single user for MVP |
| Async/concurrent fetching | Sync PyGithub sufficient at single-repo scale |
| SQLite / database for KB | Markdown + git history sufficient; add only if search needed |
| Slack/Discord notifications | KB is source of truth, not notifications |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete (01-01) |
| INFRA-04 | Phase 1 | Complete (01-01) |
| CORE-01 | Phase 2 | Complete |
| CORE-02 | Phase 2 | Pending |
| CORE-03 | Phase 3 | Complete |
| CORE-04 | Phase 3 | Complete |
| CORE-05 | Phase 3 | Complete |
| CLASS-01 | Phase 4 | Complete |
| CLASS-02 | Phase 4 | Complete |
| CLASS-03 | Phase 4 | Complete |
| CLASS-04 | Phase 4 | Complete |
| KB-01 | Phase 5 | Pending |
| KB-02 | Phase 5 | Pending |
| KB-03 | Phase 5 | Pending |
| KB-04 | Phase 5 | Pending |
| CLI-01 | Phase 6 | Pending |
| CLI-02 | Phase 6 | Pending |
| CLI-03 | Phase 6 | Pending |
| CLI-04 | Phase 6 | Pending |
| ACTION-01 | Phase 7 | Pending |
| ACTION-02 | Phase 7 | Pending |
| ACTION-03 | Phase 7 | Pending |
| INFRA-02 | distributed (phases 1-7) | Pending |
| INFRA-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-10 — Phase structure revised: Phase 2 split into 2+3, testing distributed, Phase 7 (Testing & Docs) removed, new Phase 7 is GitHub Action + README*
