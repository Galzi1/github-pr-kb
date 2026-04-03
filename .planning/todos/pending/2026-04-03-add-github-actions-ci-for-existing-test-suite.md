---
created: 2026-04-03T21:23:05.798Z
title: Add GitHub Actions CI for existing test suite
area: testing
files:
  - tests/
  - pyproject.toml
  - .github/workflows/
---

## Problem

The project has a solid unit test suite (27 tests across config, models, and extractor) plus integration tests (6 tests gated by `RUN_INTEGRATION_TESTS=1`), but no CI pipeline runs them automatically on push or PR. Regressions can only be caught by running tests manually.

## Solution

Create a GitHub Actions workflow (`.github/workflows/ci.yml`) that:
- Triggers on push to any branch and on pull requests targeting `main`
- Sets up Python using the version from `pyproject.toml` (`requires-python = ">=3.11"`)
- Installs dependencies via `uv sync`
- Runs the unit test suite: `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_extractor_integration.py`
- Skips integration tests by default (they require `RUN_INTEGRATION_TESTS=1` + a real `GITHUB_TOKEN` secret)
- Optionally: run linting via `ruff check src/ tests/`
