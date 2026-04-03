# Project Instructions

## Running Tests

Always run tests with the venv Python directly — never `uv run pytest`:

```bash
.venv/Scripts/python.exe -m pytest tests/
```

`uv run pytest` resolves to the system miniconda pytest on this machine, which runs under the wrong interpreter and fails to import the package.
