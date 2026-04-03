import os

import pytest

# Set GITHUB_TOKEN before collection so config.settings (module-level) doesn't raise.
# Must be done at module level here, not in a fixture, because extractor.py
# instantiates settings = Settings() at import time.
os.environ.setdefault("GITHUB_TOKEN", "ghp_test000000000000000000000000000fake")


@pytest.fixture(autouse=True, scope="session")
def _set_dummy_github_token():
    """Ensure GITHUB_TOKEN exists so config.settings imports cleanly in tests."""
    os.environ.setdefault("GITHUB_TOKEN", "ghp_test000000000000000000000000000fake")
