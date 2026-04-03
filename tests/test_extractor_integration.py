"""Integration tests for GitHubExtractor — requires real GitHub API access.

Run with:
    RUN_INTEGRATION_TESTS=1 .venv/Scripts/python.exe -m pytest tests/test_extractor_integration.py -v -m integration

Skipped automatically unless both conditions hold:
  - RUN_INTEGRATION_TESTS=1 env var is set
  - GITHUB_TOKEN is a real PAT (not the unit-test dummy value)
"""
import json
import os

import pytest

from github_pr_kb.config import settings
from github_pr_kb.extractor import GitHubExtractor
from github_pr_kb.models import PRFile

_DUMMY_TOKEN = "ghp_test000000000000000000000000000fake"
_SKIP_REASON = "Integration tests require RUN_INTEGRATION_TESTS=1 and a real GITHUB_TOKEN"


def _integration_tests_enabled() -> bool:
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        return False
    return settings.github_token != _DUMMY_TOKEN


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _integration_tests_enabled(), reason=_SKIP_REASON),
]

# ---------------------------------------------------------------------------
# Known values from PR #2 (Galzi1/github-pr-kb#2 — "Phase 02: GitHub Extraction Core")
# ---------------------------------------------------------------------------
REPO = "Galzi1/github-pr-kb"
PR_NUMBER = 2
PR_TITLE = "Phase 02: GitHub Extraction Core"
PR_STATE = "closed"
PR_URL = "https://github.com/Galzi1/github-pr-kb/pull/2"
KNOWN_AUTHOR = "Galzi1"

KNOWN_REVIEW_COMMENT_IDS = {
    3034151684,  # "Missing type hinting for `raw_reactions`"
    3034154036,  # "This code repeats itself..."
    3034158911,  # "The code that processes each `pr` is very long..."
    3034166484,  # "I think it could be useful to encapsulate this logic..."
    3034175576,  # "I think that this line is too hard to read..."
    3034250523,  # "You are using `Any` too much for type hinting..."
}


# ---------------------------------------------------------------------------
# Shared fixture — fetches only PR #2, shared across all tests in this module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pr2_file(tmp_path_factory: pytest.TempPathFactory) -> PRFile:
    """Fetch PR #2 directly from the real API and return its PRFile."""
    cache_dir = tmp_path_factory.mktemp("integration_cache")
    extractor = GitHubExtractor(REPO, cache_dir=cache_dir)
    pr = extractor.repo.get_pull(PR_NUMBER)
    extractor._write_cache(pr, extractor._collect_comments(pr))

    cache_file = cache_dir / f"pr-{PR_NUMBER}.json"
    assert cache_file.exists(), f"Cache file for PR #{PR_NUMBER} not found"
    return PRFile.model_validate(json.loads(cache_file.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pr2_metadata(pr2_file: PRFile) -> None:
    """PR #2 has the correct number, title, state, and URL."""
    assert pr2_file.pr.number == PR_NUMBER
    assert pr2_file.pr.title == PR_TITLE
    assert pr2_file.pr.state == PR_STATE
    assert pr2_file.pr.url == PR_URL


def test_pr2_contains_known_author(pr2_file: PRFile) -> None:
    """PR #2 contains at least one comment authored by Galzi1."""
    authors = {c.author for c in pr2_file.comments}
    assert KNOWN_AUTHOR in authors


def test_pr2_all_comment_types_valid(pr2_file: PRFile) -> None:
    """Every comment has a comment_type of 'review' or 'issue'."""
    for comment in pr2_file.comments:
        assert comment.comment_type in ("review", "issue"), (
            f"Unexpected comment_type {comment.comment_type!r} for comment {comment.comment_id}"
        )


def test_pr2_reactions_are_dict_of_str_int(pr2_file: PRFile) -> None:
    """reactions on every comment is a dict mapping str keys to int values."""
    for comment in pr2_file.comments:
        assert isinstance(comment.reactions, dict), (
            f"comment {comment.comment_id}: reactions is {type(comment.reactions)}, expected dict"
        )
        for key, value in comment.reactions.items():
            assert isinstance(key, str)
            assert isinstance(value, int)


def test_pr2_no_automation_bot_comments(pr2_file: PRFile) -> None:
    """Dependabot and codecov bot comments are absent from the extracted results."""
    filtered_logins = {"dependabot[bot]", "dependabot", "codecov[bot]", "codecov"}
    authors = {c.author for c in pr2_file.comments}
    unexpected = authors & filtered_logins
    assert not unexpected, f"Bot accounts found in extracted comments: {unexpected}"


def test_pr2_known_review_comment_ids_present(pr2_file: PRFile) -> None:
    """All 6 known Galzi1 review comment IDs are present in the extraction output."""
    extracted_ids = {c.comment_id for c in pr2_file.comments}
    missing = KNOWN_REVIEW_COMMENT_IDS - extracted_ids
    assert not missing, f"Expected comment IDs not found: {missing}"
