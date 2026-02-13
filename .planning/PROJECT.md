# GitHub PR Knowledge Base Extractor

## What This Is

A tool that extracts valuable context from GitHub PR comments and organizes it into a markdown knowledge base. It captures architectural decisions, code patterns, gotchas, and domain knowledge that emerge during code review discussions, making this tribal knowledge discoverable and usable by both AI agents (like Claude Code) and human developers.

## Core Value

Preserve and make discoverable the architectural decisions, code patterns, gotchas, and domain knowledge that naturally emerge in PR discussions but typically get lost in closed PR threads.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Extract PR comments from a GitHub repository via API
- [ ] Classify comments into topics using AI (architecture decisions, code patterns, gotchas, domain knowledge)
- [ ] Generate markdown files organized by topic
- [ ] Create an index file that summarizes the content in each topic file
- [ ] CLI tool for manual extraction of specific PRs
- [ ] GitHub Action for automated extraction workflow
- [ ] Basic topic categorization that's good enough for MVP

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
*Last updated: 2026-02-13 after initialization*
