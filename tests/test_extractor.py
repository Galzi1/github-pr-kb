"""Tests for GitHub PR extractor — uses mocked PyGithub objects."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import RetryError

from github_pr_kb.extractor import GitHubExtractor, RateLimitExhaustedError
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


def test_naive_datetime_coerced_to_utc(tmp_path):
    """Naive since/until datetimes are coerced to UTC instead of crashing with TypeError."""
    cache_dir = tmp_path / "cache"
    since = datetime(2024, 6, 1)  # intentionally naive — no tzinfo
    pr = make_mock_pr(number=90, updated_at=datetime(2024, 7, 1, tzinfo=timezone.utc))

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        paths = extractor.extract(since=since)  # must not raise TypeError

    assert len(paths) == 1


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


# ---------------------------------------------------------------------------
# Resilience tests (Phase 03 — CORE-03, CORE-04, CORE-05, D-06)
# ---------------------------------------------------------------------------

def _make_pr_file_json(number: int, comment_ids: list[int]) -> str:
    """Build a PRFile JSON string with the given comment IDs for pre-populating cache."""
    comments = [
        CommentRecord(
            comment_id=cid,
            comment_type="review",
            author="alice",
            body="Substantive comment here",
            created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
            url=f"https://github.com/o/r/pull/{number}#discussion_r{cid}",
        )
        for cid in comment_ids
    ]
    pr_file = PRFile(
        pr=PRRecord(
            number=number,
            title="Test PR",
            body="desc",
            state="open",
            url=f"https://github.com/o/r/pull/{number}",
        ),
        comments=comments,
        extracted_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
    )
    return json.dumps(pr_file.model_dump(mode="json"), indent=2)


def test_rate_limit_exhaustion(tmp_path):
    """When iteration over pulls raises RetryError, RateLimitExhaustedError is raised with resume hint."""
    cache_dir = tmp_path / "cache"

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.side_effect = RetryError("rate limit")
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        with pytest.raises(RateLimitExhaustedError) as exc_info:
            extractor.extract()

    assert "Re-run the same command to resume" in str(exc_info.value)


def test_rate_limit_partial_flush(tmp_path):
    """Already-processed PRs are written to disk before RateLimitExhaustedError is raised."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    pr1 = make_mock_pr(number=1)
    pr1.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, body="Substantive comment about architecture"),
    ]
    pr2 = make_mock_pr(number=2)
    pr2.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1002, body="Another substantive review comment"),
    ]
    pr3 = make_mock_pr(number=3)
    pr3.get_review_comments.side_effect = RetryError("rate limit")

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr1, pr2, pr3]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        with pytest.raises(RateLimitExhaustedError):
            extractor.extract()

    assert (cache_dir / "pr-1.json").exists(), "PR 1 should be flushed before rate limit error"
    assert (cache_dir / "pr-2.json").exists(), "PR 2 should be flushed before rate limit error"


def test_outside_window_not_fetched(tmp_path):
    """PR outside date window keeps existing cache file byte-for-byte unchanged."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    original_content = _make_pr_file_json(99, [1001])
    (cache_dir / "pr-99.json").write_text(original_content, encoding="utf-8")

    # PR #99 updated_at is outside the window (before since)
    pr99 = make_mock_pr(number=99, updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc))

    since = datetime(2024, 1, 1, tzinfo=timezone.utc)

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr99]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract(since=since)

    actual_content = (cache_dir / "pr-99.json").read_text(encoding="utf-8")
    assert actual_content == original_content, "Cache file for out-of-window PR must not change"


def test_inside_window_comments_merged(tmp_path):
    """Re-run merges new comments into existing cache without duplicating existing ones."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    (cache_dir / "pr-42.json").write_text(_make_pr_file_json(42, [1001, 1002]), encoding="utf-8")

    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, body="Substantive comment about architecture"),
        make_mock_review_comment(comment_id=1002, body="Another substantive review comment"),
        make_mock_review_comment(comment_id=1003, body="A brand new comment with details"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-42.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 3, f"Expected 3 comments after merge, got {len(pr_file.comments)}"


def test_no_duplicate_comment_ids(tmp_path):
    """Re-run with same comments does not add duplicates."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    (cache_dir / "pr-42.json").write_text(_make_pr_file_json(42, [1001, 1002]), encoding="utf-8")

    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, body="Substantive comment about architecture"),
        make_mock_review_comment(comment_id=1002, body="Another substantive review comment"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-42.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 2, f"Expected 2 comments (no duplicates), got {len(pr_file.comments)}"


def test_merge_appends_new_only(tmp_path):
    """Merge appends only net-new comments by comment_id."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    (cache_dir / "pr-42.json").write_text(_make_pr_file_json(42, [1001]), encoding="utf-8")

    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, body="Substantive comment about architecture"),
        make_mock_review_comment(comment_id=2001, body="A new substantive comment about the design"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    data = json.loads((cache_dir / "pr-42.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 2
    comment_ids = {c.comment_id for c in pr_file.comments}
    assert comment_ids == {1001, 2001}


def test_atomic_write_no_partial_file(tmp_path):
    """After extraction, no .tmp files remain in cache directory."""
    import glob as glob_module

    cache_dir = tmp_path / "cache"
    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, body="Substantive comment about architecture"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()

    assert (cache_dir / "pr-42.json").exists()
    tmp_files = list(cache_dir.glob("*.tmp"))
    assert len(tmp_files) == 0, f"Found orphaned .tmp files: {tmp_files}"


def test_corrupt_cache_full_fetch(tmp_path):
    """Corrupt cache file is replaced with fresh data, not crashed on."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    (cache_dir / "pr-42.json").write_text("{corrupt", encoding="utf-8")

    pr = make_mock_pr(number=42)
    pr.get_review_comments.return_value = [
        make_mock_review_comment(comment_id=1001, body="Substantive comment about architecture"),
    ]

    with patch("github_pr_kb.extractor.Github") as MockGithub:
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        extractor = GitHubExtractor("owner/repo", cache_dir=cache_dir)
        extractor.extract()  # must not raise

    data = json.loads((cache_dir / "pr-42.json").read_text())
    pr_file = PRFile.model_validate(data)
    assert len(pr_file.comments) == 1
