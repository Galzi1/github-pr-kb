---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Ruff Lint Check After Python Changes

After finishing changes to ANY `*.py` files in `src/` or `tests/`, ALWAYS run:

```bash
uv run ruff check src/ tests/ --fix --exit-non-zero-on-fix
```

If ruff reports errors that `--fix` cannot auto-resolve, you MUST fix them manually BEFORE considering the task complete.
