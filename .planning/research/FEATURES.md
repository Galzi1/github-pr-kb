# Feature Landscape

**Domain:** GitHub PR Knowledge Extraction Tools
**Researched:** 2026-02-13

## Table Stakes

Features users/stakeholders expect. Missing one = product feels incomplete for intended use case.

| Feature | Why Expected | Complexity | Phase | Notes |
|---------|--------------|------------|-------|-------|
| **Extract PR comments from repository** | Core requirement; cannot classify what you don't extract | Low | 1 | PyGithub handles pagination; straightforward API call |
| **Classify comments into topics with AI** | Core value; why not just grep? | Medium | 1 | Prompt engineering needed; structured outputs required |
| **Generate markdown knowledge base** | Output must be consumable; markdown is standard | Low | 1 | File I/O + Markdown formatting; no parsing needed |
| **Filter PRs by date range or state** | Enable historical analysis; avoid processing 10K closed PRs | Low | 1 | PyGithub query parameters; minimal effort |
| **CLI interface to run extraction** | Automation and reproducibility; not just library | Low | 1 | Click decorator-based syntax; standard entry point |
| **Support GitHub authentication** | Must work with private repos; required for real usage | Low | 1 | Environment variable (GITHUB_TOKEN); PyGithub handles auth |
| **Handle GitHub API rate limits gracefully** | Will hit 5000 req/hr limit with 100+ PRs | Low | 1 | Check response headers; implement backoff or caching logic |
| **Persist extracted comments locally** | Don't re-download every run; enable diffing | Medium | 1/2 | Simple JSON cache in .cache/; enables incremental extraction |
| **Generate readable markdown output** | Not a wall of text; organized by topic | Medium | 1 | Directory structure: kb/topic/slug.md with YAML frontmatter |
| **Configurable classification categories** | Different projects have different knowledge types | Medium | 2 | Config file (YAML) or CLI flags for topic categories |

---

## Differentiators

Features that set product apart. Not expected, but valuable for discoverability and maintainability.

| Feature | Value Proposition | Complexity | Phase | Notes |
|---------|-------------------|----------|-------|-------|
| **Cross-reference PR links in KB** | Navigate from KB article back to PR discussion context | Medium | 1 | Add PR number + link in YAML frontmatter; build index in Phase 2 |
| **Time-series analysis of architectural patterns** | See how decisions evolved over time; spot recurring issues | High | 3 | Requires database + dashboard; Phase 3 feature |
| **Confidence scores on classifications** | Know which recommendations are certain vs speculative | Medium | 1 | Use Claude's tool_use response confidence; include in frontmatter |
| **Multi-repo aggregation with deduplication** | Build KB across multiple projects; identify company-wide patterns | High | 2/3 | Requires semantic similarity detection; Phase 2/3 |
| **Automatic KB updates on new PRs** | Real-time knowledge capture; GitHub Action trigger | Medium | 2 | GitHub Action workflow; scheduled or webhook-based |
| **Knowledge decay detection** | Flag recommendations that become outdated (e.g., old dependencies) | High | 3 | Requires versioning + time metadata; Phase 3 |
| **Topic clustering via embeddings** | Group related articles without manual tagging | High | 3 | Requires embeddings model; likely Claude embeddings API |
| **FAQ generation from KB** | Auto-synthesize common questions from patterns | High | 3 | Summarization task; Phase 3 |
| **Search & filter KB** | Navigate large KB; semantic search for "how do we handle X?" | High | 3 | Full-text search (Elasticsearch) + embeddings (Phase 3) |

---

## Anti-Features

Features to explicitly NOT build in MVP/Phase 1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Web dashboard in Phase 1** | Markdown files sufficient; adds deployment complexity | CLI tool now; add web UI in Phase 3 only if user demand |
| **Real-time PR webhook processing** | Scheduled daily/weekly extraction simpler to test | Implement GitHub Action trigger in Phase 2 |
| **Multi-repo processing in Phase 1** | Scope creep; single repo validates core logic | Single repo config in Phase 1; multi-repo in Phase 2 |
| **Database for KB storage** | Markdown files are searchable and versionable | Keep files; add database index only in Phase 3 for search |
| **Async/concurrent PR fetching in Phase 1** | Synchronous PyGithub sufficient at single-repo scale | Add async in Phase 2 if processing 10+ repos needed |
| **Advanced NLP (embeddings, clustering) in Phase 1** | Claude's prompt engineering sufficient for MVP | Add embeddings Phase 3 if semantic search needed |
| **Authentication & authorization** | Single-repo single-user MVP; no multi-tenant complexity | Keep as CLI tool accessing single token |
| **Webhook integration to Slack/Discord** | Out of scope; KB is source of truth, not notifications | Can add as Phase 3 enhancement (optional) |
| **Automatic code snippet extraction** | Over-complicates classification; focus on comment text | Manually link code examples in markdown frontmatter |

---

## Feature Dependencies

```
Extract PR Comments (Foundation)
    ↓
Classify with Claude (Requires: Extract)
    ↓
Generate Markdown KB (Requires: Classify)
    ↓
├─ Persist Cache (Optional, enables Phase 2)
├─ CLI Interface (Required, enables manual usage)
└─ Documentation (Required for reproducibility)

[Phase 2]
Multi-Repo Support (Requires: Phase 1 core)
    ↓
Incremental Extraction (Requires: Caching from Phase 1)
    ↓
KB Index/Search (Requires: Multi-Repo)

[Phase 3]
Web Dashboard (Requires: KB Index from Phase 2)
    ↓
Real-time GitHub Action (Requires: Solid Phase 1/2 foundation)
```

**Critical Path for MVP:**
1. ✅ Extract PR Comments (Foundation — 1-2 days)
2. ✅ Classify with Claude (Core logic — 2-3 days)
3. ✅ Generate Markdown (Output — 1 day)
4. ✅ CLI tool (Interface — 1 day)
5. ✅ Testing & documentation (Quality — 2 days)

**Total MVP critical path: ~1-1.5 weeks**

---

## MVP Recommendation

### Phase 1: MVP Features (Weeks 1-4)

**Prioritize (in order):**

1. **Extract PR Comments from Single Repository**
   - Input: GitHub repo (owner/name), date range (optional), PR state (open/closed/all)
   - Output: JSON cache file (comments + metadata)
   - Why first: Foundation for everything else; enables testing classifier independently

2. **Classify Comments with Claude Structured Outputs**
   - Input: PR comment text
   - Output: JSON with {category, confidence, summary}
   - Categories: architecture_decision, code_pattern, gotcha, domain_knowledge, other
   - Why: Core value prop; determines KB organization

3. **Generate Markdown Knowledge Base from Classifications**
   - Input: Classified comments + PR metadata
   - Output: kb/category/slug.md files with YAML frontmatter
   - Structure: Each article includes author, PR link, date, confidence
   - Why: Makes knowledge discoverable and versionable

4. **CLI Interface (Click)**
   - Commands: `extract`, `classify`, `generate`
   - Options: --repo, --token, --start-date, --end-date
   - Why: Enable scripting and GitHub Action integration

5. **Documentation**
   - README with setup instructions
   - Example KB output
   - Development guide for future contributors
   - Why: MVP incomplete without docs

### Defer to Phase 2+

- ❌ Multi-repo support (add in Phase 2)
- ❌ Incremental extraction (add after Phase 1 validation)
- ❌ Advanced search/KB index (Phase 3)
- ❌ Web dashboard (Phase 3)
- ❌ Real-time processing (Phase 2 GitHub Action)
- ❌ Analytics/reporting (Phase 3)

---

## Success Metrics for Each Feature

| Feature | MVP Success Metric | Phase 2 Target | Phase 3 Target |
|---------|-------------------|----------------|----------------|
| **PR Comment Extraction** | Extract 100% of comments from single repo without errors | Handle 10+ repos without rate limiting | Incremental extraction (only new PRs) |
| **Classification Accuracy** | 80%+ developer agreement on category assignment | 90%+ with feedback loop | 95%+ with retraining |
| **Markdown Generation** | All comments organized by category; readable output | Cross-linked across repos | Full-text searchable |
| **CLI Usability** | Run extraction with single command; --help is clear | Scheduled execution (cron/GitHub Action) | Web UI available |
| **Documentation** | README + example output; new dev can run in 10min | Video tutorials; contributing guide | Full API docs |

---

## Research Findings on Competitive Features

Based on 2025-2026 research on PR analysis tools:

**Existing Tools (Greptile, PR Agent, etc.):**
- ✅ Extract & classify PR comments ← We're here
- ⚠️ Real-time webhook processing ← Nice-to-have, Phase 2
- ⚠️ Multi-code-provider support (GitHub/GitLab/Bitbucket) ← Out of scope
- ⚠️ Code review automation (generate comments) ← Different use case
- ✅ Markdown output for knowledge base ← Differentiator

**Gap we're addressing:**
- Most tools focus on generating suggestions (feedback) not extracting knowledge
- Our focus on preserving architectural decisions from discussions is novel
- Markdown-first output is differentiator (portable, versionable, Git-friendly)

---

## Classification Categories (Recommended for MVP)

Based on PR discussion patterns observed in 2025-2026 research:

```
architecture_decision
  └─ "We decided to use async everywhere"
  └─ "Database migration strategy: plan for downtime"

code_pattern
  └─ "Here's how we handle error handling across projects"
  └─ "Consistent way to structure React components"

gotcha
  └─ "Watch out: this library has memory leaks on version X.Y"
  └─ "Django's ORM N+1 issue when doing this..."

domain_knowledge
  └─ "Payment processing takes 48 hours to settle"
  └─ "Why we support IE11 (compliance requirement)"

other
  └─ Comments that don't fit above
```

**Note:** Categories can be extended via config in Phase 2; use these 4 + "other" for MVP.

---

## Feature Complexity Estimation

| Feature | Effort | Uncertainty | Dependencies |
|---------|--------|-------------|--------------|
| Extract PR Comments | 1-2 days | Low | PyGithub API knowledge |
| Classify with Claude | 2-3 days | Medium | Prompt engineering iteration |
| Generate Markdown | 1 day | Low | File I/O knowledge |
| CLI Interface | 1 day | Low | Click framework basics |
| Testing suite | 1-2 days | Low | pytest + mocking GitHub API |
| Documentation | 1-2 days | Low | Markdown writing |
| **Total MVP** | **~8-10 days** | **Medium** | None blocking |

---

## Sources

- [Atlassian Code Review ML Classifier](https://www.atlassian.com/blog/atlassian-engineering/ml-classifier-improving-quality) — ML patterns for comment filtering
- [PR Agent](https://pypi.org/project/pr-agent/) — Competitor research on PR analysis automation
- [Greptile Code Intelligence](https://www.greptile.com/content-library/best-code-review-github) — Market analysis of PR tools
- [Towards Data Science: PR Data Extraction](https://towardsdatascience.com/how-to-get-pull-request-data-using-github-api-b91891cbd54c/) — GitHub API patterns for PR analysis

---

*Feature landscape for: GitHub PR Knowledge Extraction Tools*
*Researched: 2026-02-13*
