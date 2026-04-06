# GitHub PR Knowledge Base Extractor

## What This Is

A tool that extracts valuable context from GitHub PR comments and organizes it into a markdown knowledge base. It captures architectural decisions, code patterns, gotchas, and domain knowledge that emerge during code review discussions, making this tribal knowledge discoverable and usable by both AI agents (like Claude Code) and human developers.

## Core Value

Preserve and make discoverable the architectural decisions, code patterns, gotchas, and domain knowledge that naturally emerge in PR discussions but typically get lost in closed PR threads.

## Current Milestone: v1.0 MVP

**Goal:** Build a working CLI tool that extracts PR comments from a GitHub repository, classifies them with Claude AI, and generates an organized markdown knowledge base.

**Target features:**
- GitHub PR comment extraction with rate-limit handling and local caching
- Claude-powered comment classification (architecture decisions, code patterns, gotchas, domain knowledge)
- Markdown KB generation with YAML frontmatter and index file
- CLI interface with extract / classify / generate commands
- GitHub Action for automated extraction

## Requirements

### Validated

- [x] Extract PR comments from a GitHub repository via API — Validated in Phase 02: GitHub Extraction Core
- [x] Authenticated access via PAT (GITHUB_TOKEN) — Validated in Phase 02: GitHub Extraction Core
- [x] Classify comments into topics using AI (architecture decisions, code patterns, gotchas, domain knowledge) — Validated in Phase 04: Claude Classifier
- [x] Generate markdown files organized by topic — Validated in Phase 05: KB Generator
- [x] Create an index file that summarizes the content in each topic file — Validated in Phase 05: KB Generator

### Active

- [ ] CLI tool for manual extraction of specific PRs
- [ ] GitHub Action for automated extraction workflow

### Out of Scope

- Multi-repository extraction in v1 — Single repo focus first
- Complex manual tagging UI — AI classification is sufficient for MVP
- Real-time extraction — Batch processing acceptable for v1
- Web interface — CLI and GitHub Action cover the use cases

## Context

**Problem:** Valuable tribal knowledge (why we made certain decisions, what patterns to follow, what to avoid) gets buried in PR comment threads. When PRs close, this context becomes hard to find. New team members and AI agents can't easily discover this institutional knowledge.

**Current state:** There's a `requirements.txt` file in the repository, suggesting Python tooling. No existing codebase for this specific tool.

**Target users:**
- AI agents (especially Claude Code) that need context about how this codebase works
- Developers onboarding to the project
- Anyone trying to understand past decisions

**Use case:** After running the extraction (manually via CLI or automatically via GitHub Action), the knowledge base lives as markdown files that can be read directly or referenced in AI agent contexts.

## Constraints

- **Tech stack**: Python — Good GitHub API libraries, easy scripting
- **Platform**: GitHub — Tool specifically for GitHub PRs
- **Output format**: Markdown — Human-readable and AI-agent-friendly
- **Scope**: Single repository at a time for MVP

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| AI-based topic classification | More flexible than keyword matching, less overhead than manual tagging | — Pending |
| Both CLI and GitHub Action | Manual for targeted extraction, automation for keeping KB current | — Pending |
| Python implementation | Strong GitHub API ecosystem, familiar for scripting tasks | — Pending |
| Single repo scope for v1 | Simpler to build and test, can expand later if needed | — Pending |

---
*Last updated: 2026-04-06 — Phase 05 complete: KB Generator implemented (KBGenerator class, per-category markdown articles with YAML frontmatter, manifest-based incremental dedup, INDEX.md generation with category grouping and [review] markers)*
