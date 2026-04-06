"""Integration tests for PRClassifier — requires real Anthropic API access.

Run with:
    RUN_INTEGRATION_TESTS=1 .venv/Scripts/python.exe -m pytest tests/test_classifier_integration.py -v -m integration

Skipped automatically unless both conditions hold:
  - RUN_INTEGRATION_TESTS=1 env var is set
  - ANTHROPIC_API_KEY is a real key (not the unit-test dummy value)
"""

import os

import pytest
from anthropic import Anthropic

from github_pr_kb.classifier import DEFAULT_MODEL

_DUMMY_KEY = "sk-ant-test000000000000000000000000000fake"
_SKIP_REASON = "Integration tests require RUN_INTEGRATION_TESTS=1 and a real ANTHROPIC_API_KEY"


def _integration_tests_enabled() -> bool:
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        return False
    return os.environ.get("ANTHROPIC_API_KEY", _DUMMY_KEY) != _DUMMY_KEY


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _integration_tests_enabled(), reason=_SKIP_REASON),
]


@pytest.fixture(scope="module")
def anthropic_client() -> Anthropic:
    """Create a real Anthropic client for integration tests."""
    return Anthropic(max_retries=2)


def test_default_model_exists_on_api(anthropic_client: Anthropic) -> None:
    """DEFAULT_MODEL must resolve to a valid model on the Anthropic API.

    This catches model deprecation/renaming before it reaches users.
    If this test fails, update DEFAULT_MODEL in classifier.py.
    """
    model_info = anthropic_client.models.retrieve(model_id=DEFAULT_MODEL)
    assert model_info.id == DEFAULT_MODEL
