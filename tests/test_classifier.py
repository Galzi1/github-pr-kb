"""Tests for PRClassifier — scaffolded in Phase 4 Plan 01 (TDD RED).

These tests will fail until Plan 02 implements PRClassifier in classifier.py.
PRClassifier is imported inside each test function body to avoid ImportError at
collection time (classifier.PRClassifier does not exist yet).
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import anthropic
import pytest

from github_pr_kb.classifier import (
    DEFAULT_COMMENT_CHUNK_SIZE,
    DEFAULT_MODEL,
    DEFAULT_REVIEW_CONFIDENCE_THRESHOLD,
    LEGACY_FAILURE_SUMMARY,
)
from github_pr_kb.models import (
    ClassifiedFile,
    CommentRecord,
    PRFile,
    PRRecord,
)


def make_mock_message(json_text: str) -> anthropic.types.Message:
    """Build a minimal Anthropic Message object for mocking SDK responses."""
    return anthropic.types.Message(
        id="msg_test",
        content=[anthropic.types.TextBlock(text=json_text, type="text")],
        model=DEFAULT_MODEL,
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=anthropic.types.Usage(input_tokens=120, output_tokens=40),
    )


@pytest.fixture
def cache_dir_with_pr(tmp_path):
    """Create a cache dir with a single pr-1.json containing one comment."""
    pr_file = PRFile(
        pr=PRRecord(
            number=1,
            title="Test PR",
            state="open",
            url="https://github.com/test/repo/pull/1",
        ),
        comments=[
            CommentRecord(
                comment_id=101,
                comment_type="review",
                author="testuser",
                body="Always use retry logic when calling external APIs to handle transient failures.",
                created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
                url="https://github.com/test/repo/pull/1#comment-101",
            ),
        ],
        extracted_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    cache_file = tmp_path / "pr-1.json"
    cache_file.write_text(json.dumps(pr_file.model_dump(mode="json"), indent=2))
    return tmp_path


def test_classify_returns_valid_category(cache_dir_with_pr):
    """Classify a comment and assert the returned category is one of the 5 valid values."""
    from github_pr_kb.classifier import PRClassifier

    valid_categories = {"architecture_decision", "code_pattern", "gotcha", "domain_knowledge", "other"}
    response_json = json.dumps({
        "category": "code_pattern",
        "confidence": 0.9,
        "summary": "Use retry logic for external API calls to handle transient failures.",
    })
    mock_message = make_mock_message(response_json)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier.classify_pr(1)

    assert isinstance(result, ClassifiedFile)
    assert len(result.classifications) == 1
    classified = result.classifications[0]
    assert classified.category in valid_categories


def test_needs_review_flag_low_confidence(cache_dir_with_pr):
    """When confidence falls below the review threshold, needs_review must be True."""
    from github_pr_kb.classifier import PRClassifier

    response_json = json.dumps({
        "category": "other",
        "confidence": 0.6,
        "summary": "Unclear comment.",
    })
    mock_message = make_mock_message(response_json)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier.classify_pr(1)

    assert result.classifications[0].needs_review is True


def test_needs_review_flag_high_confidence(cache_dir_with_pr):
    """When confidence meets the review threshold, needs_review must be False."""
    from github_pr_kb.classifier import PRClassifier

    response_json = json.dumps({
        "category": "architecture_decision",
        "confidence": 0.85,
        "summary": "Architectural pattern for external service calls.",
    })
    mock_message = make_mock_message(response_json)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier.classify_pr(1)

    assert result.classifications[0].needs_review is False


def test_cache_hit_no_api_call(cache_dir_with_pr):
    """Classifying the same PR twice should only call the API once (cache hit on second run)."""
    from github_pr_kb.classifier import PRClassifier

    response_json = json.dumps({
        "category": "gotcha",
        "confidence": 0.8,
        "summary": "Use retry logic.",
    })
    mock_message = make_mock_message(response_json)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        classifier.classify_pr(1)
        # Second call — same comment body hash should hit classification-index.json
        classifier.classify_pr(1)

    assert mock_client.messages.create.call_count == 1


def test_classified_comment_fields(cache_dir_with_pr):
    """ClassifiedComment must expose all required fields with correct types."""
    from github_pr_kb.classifier import PRClassifier

    response_json = json.dumps({
        "category": "domain_knowledge",
        "confidence": 0.92,
        "summary": "Retry pattern for transient failures.",
    })
    mock_message = make_mock_message(response_json)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier.classify_pr(1)

    classified = result.classifications[0]
    assert isinstance(classified.comment_id, int)
    assert isinstance(classified.category, str)
    assert isinstance(classified.confidence, float)
    assert isinstance(classified.summary, str)
    assert isinstance(classified.classified_at, datetime)
    assert isinstance(classified.needs_review, bool)


def test_body_hash_deterministic():
    """The same comment body must always produce the same SHA-256 hash."""
    from github_pr_kb.classifier import body_hash

    body = "Always use retry logic when calling external APIs."
    assert body_hash(body) == body_hash(body)


def test_body_hash_different_bodies():
    """Different comment bodies must produce different SHA-256 hashes."""
    from github_pr_kb.classifier import body_hash

    hash_a = body_hash("Use retry logic for external APIs.")
    hash_b = body_hash("Avoid global state in modules.")
    assert hash_a != hash_b


def test_parse_failure_returns_none(cache_dir_with_pr):
    from github_pr_kb.classifier import PRClassifier, body_hash

    mock_message = make_mock_message("NOT VALID JSON {{{")

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        comment = PRFile.model_validate_json(
            (cache_dir_with_pr / "pr-1.json").read_text(encoding="utf-8")
        ).comments[0]

        result = classifier._classify_comment(comment)

    assert result is None
    assert classifier._failed_count == 1
    assert body_hash(comment.body) not in classifier._index


def test_markdown_fenced_json_is_parsed(cache_dir_with_pr):
    from github_pr_kb.classifier import PRClassifier

    response_text = """```json
    {"category": "gotcha", "confidence": 0.88, "summary": "Validate discount rate bounds."}
    ```"""
    mock_message = make_mock_message(response_text)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier.classify_pr(1)

    assert len(result.classifications) == 1
    assert result.classifications[0].category == "gotcha"
    assert classifier._failed_count == 0


def test_prose_wrapped_json_is_parsed(cache_dir_with_pr):
    from github_pr_kb.classifier import PRClassifier

    response_text = (
        'Here is the classification result:\n'
        '{"category": "domain_knowledge", "confidence": 0.91, '
        '"summary": "Discount order is a business rule."}\n'
        "Thanks."
    )
    mock_message = make_mock_message(response_text)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier.classify_pr(1)

    assert len(result.classifications) == 1
    assert result.classifications[0].category == "domain_knowledge"
    assert classifier._failed_count == 0


def test_load_index_filters_failed(tmp_path):
    from github_pr_kb.classifier import PRClassifier

    index_path = tmp_path / "classification-index.json"
    index_path.write_text(
        json.dumps(
            {
                "hash1": {
                    "category": "gotcha",
                    "confidence": 0.9,
                    "summary": "real summary",
                    "classified_at": "2026-01-01T00:00:00+00:00",
                },
                "hash2": {
                    "category": "other",
                    "confidence": 0.0,
                    "summary": LEGACY_FAILURE_SUMMARY,
                    "classified_at": "2026-01-01T00:00:00+00:00",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with patch("github_pr_kb.classifier.Anthropic"):
        classifier = PRClassifier(cache_dir=tmp_path, api_key="sk-ant-fake")

    assert "hash1" in classifier._index
    assert "hash2" not in classifier._index


def test_long_comment_body_is_sent_in_full(tmp_path):
    from github_pr_kb.classifier import PRClassifier

    tail_marker = "TAIL-MARKER"
    long_body = "START-" + ("a" * DEFAULT_COMMENT_CHUNK_SIZE) + tail_marker
    pr_file = PRFile(
        pr=PRRecord(
            number=1,
            title="Test PR",
            state="open",
            url="https://github.com/test/repo/pull/1",
        ),
        comments=[
            CommentRecord(
                comment_id=101,
                comment_type="review",
                author="testuser",
                body=long_body,
                created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
                url="https://github.com/test/repo/pull/1#comment-101",
            ),
        ],
        extracted_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    (tmp_path / "pr-1.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    response_json = json.dumps({
        "category": "code_pattern",
        "confidence": 0.9,
        "summary": "Use the complete comment body.",
    })
    mock_message = make_mock_message(response_json)

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=tmp_path, api_key="sk-ant-fake")
        classifier.classify_pr(1)

    api_body = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert tail_marker in api_body
    assert api_body.count("<comment_chunk") == 2


def test_load_index_keeps_valid(tmp_path):
    from github_pr_kb.classifier import PRClassifier

    index_path = tmp_path / "classification-index.json"
    index_path.write_text(
        json.dumps(
            {
                "hash1": {
                    "category": "gotcha",
                    "confidence": 0.9,
                    "summary": "real summary 1",
                    "classified_at": "2026-01-01T00:00:00+00:00",
                },
                "hash2": {
                    "category": "code_pattern",
                    "confidence": 0.8,
                    "summary": "real summary 2",
                    "classified_at": "2026-01-01T00:00:00+00:00",
                },
                "hash3": {
                    "category": "other",
                    "confidence": DEFAULT_REVIEW_CONFIDENCE_THRESHOLD,
                    "summary": "real summary 3",
                    "classified_at": "2026-01-01T00:00:00+00:00",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with patch("github_pr_kb.classifier.Anthropic"):
        classifier = PRClassifier(cache_dir=tmp_path, api_key="sk-ant-fake")

    assert set(classifier._index) == {"hash1", "hash2", "hash3"}


def test_classifier_summary_counts_include_cached_review(cache_dir_with_pr):
    from github_pr_kb.classifier import PRClassifier, body_hash

    comment = PRFile.model_validate_json(
        (cache_dir_with_pr / "pr-1.json").read_text(encoding="utf-8")
    ).comments[0]
    (cache_dir_with_pr / "classification-index.json").write_text(
        json.dumps(
            {
                body_hash(comment.body): {
                    "category": "gotcha",
                    "confidence": 0.6,
                    "summary": "cached low confidence item",
                    "classified_at": "2026-01-01T00:00:00+00:00",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client

        classifier = PRClassifier(cache_dir=cache_dir_with_pr, api_key="sk-ant-fake")
        result = classifier._classify_comment(comment)

    assert result is not None
    assert result.needs_review is True
    assert classifier.get_summary_counts() == {
        "new": 0,
        "cached": 1,
        "need_review": 1,
        "failed": 0,
    }
    mock_client.messages.create.assert_not_called()
