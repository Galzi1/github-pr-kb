# Pitfalls Research: GitHub PR Extraction & Analysis Tools

**Domain:** GitHub API Integration + AI Classification + Knowledge Extraction
**Researched:** 2026-02-13
**Confidence:** HIGH (GitHub official docs + verified best practices)

## Critical Pitfalls

### Pitfall 1: Underestimating GitHub API Rate Limiting Impact

**What goes wrong:**
Tools silently fail or crash when hitting rate limits (5,000 requests/hour for authenticated, 60/hour unauthenticated). Developers start with simple polling loops, succeed on small repos, then fail catastrophically on medium+ repos where they exhaust limits mid-run with no graceful degradation.

**Why it happens:**
- Rate limits feel theoretical until they're hit; developers underestimate how many requests comment extraction requires (PR metadata + comments + review comments = 3+ requests per PR)
- No built-in backoff or retry logic in initial implementation
- Testing only on small repos where limits aren't encountered
- Missing rate limit headers monitoring (X-RateLimit-Remaining, X-RateLimit-Reset)

**How to avoid:**
- **Phase 1 (Architecture):** Design with rate limit awareness from day 1
  - Track X-RateLimit-* headers on every request and implement exponential backoff (1s, 2s, 4s, 8s...)
  - Calculate max requests per PR: metadata (1) + paginated comments (N) + reviews = count carefully
  - Estimate worst-case usage: `PRs × requests_per_PR > 5000/hour?` triggers failure case
  - Implement request queuing with prioritization (recent PRs > old PRs)
- **Phase 2 (MVP):** Test on actual mid-sized repos (100+ PRs) before release
- **Phase 3 (Scaling):** Monitor and alert when 80% of quota is consumed

**Warning signs:**
- 429 Throttled responses appearing in logs
- Tool runs successfully on test repos but fails on production repos
- Comment extraction stopping partway through
- No retry logic or backoff visible in code
- Missing rate limit header checks

**Phase to address:**
Architecture (Phase 1) — Must design pagination and request batching from start. Performance (Phase 3) — Monitor and optimize requests.

---

### Pitfall 2: Uncontrolled LLM Classification Costs Exploding

**What goes wrong:**
Running every PR comment through an LLM (Claude, GPT-4, etc.) for classification causes:
- $100-1000+/month in API costs for moderate usage (1000+ comments/month)
- No cost visibility until bill arrives; budget blowout surprises stakeholders
- Redundant classifications (same comment classified multiple times)
- No cost optimization or model selection strategy

**Why it happens:**
- Developers start with best-in-class models (GPT-4, Claude 3 Opus) because accuracy seems critical
- No batching or caching of identical comments before calling APIs
- Not comparing cost-per-token across providers (Anthropic vs OpenAI vs local models)
- No evaluation of whether smaller/cheaper models would work for this task
- Classifying historical data repeatedly on each run

**How to avoid:**
- **Phase 1 (Architecture):** Evaluate classification with cost-accuracy tradeoffs
  - Research shows fine-tuned smaller models (8B parameter) match LLM accuracy at 10x lower cost
  - Implement request deduplication: hash(comment_text) → cached_classification
  - Set monthly budget hard limits in API client; fail gracefully when exceeded
  - Compare at least 2 models on real sample (GPT-4 vs Claude 3.5 Sonnet vs Llama-based)
- **Phase 2 (MVP):** Use cheaper model for MVP (Claude Haiku, GPT-3.5) and upgrade only if needed
- **Phase 3 (Optimization):** Test model distillation or routing (use small model for 80% of cases, escalate to larger model for uncertain cases)

**Warning signs:**
- Every API call uses latest/largest model without evaluation
- No caching between runs
- Monthly API bill >$100 for modest usage
- Classification latency >1s per comment
- No A/B testing of model accuracy

**Phase to address:**
Architecture (Phase 1) — Choose classification approach and model. Performance (Phase 3) — Optimize costs.

---

### Pitfall 3: Classification Accuracy Drift & Unreliable Categories

**What goes wrong:**
AI classification produces inconsistent, unusable categories:
- Same comment classified differently on different runs
- False positive rate too high (real discussion marked as unrelated)
- Categories too vague or overlapping (PR Review + Code Review + Feedback all mean similar things)
- No way to fix wrong classifications or improve schema over time
- Extracted knowledge not actually useful because categorization is noise

**Why it happens:**
- No schema design for categories before building classifier
- Prompt engineering done once, never validated against real data
- No quality threshold (e.g., reject classifications below 80% confidence)
- Using generic classification templates instead of domain-specific categories for PRs
- No feedback loop or human-in-the-loop correction mechanism

**How to avoid:**
- **Phase 1 (Design):** Define category schema and success criteria
  - Design 5-8 core categories (Bug Fix, Feature Discussion, Architecture, Testing, Documentation, Dependencies, Refactor, Other)
  - Document rules for each: "Bug Fix includes: fixing broken behavior, regression, error handling"
  - Set confidence threshold: reject classifications <75% confidence
  - Validate schema against 100 real comments before implementation
- **Phase 2 (MVP):** Implement with human review stage
  - Store classification + raw LLM response (reasoning)
  - Have humans spot-check 10% of classifications and tag errors
  - Measure: accuracy, precision per category, false positive rate
- **Phase 3 (Improvement):** Add feedback loop
  - Collect human corrections and retrain/recalibrate periodically
  - Monitor drift: track accuracy over time, alert if it drops

**Warning signs:**
- Accuracy metrics never measured or tracked
- Users manually fixing classifications in output
- Same comment gets different categories on re-run
- Classification reasoning not stored or visible
- No feedback mechanism for wrong classifications

**Phase to address:**
Design (Phase 0) — Schema definition. Performance (Phase 3) — Accuracy monitoring and improvement.

---

### Pitfall 4: Unmanaged Knowledge Base Discoverability & Staleness

**What goes wrong:**
Extracted knowledge becomes a "write-once, never read" dump:
- 1000s of markdown files with no search or navigation
- Extracted categories (Bug Fix, Feature) not matching how users think about knowledge
- No updated mechanism: new PRs create duplicate entries for same topic
- Categories drift over time, become meaningless
- Users can't find what they're looking for despite extraction existing
- Knowledge base grows but usefulness decreases

**Why it happens:**
- Focus on extraction, not on knowledge organization and reuse
- No clear categorization schema or ownership model
- No update mechanism: full re-extraction creates duplicates instead of merging
- Missing metadata (date, PR link, contributor) that helps with search
- No discoverability layer (full-text search, tags, relationships)
- Static markdown doesn't scale; needs semantic indexing

**How to avoid:**
- **Phase 1 (Architecture):** Design knowledge organization before extraction
  - Define: how categories map to user questions (e.g., "How do we handle errors?" → Bug Fix + Architecture)
  - Include metadata in outputs: extracted_date, pr_link, contributors, confidence
  - Design for incremental updates: new content merges with existing, doesn't duplicate
  - Plan for searchability: full-text index, tag-based navigation, date-based filtering
- **Phase 2 (MVP):** Build with minimal discoverability
  - Generate table of contents with summaries
  - Include links back to original PRs
  - Implement tag-based categorization (multiple tags per item)
- **Phase 3 (Usability):** Add discovery layer
  - Full-text search engine (even Grep is better than nothing)
  - Relationship mapping (link similar findings across PRs)
  - Merge similar entries when new extractions find duplicate topics
  - Track which knowledge items were accessed/useful

**Warning signs:**
- Knowledge base exists but users don't know about it or can't search it
- Same topic documented in multiple places
- Growing backlog of unread/unreviewed extracted content
- No way to update entries when new PRs discuss same topic
- No metrics on knowledge base usage

**Phase to address:**
Architecture (Phase 1) — Design knowledge schema. Usability (Phase 3) — Add search and deduplication.

---

### Pitfall 5: Pagination & Incremental Sync Mismanagement

**What goes wrong:**
Data extraction fails or misses content:
- Offset-based pagination causes duplicate or missing comments when PRs have concurrent updates
- Extracting same data repeatedly instead of incremental updates (costs, inefficiency)
- No idempotency: re-runs create duplicate entries in knowledge base
- PR comment ordering assumptions break (new comments added since last extraction)
- Webhook handling introduces race conditions with polling

**Why it happens:**
- Developers use simple offset pagination without understanding its pitfalls
- No incremental update design (extract only new/changed data since last run)
- Testing on static repos where pagination doesn't expose issues
- Mixing webhooks (push events) with polling (pull), creating inconsistency
- No cursor or timestamp tracking of what was already extracted

**How to avoid:**
- **Phase 1 (Architecture):** Choose pagination strategy upfront
  - Use cursor-based pagination, not offset (GitHub GraphQL uses cursors, REST can use Link header)
  - For incremental updates: track `updated_at` timestamp, only fetch PRs modified since last run
  - Implement idempotency: use PR+comment ID as key to detect duplicates on re-run
  - If using webhooks: maintain local timestamp to reconcile new events with polling
- **Phase 2 (MVP):** Implement full-history extraction with deduplication
  - Extract all PR comments on first run (accept slower)
  - On incremental runs: fetch only updated PRs (use since=last_run_time parameter)
  - Check for duplicates before inserting into knowledge base
- **Phase 3 (Optimization):** Optimize incremental extraction
  - Batch requests: get multiple PRs per request instead of one-by-one
  - Monitor for missed events (gaps in comment sequence)
  - Consider hybrid: webhook for new activity + periodic full sync for reconciliation

**Warning signs:**
- Duplicate entries in knowledge base
- Comment counts don't match GitHub PR
- Re-running extraction takes same time as initial run (no optimization)
- Missing recent comments on re-extract
- Offset pagination offset values growing unbounded

**Phase to address:**
Architecture (Phase 1) — Pagination strategy. Performance (Phase 3) — Incremental sync optimization.

---

### Pitfall 6: GitHub Action Maintenance & Cost Surprises

**What goes wrong:**
Automation becomes a liability:
- Scheduled GitHub Action runs waste quota on no-change runs (PRs unchanged since last run)
- GitHub Actions pricing changes (2026) cause budget blowout for frequent runs
- Workflow files become technical debt: outdated dependencies, deprecated actions, manual maintenance overhead
- Silent failures: action runs but produces wrong output without alerting
- Stateless runs: no tracking of what was already processed, re-processes everything

**Why it happens:**
- Action scheduled on timer (e.g., hourly) without checking if work is needed
- No cost awareness of GitHub Actions minutes (Linux: 0.008 USD/min, Mac: 0.08 USD/min)
- Workflow YAML not versioned with intent or documentation
- No alerting: action succeeds but output is empty or malformed
- No state management: each run starts from scratch

**How to avoid:**
- **Phase 1 (Architecture):** Design action with cost and state awareness
  - Implement check-before-run: action queries "any new PRs since last run?" before extracting (1 API call)
  - Skip execution if no new data (save 10-100 action minutes per run)
  - Track state: store last_extraction_time in repo (commit to .github/state/ or use artifacts)
  - Document pricing impact: calculate monthly cost for chosen schedule
- **Phase 2 (MVP):** Implement with minimal automation
  - Start with manual trigger or high frequency schedule (daily, not hourly)
  - Monitor first month costs; adjust schedule if needed
  - Set GitHub Actions spending alerts at 50%, 80%, 100% of budget
- **Phase 3 (Maintenance):** Add observability and guardrails
  - Log action execution: what ran, how many PRs processed, how many API requests
  - Alert on anomalies (0 PRs extracted when 10 expected, classification failures)
  - Version action dependencies and review quarterly
  - Implement rollback: keep previous knowledge base snapshot

**Warning signs:**
- GitHub Actions always has remaining minutes unused
- Monthly costs trending up without new PRs being added
- Action runs frequently but produces no output changes
- No logs or visibility into action execution
- Manual steps still needed after automation
- Workflow YAML has outdated action versions

**Phase to address:**
Architecture (Phase 1) — Design efficient automation. Performance (Phase 3) — Monitor and optimize.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded API key in code | Fast local testing | Security breach, credential rotation nightmare, repo scanning catches it | Never for any production code |
| Full re-extraction on every run | Simple to implement, avoid incremental logic | 10x API costs, slow runs, duplicate knowledge entries | Only for MVP on <100 PRs |
| No classification confidence threshold | Any classification accepted | False positives pollute knowledge base, users ignore output | Only during initial testing |
| Offset-based pagination | Easier to implement than cursors | Duplicates and missing data at scale | Only for <100 items total |
| Single endpoint GitHub API calls | Fast prototyping | 3-5x more API calls than batching | Never; switch to batch calls immediately |
| Manual category schema | Get started quickly | Unmaintainable, inconsistent, users confused | Only for first 2 weeks; finalize by end of Design phase |
| No deduplication in knowledge base | Fast knowledge base generation | Same topic documented 10 times, unusable | Only if <50 PRs total; add before MVP |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub API Pagination | Using offset with Link header, assuming order unchanged | Use cursor-based pagination (GraphQL) or check Link header until exhausted; verify comment count matches |
| Rate Limit Handling | Failing hard when 429 response | Implement exponential backoff; read X-RateLimit-Reset header; queue requests if approaching limit |
| LLM API Calls | Calling API for every classification, no caching | Hash comment text; cache results; reuse classifications for identical comments |
| Webhook Events | Relying solely on webhooks for sync | Webhooks miss events; pair with periodic polling; reconcile local state with GitHub source of truth |
| Token Management | Hardcoding token in code or environment variable only | Use GitHub Secrets in Actions; rotate tokens on schedule; use fine-grained tokens with minimal scopes |
| GraphQL vs REST | Mixing both APIs, counting requests wrong | Choose one; if mixing, count GraphQL as 1 request (can fetch multiple PRs per call vs REST needs multiple calls) |
| Conditional Requests | Not using etag/If-Modified-Since headers | Track etag from PR response; on re-fetch, include If-Modified-Since header; 304 response doesn't count against rate limit |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full re-extraction every run | Tool takes 10+ minutes, API quota exhausted | Implement incremental extraction (only changed PRs since last run) | >100 PRs in repository |
| One API call per PR comment | 1000 PRs = 1000+ API calls, hits rate limit at 5K/hour | Batch: use GraphQL to fetch 10 PRs + comments in single call, or REST pagination | >200 PRs |
| LLM API call for every comment | $100+/month costs, 1s+ latency per comment | Cache: deduplicate identical comments, classify once; batch classify 10 comments per request | >500 comments/month |
| Storing full PR + comments in memory | OOM (Out of Memory) errors on large repos | Stream processing: extract, classify, write to disk; don't load all data at once | >10,000 comments |
| No pagination limit (fetch all results) | Timeout, huge responses, network issues | Set page size to 30-100 items; paginate through results; set request timeout | >1000 items per endpoint |
| Search via grep on 10K markdown files | Slow searches (minutes), poor UX | Index knowledge base (even simple: JSON index with full-text); implement tag-based navigation | >5,000 files |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoded GitHub token in code or .env | Token leaked in public repo; attacker can impersonate your app, modify PRs, delete repos | Use GitHub Secrets in Actions; never commit tokens; use fine-grained tokens with only necessary scopes (e.g., read:pull_requests, not admin) |
| Using personal access token instead of GitHub App token | Higher permission footprint; token is tied to individual, not organization | Create GitHub App for automation; use installation tokens (shorter-lived, per-installation scoping) |
| Not rotating tokens | Compromised token used indefinitely | Set token expiration to 90-180 days; rotate on schedule; implement emergency rotation process |
| Accepting all LLM API responses without validation | Malicious/incorrect classifications pollute knowledge base; no audit trail | Validate classification against confidence threshold; store original LLM response (reasoning); enable human review for low-confidence items |
| Storing extracted data (including user comments) without access controls | Privacy breach; extracted knowledge shared with unauthorized users | Apply same access controls to knowledge base as original repo; review extraction contents before sharing; anonymize sensitive data if needed |
| No logging of API requests/responses | Breaches undetected; no audit trail; debugging blind | Log: which user/action initiated extraction, what data was accessed, timestamps; never log tokens; monitor for suspicious patterns |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Knowledge base has no search; users must browse 1000s of files | Users give up, knowledge extraction feels useless | Implement search (even Cmd+F with ctrl+shift+f in editor is better than nothing); add table of contents with summaries and dates |
| Category schema doesn't match user mental model (e.g., "Refactor" when users think "Technical Debt") | Users misclassify findings; knowledge not used | Co-design categories with users; validate schema on real PRs before finalization; allow user feedback to evolve schema |
| Extracted markdown links to PRs are stale (branch deleted, PR closed) | Users click links, get 404; trust in knowledge base decreases | Store PR number + commit SHA; generate links to PR view page; verify links still work on periodic audits |
| No context in extracted snippets (missing PR title, date, participants) | Users don't understand context; can't evaluate relevance | Include metadata: PR title, date, URL, participants, comment counts; link to full PR |
| Too many categories per item; users don't know what content is about | Users skip entries; knowledge base cluttered | Limit to 2-3 primary tags per item; allow optional secondary tags; auto-hide low-confidence classifications |
| Knowledge base grows but never updated; users see stale findings | Trust decreases; users think findings are outdated even if relevant | Implement refresh schedule (quarterly); add "last updated" date to each entry; track if entry is still relevant via usage metrics |

## "Looks Done But Isn't" Checklist

- [ ] **API Integration:** Extraction runs successfully on test repo, but have you tested on production repo with 10x more PRs and comments? Verify no 429 errors and rate limit tracking working.
- [ ] **Classification:** Classifier produces output for all comments, but have you measured accuracy? Reviewed sample of classifications for false positives? Checked consistency (same comment classified same way on re-run)?
- [ ] **Knowledge Base:** Markdown files generated, but can users find what they're looking for? Test with "find me all discussion about error handling" — if you need to manual grep, search isn't ready.
- [ ] **Incremental Updates:** Tool runs faster on second run, but have you verified no duplicates in knowledge base? Checked that all new PRs since last run were captured?
- [ ] **GitHub Action:** Workflow file exists and runs, but do you have cost tracking? Does it fail silently? Have you verified output is correct by spot-checking?
- [ ] **Token Management:** Tool works locally with token, but is token stored securely in production? Can you rotate it without downtime? Is access logged?
- [ ] **Error Handling:** Happy path works, but what happens on 429 rate limit, API timeout, LLM API down, corrupted data? Tool should fail gracefully, not silently.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Rate limit exhausted, extraction incomplete | HIGH | Implement exponential backoff; wait X-RateLimit-Reset seconds; resume from last checkpoint. Requires state tracking and resumable design. |
| LLM API costs out of control | MEDIUM | Audit spending; identify high-cost comment types; switch to cheaper model for MVP; implement caching immediately |
| Knowledge base has duplicates (same topic 10x) | MEDIUM | Write deduplication script: hash content, identify near-duplicates, merge and link; future runs with dedup enabled |
| Classification accuracy drifted (false positives 50%) | MEDIUM | Audit recent classifications; identify when drift started; retrain or recalibrate LLM prompt; implement confidence threshold; flag low-confidence for review |
| Incremental updates missed some PRs | HIGH | Full re-extraction required to reconcile; causes re-processing costs; prevents with proper idempotency keys and comprehensive testing |
| GitHub Action producing wrong output silently | HIGH | Add output validation; alert on anomalies; implement rollback to previous knowledge base; review action logs post-mortem |
| Token compromised and leaked | HIGH | Immediate: revoke token, generate new one, deploy to all runners; Audit: check GitHub audit log for unauthorized actions; if damage done, may need to force-push repos or recover from backup |

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Design: Categorization Schema** | Categories too vague or don't match user needs | Validate with 20-30 real PRs before finalizing; co-design with potential users; allow for "Other" category for edge cases |
| **Design: API Strategy** | Choosing GraphQL without understanding authentication/caching differences | Research GitHub GraphQL auth requirements (requires authentication, no public queries); test caching approach upfront |
| **Architecture: Rate Limiting** | Assuming 5000 req/hour is plenty without calculating worst-case requests per PR | Calculate: 1 req for PR metadata + N reqs for paginated comments + M reqs for reviews = total requests per PR; test on 100-PR repo |
| **Architecture: LLM Integration** | Starting with expensive model without baseline cost | Create simple cost calculator: comments × tokens × $/1M tokens; test on 10 PRs; extrapolate to prod; choose model based on budget |
| **Architecture: Knowledge Storage** | Designing for eventual Postgres/ElasticSearch without testing markdown-only approach | Start with markdown + Git history; validate with users that search/discoverability is usable; only add DB if needed |
| **MVP: Data Completeness** | Extracting only current PR state without understanding how to handle updates | Decide early: full re-extract each run? Or incremental? Document approach; implement deduplication regardless |
| **MVP: Automation** | Deploying action without cost awareness or failure monitoring | Calculate monthly cost before deployment; set budget alerts; add logging and error notifications |
| **Performance: Caching** | Adding caching without measuring actual hit rate | Benchmark before/after: measure cache hit %, storage size, latency improvement; ensure cache invalidation doesn't introduce stale data bugs |
| **Maintenance: Technical Debt** | Shipping with shortcuts (hardcoded tokens, no error handling) | Document all shortcuts; assign debt payoff phase before launch; prioritize security debt (tokens) |

## Sources

- [Rate limits for the REST API - GitHub Docs](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [A Developer's Guide: Managing Rate Limits for the GitHub API - Lunar](https://www.lunar.dev/post/a-developers-guide-managing-rate-limits-for-the-github-api)
- [Best Practices for Handling GitHub API Rate Limits - GitHub Community](https://github.com/orgs/community/discussions/151675)
- [Rate limits for GitHub Apps - GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/rate-limits-for-github-apps)
- [Best practices for using the REST API - GitHub Docs](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)
- [Managing your personal access tokens - GitHub Docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Keeping your API credentials secure - GitHub Docs](https://docs.github.com/en/rest/authentication/keeping-your-api-credentials-secure)
- [GITHUB_TOKEN: How It Works - StepSecurity](https://www.stepsecurity.io/blog/github-token-how-it-works-and-how-to-secure-automatic-github-action-tokens)
- [5 Common API Integration Mistakes - Lonti](https://www.lonti.com/blog/5-common-api-integration-mistakes-and-how-to-avoid-them)
- [Cost-Aware Model Selection for Text Classification - ArXiv](https://arxiv.org/html/2602.06370)
- [LLM Cost Optimization: Stop Overpaying 5-10x in 2026 - byteiota](https://byteiota.com/llm-cost-optimization-stop-overpaying-5-10x-in-2026/)
- [Knowledge Discovery & Management in 2026 - Marcus P. Zillman](https://www.zillman.us/knowledge-discovery-resources-2026/)
- [Top Knowledge Management System Features in 2026 - Context Clue](https://context-clue.com/blog/top-10-knowledge-management-system-features-in-2026/)
- [Knowledge Management in 2026: Trends, Technology & Best Practice - Vable](https://www.vable.com/blog/knowledge-management-in-2026-trends-technology-best-practice)
- [The 10 Best Knowledge Base Software in 2026 - Help Scout](https://www.helpscout.com/blog/knowledge-base-software/)
- [10 API pagination best practices in 2026 - Merge](https://www.merge.dev/blog/api-pagination-best-practices)
- [Guide to API Pagination - Treblle](https://treblle.com/blog/api-pagination-guide-techniques-benefits-implementation)
- [Webhook events and payloads - GitHub Docs](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
- [About webhooks - GitHub Docs](https://docs.github.com/en/webhooks/about-webhooks)
- [Data Classification Guide - Satori](https://satoricyber.com/data-classification/data-classification/)
- [Types of Technical Debt & Categories - Guide 2026 - Leanware](https://www.leanware.co/insights/technical-debt-types-categories)
- [GitHub Actions Pricing Changes 2026 - devops-geek](https://devops-geek.net/devops-lab/github-actions-pricing-changes-2026-what-devops-geeks-need-to-know/)
- [REST vs. GraphQL vs. gRPC: Choosing the Right API Style for 2026 - Toolshelf](https://toolshelf.tech/blog/rest-vs-graphql-vs-grpc-api-comparison-2026/)
- [GraphQL vs REST: Top 4 Advantages & Disadvantages - Research.aimultiple](https://research.aimultiple.com/graphql-vs-rest/)

---

*Pitfalls research for: GitHub PR Extraction & Analysis Tools*
*Researched: 2026-02-13*
