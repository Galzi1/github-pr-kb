# Phase 9: Topic-Grouped KB Synthesis - Research

**Researched:** 2026-04-16
**Revised:** 2026-04-16 - reframed around github-pr-kb's goal, not generic LLM Wiki
**Domain:** Improving generate output quality via topic grouping, cross-referencing, and chronological awareness
**Confidence:** HIGH (multiple implementations examined, filtered for relevance to this project)

---

## Summary

The current `generate` command writes one article per classified PR comment. When a repository has 5 PRs that all discuss authentication gotchas, the KB contains 5 separate articles - each individually synthesized but collectively redundant and hard to navigate. This is the core problem Phase 9 solves.

**The fix is not building an LLM Wiki.** The fix is making `generate` smarter: after writing per-comment articles (the current behavior), a second pass groups related articles by topic and produces one synthesized topic page per concept. The topic pages *replace* the per-comment articles as the primary KB output - not a parallel layer alongside them.

Key technique borrowed from the LLM Wiki pattern: **two-pass LLM synthesis** (plan which topics exist, then write each topic page). But adapted to our constraints:

- No `[[wikilinks]]` - standard markdown links that render on GitHub
- No separate `synthesize` CLI command - integrated into `generate` (with `--no-synthesize` escape hatch)
- No standalone contradiction linter - the synthesis prompt handles chronological evolution naturally ("This approach was later superseded in PR #456")
- No `.topics.json` - extend the existing `.manifest.json`
- Topic pages replace per-comment articles, not sit alongside them

**Primary recommendation:** Extend `KBGenerator` with a `_synthesize_topics()` post-pass that runs after `_run_generation_pass()`. Per-comment articles become intermediate artifacts (still written for manifest tracking) but the final KB output is topic pages organized by category.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | >=0.84.0 (already pinned) | Claude API for topic planning and synthesis | Already in project |
| `python-frontmatter` | 1.1.0 | Parse and write YAML frontmatter in markdown files | Replaces fragile `_parse_article_metadata()` in generator.py; handles quoted values with colons, multiline, encoding |
| `pydantic` | >=2.12.5 (already pinned) | TopicPage, SynthesisResult models | Already in project; same pattern as ClassifiedComment |

### Supporting

| Library | Version | Purpose |
|---------|---------|---------|
| `hashlib` (stdlib) | stdlib | SHA-256 content hash to skip unchanged topics on re-runs |
| `pathlib` (stdlib) | stdlib | All file operations (project standard) |
| `re` (stdlib) | stdlib | Extract markdown links for cross-reference tracking |

### Not Needed

| Library | Why Not |
|---------|---------|
| Vector DB / embeddings | The LLM planning pass handles semantic grouping; no infra needed |
| Graph database | Standard markdown links are sufficient for cross-references |
| `obsidiantools` / wikilink parsers | We use standard markdown links, not `[[wikilinks]]` |

**Installation:**
```bash
uv add python-frontmatter
```

---

## Architecture Patterns

### How It Fits Into the Existing Pipeline

The synthesis is a post-pass inside `generate`, not a separate command. The pipeline remains:

```
extract → classify → generate
                       ├── per-comment articles (intermediate, written to staging)
                       └── topic synthesis (final KB output)
```

### Pattern 1: Two-Pass Synthesis (Plan then Write)

**What:** First LLM call identifies topic groupings from all per-comment articles. Second set of calls writes one topic page per group.

**Why two passes:** Sending all articles to one prompt blows the token budget. The planning pass returns a lightweight JSON mapping, then each write call only receives the articles relevant to that topic.

**Adapted for github-pr-kb:**

```python
# Pass 1: Planning call - group articles into topics
TOPIC_PLAN_SYSTEM = (
    "You are organizing a knowledge base extracted from GitHub PR discussions. "
    "Group related articles into topics. Each topic should be a single concept "
    "that multiple PR discussions contribute to. "
    "Return JSON only."
)

TOPIC_PLAN_USER = """
These are knowledge base articles extracted from PR comments in a repository.
Group them into topics - each topic is one concept that multiple articles discuss.

Articles:
{article_summaries}

Return JSON:
{{
  "topics": [
    {{
      "slug": "filesystem-safe-slug",
      "title": "Human Readable Title",
      "category": "architecture_decision",
      "article_keys": ["comment_id_1", "comment_id_2"]
    }}
  ]
}}

Rules:
- Prefer fewer, broader topics over many narrow ones
- An article with no related articles becomes a single-source topic (that's fine)
- Do NOT create overlapping topics - each article belongs to exactly one topic
- Use the most common category among grouped articles as the topic category
"""

# Pass 2: Synthesis call per topic (only articles in that group)
TOPIC_SYNTHESIS_SYSTEM = (
    "You are a technical writer synthesizing a knowledge base topic page "
    "from multiple GitHub PR comments about the same concept. "
    "Preserve ALL information from every source - never discard details. "
    "When sources span different time periods, note the chronological evolution "
    "(e.g., 'Initially X was used (PR #12), later replaced by Y (PR #45)'). "
    "Use standard markdown links [text](path) for cross-references to related topics. "
    "Output ONLY the article body using the provided section headings."
)
```

### Pattern 2: Topic Pages Replace Per-Comment Articles

**What:** The final KB directory contains topic pages, not per-comment articles. Per-comment articles are intermediate artifacts used during synthesis but not exposed to the user.

**Why:** One KB, not two. The user doesn't want to navigate both `architecture_decision/use-postgres.md` AND `topics/database-selection.md`. They want one good article about database selection.

**Structure:**

```
kb/
├── .manifest.json          # Extended: comment_id → topic_slug mapping
├── INDEX.md                # Regenerated from topic pages
├── architecture_decision/
│   ├── database-selection.md       # Synthesized from 3 PR comments
│   └── api-versioning-strategy.md  # Synthesized from 2 PR comments
├── gotcha/
│   ├── connection-pool-exhaustion.md  # Single-source topic (1 PR comment)
│   └── timezone-handling.md           # Synthesized from 4 PR comments
└── code_pattern/
    └── retry-with-backoff.md          # Synthesized from 2 PR comments
```

### Pattern 3: Chronological Awareness Instead of Contradiction Detection

**What:** Instead of a standalone contradiction linter, the synthesis prompt is aware that PR comments span time. When a newer comment supersedes an older one, the topic page notes the evolution rather than flagging a "contradiction."

**Why this fits better than a linter:** In a PR-based KB, "contradictions" are usually just decisions evolving over time. "Use Redis for caching" (PR #12, Jan 2025) followed by "We migrated caching to Postgres" (PR #45, Mar 2025) isn't a contradiction - it's history. The synthesis prompt handles this naturally.

**Prompt fragment:**
```
When source comments span different dates and appear to conflict,
present this as chronological evolution, not a contradiction:
"Initially [approach A] was adopted (PR #12, Jan 2025). This was later
revised to [approach B] (PR #45, Mar 2025) because [reason if stated]."
```

### Pattern 4: Standard Markdown Links for Cross-References

**What:** The synthesis prompt generates standard markdown links `[related topic](../category/slug.md)` instead of Obsidian-style `[[wikilinks]]`.

**Why:** Our KB is consumed on GitHub, in editors, and locally. `[[wikilinks]]` don't render on GitHub. Standard markdown links work everywhere.

### Pattern 5: Extended Manifest (No Separate .topics.json)

**What:** The existing `.manifest.json` is extended to track topic synthesis state alongside the existing comment_id → path mapping.

```json
{
  "comments": {
    "12345": "architecture_decision/database-selection.md",
    "12346": "architecture_decision/database-selection.md",
    "12347": "gotcha/connection-pool-exhaustion.md"
  },
  "topics": {
    "architecture_decision/database-selection": {
      "sources": ["12345", "12346"],
      "content_hash": "abc123...",
      "last_synthesized": "2026-04-16T12:00:00Z"
    }
  }
}
```

**Migration:** On first synthesis run, the old flat `{comment_id: path}` manifest is migrated to the `comments` sub-key. The `topics` key is added. Existing KBs are regenerated transparently.

### Anti-Patterns to Avoid

- **Separate `synthesize` CLI command:** Adds UX friction. The user's mental model is `extract → classify → generate`. Synthesis is how generation works now, not a separate step.
- **`[[wikilinks]]`:** Don't render on GitHub. Use standard markdown links.
- **Two parallel KBs (per-comment + topic pages):** Confusing. Topic pages replace per-comment articles.
- **Standalone contradiction linter:** Over-engineered for PR-based knowledge. Chronological awareness in the synthesis prompt handles it.
- **Sending all articles to one prompt:** Token explosion. Use the two-pass pattern.
- **difflib for topic grouping:** String similarity can't detect that "PostgreSQL pool exhaustion" and "database connection pooling" are the same topic. The LLM planning pass handles semantic grouping.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | `_parse_article_metadata()` in generator.py | `python-frontmatter` library | Current implementation fails on quoted strings with colons; python-frontmatter handles edge cases |
| Topic similarity grouping | BM25 / embedding vectors / TF-IDF / difflib | LLM planning pass | LLM understands semantic equivalence; string similarity cannot |
| Markdown link extraction | Complex regex for all link formats | `re.compile(r"\[([^\]]+)\]\(([^)]+)\)")` | Simple, covers our use case |

---

## Common Pitfalls

### Pitfall 1: Information Loss During Synthesis

**What goes wrong:** Claude rewrites a topic page and drops nuance from earlier sources.

**Why it happens:** LLMs tend toward "clean" summaries that omit edge cases.

**How to avoid:** System prompt must say "Preserve ALL information from every source - never discard details." Store topic page content in git - the diff is the safety net. Verified across all examined implementations as the #1 required prompt constraint.

**Warning signs:** Topic page shrinks after adding a new source article.

### Pitfall 2: Topic Fragmentation (Too Many Topics)

**What goes wrong:** Every article becomes its own topic instead of merging with related articles.

**Why it happens:** Planning prompt doesn't emphasize "prefer fewer, broader topics."

**How to avoid:** Planning prompt must say "Prefer fewer, broader topics over many narrow ones" and "Do NOT create overlapping topics." A single-source topic is acceptable (some comments are genuinely unique), but the default behavior should be merging.

**Warning signs:** Topic count equals article count.

### Pitfall 3: Cost Explosion on Re-Runs

**What goes wrong:** Every `generate` re-synthesizes all topics, even unchanged ones.

**How to avoid:** Content-hash the source articles for each topic. If the hash matches the stored hash in the manifest, skip the synthesis call. Only call Claude for topics that have new source articles since last synthesis.

### Pitfall 4: Breaking Backward Compatibility

**What goes wrong:** Existing KBs with per-comment articles break when the user upgrades.

**How to avoid:** When `generate` runs and finds an old-format `.manifest.json` (flat dict, no `topics` key), treat it as a first-run: regenerate all topic pages from the classified files. The old per-comment articles are overwritten by topic pages. The `--regenerate` flag already handles full rebuilds.

### Pitfall 5: Single-Source Topics Lose Context

**What goes wrong:** A topic with only one source article is worse than the original per-comment article because synthesis strips the PR-specific context.

**How to avoid:** For single-source topics, the synthesis prompt should preserve more of the original context (PR title, author, date prominently displayed). The topic page should read like an enriched version of the per-comment article, not a watered-down summary.

---

## Code Examples

### Topic Frontmatter (python-frontmatter)

```python
import frontmatter

def read_topic_page(path: Path) -> tuple[dict, str]:
    """Returns (metadata_dict, body_str)."""
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content

def write_topic_page(path: Path, metadata: dict, body: str) -> None:
    post = frontmatter.Post(body, **metadata)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
```

### Topic Plan Pydantic Model

```python
from pydantic import BaseModel

class TopicGroup(BaseModel):
    slug: str
    title: str
    category: str
    article_keys: list[str]  # comment_ids

class TopicPlan(BaseModel):
    topics: list[TopicGroup]
```

### Incremental Synthesis Guard

```python
import hashlib

def _sources_hash(article_bodies: list[str]) -> str:
    combined = "\n---\n".join(sorted(article_bodies))
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

def _needs_synthesis(self, topic_slug: str, current_hash: str) -> bool:
    topic_meta = self._manifest.get("topics", {}).get(topic_slug, {})
    return topic_meta.get("content_hash") != current_hash
```

### Standard Markdown Cross-Reference

```python
CROSS_REF_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

def extract_cross_references(body: str) -> list[tuple[str, str]]:
    """Return list of (display_text, relative_path) from markdown links."""
    return CROSS_REF_RE.findall(body)
```

---

## Adaptation Notes: What We Borrowed vs. What We Changed

| LLM Wiki Pattern | Our Adaptation | Why |
|------------------|----------------|-----|
| Separate `compile`/`synthesize` command | Integrated into `generate` | Users have a 3-step pipeline; adding a 4th step is friction |
| `[[wikilinks]]` for cross-refs | Standard markdown links `[text](path)` | GitHub doesn't render wikilinks |
| `topics/` subdirectory alongside per-comment articles | Topic pages replace per-comment articles in category dirs | One KB, not two parallel outputs |
| `.topics.json` manifest | Extended `.manifest.json` with `topics` sub-key | One manifest, not two |
| Standalone contradiction lint command | Chronological awareness in synthesis prompt | PR comments evolve over time; that's history, not contradictions |
| "Preserve and extend, never discard" | Kept as-is | Universal and directly applicable |
| Two-pass LLM (plan then write) | Kept as-is | Correct architecture regardless of domain |
| Content hashing for skip-unchanged | Kept as-is | Cost-awareness is already a project constraint |

---

## Open Questions (RESOLVED)

1. **Should `generate` always synthesize, or should synthesis be opt-in?**
   - RESOLVED (D-05): Always synthesize by default. `--no-synthesize` flag provides escape hatch for per-comment-only output.

2. **What model for the planning pass vs. synthesis pass?**
   - RESOLVED (D-07): Reuse existing `ANTHROPIC_GENERATE_MODEL` for both passes. No new environment variable. The research recommendation to add `ANTHROPIC_SYNTHESIZE_MODEL` was superseded by locked decision D-07.

3. **Manifest migration strategy?**
   - RESOLVED (D-09): First synthesis run auto-detects old flat manifest and migrates. Existing dict wrapped under `"comments"`, empty `"topics"` key added.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/ -x -q --no-cov` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/` |

### Phase Requirements -> Test Map

| ID | Behavior | Test Type |
|----|----------|-----------|
| SYNTH-01 | Related articles grouped into topic pages by `generate` | unit |
| SYNTH-02 | Topic pages contain standard markdown cross-reference links | unit |
| SYNTH-03 | Chronological evolution noted when source comments span time | unit |
| SYNTH-04 | Unchanged topics skipped on re-run (content hash check) | unit |
| SYNTH-05 | Old-format manifest migrated transparently on first run | unit |
| SYNTH-06 | Single-source topics produce enriched articles (not watered-down) | unit |
| SYNTH-07 | `--no-synthesize` flag produces per-comment articles only | smoke |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: github.com/kytmanov/obsidian-llm-wiki-local] - Two-pass architecture, content hashing, incremental synthesis
- [VERIFIED: github.com/VectifyAI/OpenKB] - Topic planning prompt with "do not create overlapping topics" constraint
- [CITED: levelup.gitconnected.com article] - "Preserve and extend, never discard" synthesis constraint
- [VERIFIED: github.com/ussumant/llm-wiki-compiler] - Topic-per-concept structure, incremental updates

### Secondary (MEDIUM confidence)
- [VERIFIED: github.com/nvk/llm-wiki] - Structural lint separate from LLM contradiction detection (informed our decision to skip standalone linter)
- [VERIFIED: gist.github.com/rohitg00] - Conceptual tier model (no code implementation)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - python-frontmatter is the only new dependency
- Architecture patterns: HIGH - two-pass pattern verified across multiple implementations, adapted for our constraints
- Adaptation decisions: HIGH - each deviation from generic LLM Wiki pattern has a clear reason tied to github-pr-kb's specific use case

**Research date:** 2026-04-16
**Valid until:** 2026-05-16
