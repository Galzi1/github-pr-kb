# Architecture Patterns

**Domain:** GitHub PR Knowledge Extraction Tools
**Researched:** 2026-02-13

## Recommended Architecture for MVP

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point (Click)                  │
│                   (github_pr_kb/cli.py)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐
   │  Extract  │  │ Classify   │  │  Generate  │
   │ (PyGithub)│  │  (Claude)  │  │ (Markdown) │
   └────┬──────┘  └─────┬──────┘  └─────┬──────┘
        │                │                │
   GitHub API      Anthropic API    Markdown Files
        │                │                │
        └────────────────┼────────────────┘
                         │
                  ┌──────▼──────┐
                  │  Local Cache │
                  │  (JSON/YAML) │
                  └──────────────┘

        Knowledge Base (Markdown)
        ├─ kb/architecture_decision/
        ├─ kb/code_pattern/
        ├─ kb/gotcha/
        ├─ kb/domain_knowledge/
        └─ kb/other/
```

### Component Boundaries

| Component | Responsibility | I/O | Communicates With | Notes |
|-----------|---------------|-----|-------------------|-------|
| **CLI Layer** (cli.py) | Command routing, argument validation, user feedback | Stdin/stdout, exit codes | All modules | Entry point; handles errors; provides help text |
| **Extractor** (extractor.py) | Fetch PR data from GitHub API | API requests | Classifier, Generator | Implements pagination; caches raw comments |
| **Classifier** (classifier.py) | Call Claude API for comment classification | API requests | Generator | Stateless; can be called independently; returns JSON |
| **Generator** (generator.py) | Build markdown files from classified data | File I/O | Cache layer | Responsible for directory structure; frontmatter formatting |
| **Cache Layer** (cache.py) | Local persistence of extracted/classified data | File I/O | Extractor, Classifier, Generator | JSON for raw data; enables incremental extraction |
| **Config** (config.py) | Load and validate environment/config | ENV vars, YAML | All modules | Read-only; set at startup |

### Proposed Directory Structure

```
github-pr-kb/
├── src/
│   └── github_pr_kb/
│       ├── __init__.py
│       ├── cli.py              # Click entry point
│       ├── extractor.py        # GitHub API interaction (PyGithub)
│       ├── classifier.py       # Claude API calls
│       ├── generator.py        # Markdown file generation
│       ├── cache.py            # Local persistence
│       ├── config.py           # Configuration management
│       └── types.py            # Pydantic models for type safety
├── tests/
│       ├── test_extractor.py
│       ├── test_classifier.py
│       ├── test_generator.py
│       └── fixtures/
│               └── sample_comments.json
├── kb/                         # Generated knowledge base (Output)
│       ├── architecture_decision/
│       ├── code_pattern/
│       ├── gotcha/
│       ├── domain_knowledge/
│       └── other/
├── .cache/                     # Local extraction cache (gitignored)
│       ├── comments.json
│       ├── classifications.json
│       └── metadata.json
├── pyproject.toml
├── README.md
└── .env.example               # Template for GITHUB_TOKEN, ANTHROPIC_API_KEY
```

## Patterns to Follow

### Pattern 1: Stateless Classification
Classification module takes comment text, returns classification. No side effects.

### Pattern 2: Cache-First Architecture
Check local cache before hitting external APIs. Cache invalidation via timestamps.

### Pattern 3: Type-Safe Data with Pydantic
Define models for GitHub comments, classifications, KB articles for type safety.

### Pattern 4: Dependency Injection for Configuration
Pass config to functions rather than reading env vars inside functions.

## Anti-Patterns to Avoid

- Monolithic single-file script
- Hardcoded credentials
- Unstructured AI responses without parsing
- Ignoring rate limits

## Scalability

| Concern | MVP | Phase 2 | Phase 3 |
|---------|-----|---------|---------|
| Extraction | Sync only | Consider async | Parallelized |
| Caching | JSON files | SQLite index | PostgreSQL |
| KB size | 100-300 files | 1K-5K files | Need search |
| Storage | ~10 MB | ~50-100 MB | ~500 MB+ |

## Sources

- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [Anthropic Tool Use](https://platform.claude.com/docs/build/tool-use)
- [Click Framework](https://click.palletsprojects.com/)
- [Python Packaging Guide](https://packaging.python.org/)

*Architecture patterns for: GitHub PR Knowledge Extraction Tools*
*Researched: 2026-02-13*
