# Stack Research

**Domain:** GitHub PR Knowledge Extraction Tools
**Researched:** 2026-02-13
**Confidence:** HIGH

## Executive Summary

This document outlines the standard 2025-2026 stack for building Python-based GitHub PR extraction and analysis tools. The recommended approach uses PyGithub for API access, Anthropic's Claude API for AI classification, Click for CLI, and the modern Python packaging ecosystem (pyproject.toml, pytest). This is a mature, well-supported stack with production-grade libraries and excellent community support.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10+ | Core language | Industry standard for data processing and AI integration; excellent package ecosystem; native async support in recent versions |
| PyGithub | 2.8.1+ | GitHub API access | Most mature Python GitHub wrapper; well-maintained; type-annotated; covers GitHub REST API v3 completely; 10K+ GitHub stars |
| Anthropic SDK | 0.75.0+ | Claude API integration | Native Anthropic support; structured outputs for classification; competitive pricing (70% less than GPT-4); long context windows (200K tokens); predictable outputs for enterprise use |
| Click | 8.3.1+ | CLI framework | Decorator-based syntax; excellent help generation; built-in testing utilities (CliRunner); active maintenance; alternative to argparse with better DX |
| Markdown | 3.10.2+ | Markdown generation | Production-stable; Python implementation of Gruber spec; excellent extension support; works with structured output from LLMs |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.x+ | Data validation & structured outputs | For parsing LLM classification outputs; ensuring type safety for PR comments and classifications |
| requests | 2.31.0+ | HTTP client (fallback) | Simple synchronous requests; used by PyGithub internally; sufficient for MVP (replace with httpx for async later) |
| pytest | 9.0.2+ | Testing framework | Standard Python testing; excellent fixture system; rich plugin ecosystem (pytest-cov, pytest-asyncio) |
| python-dotenv | 1.x+ | Environment variable management | Load GitHub tokens and API keys safely; standard practice for credential management |
| ruff | latest | Code linting and formatting | Rust-based; 50-100x faster than black/isort; industry standard in 2025-2026 Python projects |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package manager | 80x faster than venv; replaces pip/poetry/pyenv; recommended for development and GitHub Actions; skip if team prefers Poetry |
| pyproject.toml | Project configuration | Modern standard (PEP 518/621); single source of truth for dependencies, scripts, and metadata |
| GitHub Actions | CI/CD pipeline | Free for public repos; setup-python action is standard; enable caching for dependencies |

---

## Detailed Recommendations by Component

### GitHub API Access

**Recommendation: PyGithub (2.8.1+) over alternatives**

**Why:**
- Most mature wrapper (maintained for 10+ years)
- Full type annotations for IDE support and mypy checking
- Directly exposes GitHub REST API v3 objects (Repository, PullRequest, Issue, Comment)
- Handles authentication seamlessly (token-based or GitHub App)
- Low barrier to entry for simple PR comment extraction

**Alternatives Not Recommended:**
- `github3.py` — Slightly less mature, smaller community; no clear advantage over PyGithub
- `github` (official REST client) — Too low-level; requires manual pagination and response handling
- GraphQL (`gql` library) — **Better for complex queries** but overkill for MVP; stick with REST unless you need advanced filtering across multiple PRs

**Code Pattern for MVP:**
```python
from github import Github

gh = Github(token=os.getenv("GITHUB_TOKEN"))
repo = gh.get_repo("owner/repo")

for pr in repo.get_pulls(state="closed"):
    for comment in pr.get_comments():
        # Extract and process comment
        process_comment(comment.body)
```

### AI Classification

**Recommendation: Anthropic Claude API (direct, not via LangChain)**

**Why:**
- **Price-performance:** Claude 3.5 Sonnet costs 70% less than GPT-4o while matching performance on classification tasks
- **Consistency:** Constitutional AI training produces more predictable, safer outputs for enterprise use
- **Long context:** 200K token window allows processing full PR thread history in one request
- **Structured outputs:** Native support for structured responses (via tool_use) enables reliable JSON parsing
- **Native SDKs:** Official Python SDK (anthropic 0.75.0+) is production-ready

**When to Use Alternatives:**
- OpenAI GPT-4o: If you need the broadest creativity (unlikely for classification) or team is GPT-only
- LangChain wrapper: Only if building a larger agent system; adds complexity for simple classification

**Why NOT LangChain for MVP:**
- Adds abstraction layer without significant benefit
- Makes it harder to use Claude's specific features (tool_use, extended thinking)
- Slower to iterate when you need to debug prompts

**Code Pattern:**
```python
from anthropic import Anthropic

client = Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": f"Classify this PR comment: {comment_text}\n\nCategories: architecture, gotcha, pattern, domain_knowledge"
        }
    ]
)
classification = message.content[0].text
```

**CRITICAL:** Use structured outputs (tool_use) for production:
```python
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=[{
        "name": "classify_comment",
        "description": "Classify PR comment",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["architecture", "gotcha", "pattern", "domain_knowledge"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "summary": {"type": "string"}
            },
            "required": ["category", "confidence"]
        }
    }],
    messages=[{"role": "user", "content": f"Classify: {comment_text}"}]
)
```

### CLI Framework

**Recommendation: Click (8.3.1+) over argparse**

**Why:**
- **Developer experience:** Decorator-based syntax is cleaner than argparse boilerplate
- **Help generation:** Auto-formats beautiful help pages with proper grouping
- **Testing:** CliRunner makes it trivial to write CLI tests
- **Subcommands:** Built-in support for command hierarchies (git-like interfaces)

**When argparse is Better:**
- Projects with zero external dependencies (argparse is stdlib)
- Very simple single-command tools

**Code Pattern:**
```python
import click

@click.group()
def cli():
    """PR Knowledge Base Generator"""
    pass

@cli.command()
@click.option('--repo', required=True, help='GitHub repo (owner/name)')
@click.option('--token', envvar='GITHUB_TOKEN', required=True)
def extract(repo, token):
    """Extract PR comments from repository"""
    # Implementation
    click.echo("Extraction complete")

if __name__ == '__main__':
    cli()
```

### Markdown Generation

**Recommendation: Markdown library (3.10.2+) + f-strings or Jinja2**

**Why:**
- **For parsing:** Markdown 3.10.2 is production-stable; handles extensions for custom syntax
- **For generation:** Raw f-strings suffice for structured markdown output in MVP
- **Alternative:** SnakeMD if you need programmatic markdown building (avoid for simple generation)

**Pattern for Knowledge Base Generation:**
```python
from markdown import Markdown

# Generation pattern (f-strings recommended for MVP):
md_content = f"""# {title}

## {section}

- **Author:** {author}
- **PR:** {pr_link}

{comment_body}
"""

# Write to file
with open(f"kb/{topic}/{slug}.md", "w") as f:
    f.write(md_content)
```

**When to add Markdown parsing:**
Only if you need to extend or validate generated markdown. Standard library file operations + string manipulation suffice for MVP.

---

## Installation

### For Development

```bash
# Using uv (recommended 2025+ approach)
uv venv
source .venv/bin/activate  # Unix/Linux
# or
.venv\Scripts\activate  # Windows

uv pip install -e .

# Or using traditional pip + virtualenv
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Dependencies (pyproject.toml)

```toml
[project]
name = "github-pr-kb"
version = "0.1.0"
description = "Extract and organize PR knowledge from GitHub"
requires-python = ">=3.10"

dependencies = [
    "pygithub>=2.8.1",
    "anthropic>=0.75.0",
    "click>=8.3.1",
    "markdown>=3.10.2",
    "pydantic>=2.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=5.0.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
    "black>=24.1.0",
]

[tool.uv]
python-version = "3.10"

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not Alternative | When Alt Makes Sense |
|-------------|-------------|---------------------|---------------------|
| PyGithub | github3.py | Smaller ecosystem; PyGithub is more mature | If team already uses github3.py elsewhere |
| PyGithub | GitHub GraphQL API (gql) | Overkill for MVP; REST is simpler for PR comments | If querying 10K+ PRs with complex filtering needs GraphQL pagination efficiency |
| Anthropic Claude | OpenAI GPT-4o | Higher cost (30% more); no clear quality advantage for classification | If org standardized on OpenAI; GPT-4o broader but not better for this task |
| Click | argparse | Requires stdlib only; more boilerplate; less DX | If absolutely no external dependencies allowed |
| Direct Claude API | LangChain | Adds abstraction layer; slower iteration on prompts | If building agent system that chains multiple tools |

---

## What NOT to Use

| Technology | Why Avoid | Use This Instead |
|------------|-----------|------------------|
| **Praw** (Reddit API wrapper) | Wrong domain; PR comments ≠ Reddit | PyGithub for GitHub |
| **Requests-only HTTP** | PyGithub already handles GitHub auth/pagination | PyGithub builds on top of requests |
| **Django/FastAPI** | MVP is CLI tool + GitHub Action, not web service | Add framework only if building dashboard later |
| **SQLAlchemy** | Markdown files are sufficient for MVP; no relational queries | Add database only for 1000+ PRs across repos |
| **Celery/RQ** | Single-repo extraction is synchronous; no job queues needed | Add only if scaling to 100+ repos with concurrency |
| **OpenAI Function Calling (legacy)** | Deprecated in favor of tool_use | Use Claude's tool_use or function_calling in OpenAI |
| **Poetry + uv together** | Creates confusion; pick one for dependency management | Choose: uv (faster) or poetry (more opinionated) |

---

## Version Compatibility Matrix

| Component | Minimum | Recommended | Notes |
|-----------|---------|------------|-------|
| Python | 3.10 | 3.11+ | 3.10 is minimum; 3.11+ for better performance |
| PyGithub | 2.8.0 | 2.8.1+ | 2.8.x stable; watch for 3.0.0 breaking changes |
| Anthropic SDK | 0.75.0 | 0.75.0+ | Stable API; new models added in patch releases |
| Click | 8.3.0 | 8.3.1+ | 8.x is stable; 9.0.0 unlikely soon |
| Markdown | 3.10.0 | 3.10.2+ | 3.10+ requires Python 3.10+; extensions included |
| pytest | 8.0+ | 9.0.2+ | 8.0+ has async improvements; 9.0.2 is latest |

**Python 3.10 and 3.11 compatibility:** All recommended libraries support both; no conflicts.

---

## GitHub Actions Stack

For CI/CD and production "GitHub Action" deployment:

```yaml
# .github/workflows/main.yml
name: Build and Deploy

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: "requirements.txt"

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Lint
        run: ruff check .

      - name: Test
        run: pytest

      - name: Run PR extraction
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m github_pr_kb extract --repo ${{ github.repository }}
```

**Key points:**
- Use `setup-python` v5+ for better caching
- Pin Python version explicitly (avoid default drift)
- Cache pip dependencies to avoid reinstalling every run
- Store secrets (GITHUB_TOKEN via Actions, ANTHROPIC_API_KEY manually) as repository secrets

---

## Confidence Levels

| Area | Confidence | Rationale |
|------|------------|-----------|
| **GitHub API** | HIGH | PyGithub is the de facto standard; 2.8.1 is current as of Feb 2026; extensive real-world usage |
| **LLM Integration** | HIGH | Anthropic SDK verified current (0.75.0+); Claude 3.5 Sonnet is industry standard for cost-effective classification |
| **CLI Framework** | HIGH | Click 8.3.1 confirmed current; no breaking changes expected soon; active maintenance |
| **Markdown generation** | HIGH | Markdown 3.10.2 verified current (Feb 2026); stable for 5+ years |
| **Testing (pytest)** | HIGH | pytest 9.0.2 verified current; industry standard with 1300+ plugins |
| **Package management** | MEDIUM | uv is fast-rising but Poetry still widely used; both valid; uv has edge for speed (2025-2026 trend) |

---

## Known Limitations & Mitigations

| Limitation | Impact | Mitigation |
|------------|--------|-----------|
| **GitHub API rate limits** | 5000 req/hr per token | Implement request caching; batch queries; consider GraphQL for future scaling |
| **Claude context window (200K)** | Can process ~50K words per request | Sufficient for typical PR threads; split large conversations if needed |
| **Markdown lacks metadata** | Difficult to query KB after generation | Add YAML frontmatter for tags/dates; consider SQLite index for 1000+ files |
| **Single-repo MVP scope** | Hard to extend to multi-repo | Design extraction logic as reusable module from start |

---

## Roadmap Implications

**Phase 1 (MVP - Feb/Mar 2026):**
- Use all "Recommended" versions as-is
- No need for GraphQL, async optimization, or database
- Focus on core extraction + classification + markdown generation

**Phase 2 (Multi-repo - Q2 2026):**
- Consider async version using httpx (replace requests)
- May need SQLite index for KB search
- Still use same LLM/CLI/markdown stack

**Phase 3 (Dashboard - Q3+ 2026):**
- Add FastAPI or Django for web UI
- Consider moving classifications to PostgreSQL
- Keep CLI tool as primary interface

---

## Sources

**Official Documentation:**
- [PyGithub Documentation](https://pygithub.readthedocs.io/) — Latest API reference
- [Anthropic Claude API Docs](https://platform.claude.com/docs/en/api) — Native SDK and models
- [Click Documentation](https://click.palletsprojects.com/) — CLI framework guide
- [Python Packaging Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — Modern Python standards
- [GitHub Actions setup-python](https://github.com/actions/setup-python) — CI/CD reference

**Comparative Research (2025-2026):**
- [Python HTTP Clients Comparison](https://www.speakeasy.com/blog/python-http-clients-requests-vs-httpx-vs-aiohttp) — Requests vs HTTPX vs AIOHTTP
- [Python Package Managers Comparison](https://medium.com/@hitorunajp/poetry-vs-uv-which-python-package-manager-should-you-use-in-2025-4212cb5e0a14) — Poetry vs uv trade-offs
- [Python CLI Frameworks Guide](https://inventivehq.com/blog/python-cli-tools-guide) — Click vs Typer vs argparse
- [Claude vs GPT-4 Detailed Comparison (2025)](https://collabnix.com/claude-api-vs-openai-api-2025-complete-developer-comparison-with-code-examples/) — Performance and cost analysis
- [GitHub REST vs GraphQL API](https://docs.github.com/en/rest/about-the-rest-api/comparing-githubs-rest-api-and-graphql-api) — Official GitHub comparison
- [PR Analysis with ML/NLP](https://www.atlassian.com/blog/atlassian-engineering/ml-classifier-improving-quality) — Code review comment classification patterns

**Verification Sources:**
- PyPI: PyGithub (2.8.1), Click (8.3.1), Markdown (3.10.2), pytest (9.0.2), Anthropic SDK (0.75.0+)
- GitHub Releases: anthropic-sdk-python, pygithub/pygithub, pallets/click

---

*Stack research for: GitHub PR Knowledge Extraction Tools*
*Researched: 2026-02-13*
*Verified with current sources and official documentation*
