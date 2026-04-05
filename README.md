# github-pr-kb
A tool for extracting GitHub PR comments into a knowledgebase for AI agents (and humans)

## The vision:

You know this feeling. You are a software engineer working on a product with the rest of your team of talented software engineers. Each time any of you create a PR on GitHub for one of your repositories of your product, you get comments on it from your peers, fix issues, and merge.

Once the PR get merged, all you see in the "regular" git worktree and history are the commits and commits messages. The PR comments went to waste, with all the organizational and product wisdom they contained.

This CLI tool allows you to analyze all the PRs (that got merged) in a GitHub repository that have 1 or more comments on them, take the interesting comments there, and pass them to LLM for analysis and building/updating the knowledgebase accordingly.

## Options: 
- Selection between processing the X most recent PRs and processing all PRs starting from a specific date.
- Configure specific people that their opinions will matter more than others.
- Configure specific people/agents to ignore.

## Tech Stack:
- Python
- OpenRouter SDK
- Chroma vector DB
- GitHub API
- TOON (Token-Oriented Object Notation) for passing the data to the LLM

## Development

```bash
uv sync --all-groups          # install dependencies including dev tools
uv run pre-commit install     # activate the git pre-commit hook (one-time setup)
```

The pre-commit hook runs `ruff` on staged files before each commit, auto-fixing what it can. If fixes are applied, the commit is blocked so you can review and re-stage them.

To run linting manually across the whole codebase:
```bash
uv run pre-commit run --all-files
```
