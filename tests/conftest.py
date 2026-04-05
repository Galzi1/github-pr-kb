import os

import pytest

# Set env vars before collection so config.settings (module-level) doesn't raise.
# Must be done at module level here, not in a fixture, because extractor.py
# instantiates settings = Settings() at import time.
os.environ.setdefault("GITHUB_TOKEN", "ghp_test000000000000000000000000000fake")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test000000000000000000000000000fake")


@pytest.fixture(autouse=True, scope="session")
def _set_dummy_env_tokens():
    """Ensure GITHUB_TOKEN and ANTHROPIC_API_KEY exist so config.settings imports cleanly in tests."""
    os.environ.setdefault("GITHUB_TOKEN", "ghp_test000000000000000000000000000fake")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test000000000000000000000000000fake")
