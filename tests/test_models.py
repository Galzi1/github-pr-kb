"""Unit tests for PRRecord, CommentRecord, and PRFile pydantic models."""
import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from github_pr_kb.models import CommentRecord, PRFile, PRRecord

# ---------------------------------------------------------------------------
# PRRecord tests
# ---------------------------------------------------------------------------


def test_prrecord_accepts_valid_data():
    """PRRecord accepts valid data with all required fields."""
    pr = PRRecord(
        number=42,
        title="Test PR",
        body=None,
        state="open",
        url="https://github.com/owner/repo/pull/42",
    )
    assert pr.number == 42
    assert pr.title == "Test PR"
    assert pr.body is None
    assert pr.state == "open"
    assert pr.url == "https://github.com/owner/repo/pull/42"


def test_prrecord_rejects_missing_required_fields():
    """PRRecord rejects missing required fields (number, title, state, url)."""
    with pytest.raises(ValidationError):
        PRRecord(title="Test PR", state="open", url="https://github.com/owner/repo/pull/42")  # missing number

    with pytest.raises(ValidationError):
        PRRecord(number=1, state="open", url="https://github.com/owner/repo/pull/1")  # missing title

    with pytest.raises(ValidationError):
        PRRecord(number=1, title="Test PR", url="https://github.com/owner/repo/pull/1")  # missing state

    with pytest.raises(ValidationError):
        PRRecord(number=1, title="Test PR", state="open")  # missing url


def test_prrecord_body_is_optional():
    """PRRecord.body is Optional — None is allowed."""
    pr_with_none = PRRecord(number=1, title="PR", body=None, state="open", url="https://github.com/owner/repo/pull/1")
    assert pr_with_none.body is None

    pr_without_body = PRRecord(number=1, title="PR", state="open", url="https://github.com/owner/repo/pull/1")
    assert pr_without_body.body is None

    pr_with_body = PRRecord(number=1, title="PR", body="Description here", state="open", url="https://github.com/owner/repo/pull/1")
    assert pr_with_body.body == "Description here"


def test_prrecord_state_rejects_invalid_values():
    """PRRecord.state rejects values that are not 'open' or 'closed'."""
    with pytest.raises(ValidationError):
        PRRecord(number=1, title="PR", state="merged", url="https://github.com/owner/repo/pull/1")

    with pytest.raises(ValidationError):
        PRRecord(number=1, title="PR", state="all", url="https://github.com/owner/repo/pull/1")


# ---------------------------------------------------------------------------
# CommentRecord tests
# ---------------------------------------------------------------------------


def test_commentrecord_accepts_review_comment():
    """CommentRecord accepts a review comment with file_path and diff_hunk populated."""
    now = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    comment = CommentRecord(
        comment_id=101,
        comment_type="review",
        author="alice",
        body="This should use a context manager here.",
        created_at=now,
        url="https://github.com/owner/repo/pull/42#discussion_r101",
        file_path="src/foo.py",
        diff_hunk="@@ -10,5 +10,6 @@ def bar():",
        reactions={"thumbs_up": 2},
    )
    assert comment.comment_id == 101
    assert comment.comment_type == "review"
    assert comment.file_path == "src/foo.py"
    assert comment.diff_hunk == "@@ -10,5 +10,6 @@ def bar():"
    assert comment.reactions == {"thumbs_up": 2}


def test_commentrecord_accepts_issue_comment():
    """CommentRecord accepts an issue comment with file_path=None and diff_hunk=None."""
    now = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    comment = CommentRecord(
        comment_id=202,
        comment_type="issue",
        author="bob",
        body="Agreed, we should refactor this module.",
        created_at=now,
        url="https://github.com/owner/repo/pull/42#issuecomment-202",
        file_path=None,
        diff_hunk=None,
    )
    assert comment.comment_type == "issue"
    assert comment.file_path is None
    assert comment.diff_hunk is None


def test_commentrecord_reactions_default_empty():
    """CommentRecord.reactions defaults to empty dict when omitted."""
    now = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    comment = CommentRecord(
        comment_id=303,
        comment_type="issue",
        author="carol",
        body="LGTM",
        created_at=now,
        url="https://github.com/owner/repo/pull/42#issuecomment-303",
    )
    assert comment.reactions == {}


def test_commentrecord_reactions_stores_nonzero_counts():
    """CommentRecord.reactions stores only non-zero counts as a dict."""
    now = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    comment = CommentRecord(
        comment_id=404,
        comment_type="review",
        author="dave",
        body="We need to cache this call.",
        created_at=now,
        url="https://github.com/owner/repo/pull/42#discussion_r404",
        reactions={"thumbs_up": 3},
    )
    assert comment.reactions == {"thumbs_up": 3}


def test_commentrecord_comment_type_rejects_invalid():
    """CommentRecord.comment_type accepts 'review' and 'issue'; rejects invalid values."""
    now = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    base_kwargs = dict(
        comment_id=505,
        author="eve",
        body="Some comment",
        created_at=now,
        url="https://github.com/owner/repo/pull/42#issuecomment-505",
    )

    # Valid values must not raise
    CommentRecord(**base_kwargs, comment_type="review")
    CommentRecord(**base_kwargs, comment_type="issue")

    # Invalid values must raise ValidationError
    with pytest.raises(ValidationError):
        CommentRecord(**base_kwargs, comment_type="general")


# ---------------------------------------------------------------------------
# PRFile round-trip test
# ---------------------------------------------------------------------------


def test_prfile_roundtrip_through_json():
    """PRFile round-trip: model_dump(mode='json') -> json.dumps -> json.loads -> model_validate = original."""
    pr = PRRecord(
        number=99,
        title="Add caching layer",
        body="This PR adds Redis caching.",
        state="closed",
        url="https://github.com/owner/repo/pull/99",
    )
    now = datetime(2026, 2, 20, 8, 0, 0, tzinfo=timezone.utc)
    review_comment = CommentRecord(
        comment_id=1001,
        comment_type="review",
        author="frank",
        body="Consider using a TTL here.",
        created_at=now,
        url="https://github.com/owner/repo/pull/99#discussion_r1001",
        file_path="src/cache.py",
        diff_hunk="@@ -5,3 +5,4 @@ class Cache:",
        reactions={"thumbs_up": 1},
    )
    issue_comment = CommentRecord(
        comment_id=2002,
        comment_type="issue",
        author="grace",
        body="This approach looks good overall.",
        created_at=now,
        url="https://github.com/owner/repo/pull/99#issuecomment-2002",
    )
    extracted_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    pr_file = PRFile(pr=pr, comments=[review_comment, issue_comment], extracted_at=extracted_at)

    # Round-trip through JSON
    dumped = pr_file.model_dump(mode="json")
    json_str = json.dumps(dumped)
    loaded_dict = json.loads(json_str)
    restored = PRFile.model_validate(loaded_dict)

    assert restored.pr.number == pr_file.pr.number
    assert restored.pr.title == pr_file.pr.title
    assert restored.pr.state == pr_file.pr.state
    assert len(restored.comments) == 2
    assert restored.comments[0].comment_id == 1001
    assert restored.comments[1].comment_id == 2002
    assert restored.comments[0].reactions == {"thumbs_up": 1}
    assert restored.comments[1].reactions == {}


def test_prfile_extracted_at_serializes_as_iso8601():
    """PRFile.extracted_at serializes as ISO 8601 string in JSON mode."""
    pr = PRRecord(number=1, title="Test", state="open", url="https://github.com/owner/repo/pull/1")
    extracted_at = datetime(2026, 3, 15, 9, 30, 0, tzinfo=timezone.utc)
    pr_file = PRFile(pr=pr, comments=[], extracted_at=extracted_at)

    dumped = pr_file.model_dump(mode="json")
    # extracted_at must be a string in JSON mode
    assert isinstance(dumped["extracted_at"], str)
    # Must be parseable as a datetime
    parsed = datetime.fromisoformat(dumped["extracted_at"].replace("Z", "+00:00"))
    assert parsed.year == 2026
    assert parsed.month == 3
    assert parsed.day == 15
