import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _set_dummy_github_token():
    """Ensure GITHUB_TOKEN exists so config.settings imports cleanly in tests."""
    os.environ.setdefault("GITHUB_TOKEN", "ghp_test000000000000000000000000000fake")
