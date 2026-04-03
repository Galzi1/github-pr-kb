"""Tests for GitHub PR extractor — uses mocked PyGithub objects."""
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from github_pr_kb.extractor import SKIP_BOT_LOGINS, GitHubExtractor, is_noise
from github_pr_kb.models import CommentRecord, PRFile, PRRecord


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def make_mock_pr(number=42, state="open", updated_at=None, title="Test PR", body="PR description"):
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.body = body
    pr.state = state
    pr.html_url = f"https://github.com/owner/repo/pull/{number}"
    pr.updated_at = updated_at or datetime(2024, 1, 15, tzinfo=timezone.utc)
    pr.get_review_comments.return_value = []
    pr.get_issue_comments.return_value = []
    return pr


def make_mock_review_comment(comment_id=1001, login="alice", body="This is a substantive review comment"):
    c = MagicMock()
    c.id = comment_id
    c.user = MagicMock()
    c.user.login = login
    c.body = body
    c.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    c.html_url = f"https://github.com/owner/repo/pull/42#discussion_r{comment_id}"
    c.path = "src/foo.py"
    c.diff_hunk = "@@ -1,3 +1,4 @@\n context\n+new line"
    c.reactions = {"+1": 2, "heart": 0, "total_count": 2}
    return c


def make_mock_issue_comment(comment_id=2001, login="bob", body="This is a thread comment"):
    c = MagicMock()
    c.id = comment_id
    c.user = MagicMock()
    c.user.login = login
    c.body = body
    c.created_at = datetime(2024, 1, 16, tzinfo=timezone.utc)
    c.html_url = f"https://github.com/owner/repo/pull/42#issuecomment-{comment_id}"
    c.reactions = {"+1": 0, "heart": 0, "total_count": 0}
    return c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_extract_pr_comments(tmp_path):
    """Mock repo with 1 PR having 2 review + 1 issue comment. Extract produces PRFile with 3 comments."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, login="alice", body="First substantive review comment here"),
        make_mock_review_comment(comment_id=1002, login="carol", body="Second substantive review comment here"),
    ]
    pr.get_issue_comments.return_value = [
        make_mock_issue_comment(comment_id=2001, login="bob", body="This is a thread comment"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        paths = extractor.extract()

    assert len(paths) == 1
    cache_file = cache_dir / "pr-42.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    pr_file = PRFile.model_validate(data)
    assert pr_file.pr.number == 42
    assert len(pr_file.comments) == 3


def test_noise_filter_skips_dependabot(tmp_path):
    """Comment from 'dependabot[bot]' is filtered out."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=10)
    pr.get_issue_comments.return_value = [
        make_mock_issue_comment(comment_id=3001, login="dependabot[bot]", body="Bumps requests from 2.28 to 2.31"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-10.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 0


def test_noise_filter_skips_emoji_only(tmp_path):
    """Comment body consisting of only emoji or single word is filtered out."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=11)
    pr.get_issue_comments.return_value = [
        make_mock_issue_comment(comment_id=4001, login="alice", body="👍"),
        make_mock_issue_comment(comment_id=4002, login="bob", body="LGTM"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-11.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 0


def test_review_bot_kept(tmp_path):
    """Comment from 'github-copilot[bot]' with substantive multi-word body is KEPT."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=12)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(
            comment_id=5001,
            login="github-copilot[bot]",
            body="Consider extracting this logic into a separate method for better testability",
        ),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-12.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 1
    assert pr_file.comments[0].author == "github-copilot[bot]"


def test_state_filter(tmp_path):
    """get_pulls called with state='closed' when state filter is 'closed'."""
    cache_dir = tmp_path / "cache"

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = []
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract(state="closed")

    mock_repo.get_pulls.assert_called_once_with(state="closed", sort="updated", direction="desc")


def test_date_early_stop(tmp_path):
    """PR with updated_at before since boundary causes iteration to stop."""
    cache_dir = tmp_path / "cache"
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)

    # PR 1 is after since boundary (should be processed)
    pr1 = make_mock_pr(number=20, updated_at=datetime(2024, 7, 1, tzinfo=timezone.utc))
    # PR 2 is before since boundary (should trigger early stop)
    pr2 = make_mock_pr(number=21, updated_at=datetime(2024, 5, 1, tzinfo=timezone.utc))
    # PR 3 would be processed if no early stop
    pr3 = make_mock_pr(number=22, updated_at=datetime(2024, 4, 1, tzinfo=timezone.utc))

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr1, pr2, pr3]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract(since=since)

    # pr1 written, pr2 triggers break (may or may not be written depending on impl)
    # pr3 must NOT be written
    assert not (cache_dir / "pr-22.json").exists()


def test_date_filter_uses_updated_at(tmp_path):
    """Verifies filtering uses pr.updated_at, not pr.created_at."""
    cache_dir = tmp_path / "cache"
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)

    pr = make_mock_pr(number=30, updated_at=datetime(2024, 7, 1, tzinfo=timezone.utc))
    # Set created_at to before since — if code uses created_at, this PR would be filtered
    pr.created_at = datetime(2024, 5, 1, tzinfo=timezone.utc)

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract(since=since)

    # PR should be present because updated_at is after since
    assert (cache_dir / "pr-30.json").exists()


def test_cache_write(tmp_path):
    """After extraction, .github-pr-kb/cache/pr-42.json exists and contains valid JSON."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        paths = extractor.extract()

    cache_file = cache_dir / "pr-42.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    pr_file = PRFile.model_validate(data)
    assert pr_file.pr.number == 42
    assert len(paths) == 1
    assert paths[0] == cache_file


def test_deleted_user_handled(tmp_path):
    """Comment with user=None produces author='[deleted]'."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=50)

    deleted_comment = make_mock_issue_comment(
        comment_id=9001, login="someone", body="A substantive comment about the implementation"
    )
    deleted_comment.user = None  # simulate deleted user

    pr.get_issue_comments.return_value = [deleted_comment]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-50.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 1
    assert pr_file.comments[0].author == "[deleted]"


def test_pr_no_body(tmp_path):
    """PR with body=None extracts without error, PRRecord.body is None."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=60, body=None)

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-60.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert pr_file.pr.body is None


def test_upper_date_bound(tmp_path):
    """PR with updated_at after until boundary is skipped (continue, not break)."""
    cache_dir = tmp_path / "cache"
    until = datetime(2024, 6, 1, tzinfo=timezone.utc)

    # PR 1 is after until (should be skipped but NOT stop iteration)
    pr1 = make_mock_pr(number=70, updated_at=datetime(2024, 7, 1, tzinfo=timezone.utc))
    # PR 2 is within range (should be processed)
    pr2 = make_mock_pr(number=71, updated_at=datetime(2024, 5, 15, tzinfo=timezone.utc))

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr1, pr2]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract(until=until)

    # pr1 skipped (after until)
    assert not (cache_dir / "pr-70.json").exists()
    # pr2 processed (within range)
    assert (cache_dir / "pr-71.json").exists()


def test_reactions_extracted(tmp_path):
    """Review comment with reactions stores non-zero counts only."""
    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=80)
    review_comment = make_mock_review_comment(comment_id=8001)
    review_comment.reactions = {"+1": 2, "heart": 1, "-1": 0, "laugh": 0, "total_count": 3}
    pr.get_review_comments.return_value = [review_comment]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-80.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 1
    reactions = pr_file.comments[0].reactions
    assert reactions.get("+1") == 2
    assert reactions.get("heart") == 1
    assert "-1" not in reactions
    assert "laugh" not in reactions
