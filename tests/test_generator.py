"""Tests for KBGenerator -- TDD scaffolds for Phase 5 Plan 01.

Task 1 tests: slugify, _yaml_str, config kb_output_dir.
Task 2 tests: KBGenerator class, article generation, manifest dedup.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from github_pr_kb.models import (
    ClassifiedComment,
    ClassifiedFile,
    CommentRecord,
    PRFile,
    PRRecord,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_classified_file(tmp_path: Path) -> Path:
    """Create classified-pr-1.json and pr-1.json in tmp_path for testing."""
    pr = PRRecord(
        number=1,
        title="Test PR",
        state="open",
        url="https://github.com/test/repo/pull/1",
    )
    comment = CommentRecord(
        comment_id=101,
        comment_type="review",
        author="alice",
        body="Always copy context before modifying...",
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/1#comment-101",
        diff_hunk="@@ -12,3 +12,3 @@\n-    ctx.user = user\n+    ctx = ctx.copy(update={\"user\": user})",
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=datetime(2026, 1, 15, tzinfo=timezone.utc))
    (tmp_path / "pr-1.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    classified_comment = ClassifiedComment(
        comment_id=101,
        category="gotcha",
        confidence=0.85,
        summary="Avoid circular imports in middleware",
        classified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        needs_review=False,
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[classified_comment],
        classified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-1.json").write_text(
        json.dumps(classified_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def make_two_classified_files(tmp_path: Path) -> Path:
    """Create two classified-pr-*.json files for incremental merge tests."""
    pr1 = PRRecord(
        number=1,
        title="Test PR 1",
        state="open",
        url="https://github.com/test/repo/pull/1",
    )
    comment1 = CommentRecord(
        comment_id=101,
        comment_type="review",
        author="alice",
        body="Always copy context before modifying...",
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/1#comment-101",
        diff_hunk="@@ -12,3 +12,3 @@\n-ctx.user = user\n+ctx = ctx.copy()",
    )
    pr_file1 = PRFile(pr=pr1, comments=[comment1], extracted_at=datetime(2026, 1, 15, tzinfo=timezone.utc))
    (tmp_path / "pr-1.json").write_text(
        json.dumps(pr_file1.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    classified1 = ClassifiedFile(
        pr=pr1,
        classifications=[
            ClassifiedComment(
                comment_id=101,
                category="gotcha",
                confidence=0.85,
                summary="Avoid circular imports in middleware",
                classified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
                needs_review=False,
            )
        ],
        classified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-1.json").write_text(
        json.dumps(classified1.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    pr2 = PRRecord(
        number=2,
        title="Test PR 2",
        state="closed",
        url="https://github.com/test/repo/pull/2",
    )
    comment2 = CommentRecord(
        comment_id=202,
        comment_type="issue",
        author="bob",
        body="Use dependency injection to avoid tight coupling.",
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/2#comment-202",
    )
    pr_file2 = PRFile(pr=pr2, comments=[comment2], extracted_at=datetime(2026, 2, 1, tzinfo=timezone.utc))
    (tmp_path / "pr-2.json").write_text(
        json.dumps(pr_file2.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    classified2 = ClassifiedFile(
        pr=pr2,
        classifications=[
            ClassifiedComment(
                comment_id=202,
                category="code_pattern",
                confidence=0.90,
                summary="Use dependency injection to avoid tight coupling",
                classified_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                needs_review=False,
            )
        ],
        classified_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-2.json").write_text(
        json.dumps(classified2.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def make_issue_comment_classified(tmp_path: Path) -> Path:
    """Create classified-pr-1.json with an issue comment (no diff_hunk)."""
    pr = PRRecord(
        number=1,
        title="Issue Comment PR",
        state="open",
        url="https://github.com/test/repo/pull/1",
    )
    comment = CommentRecord(
        comment_id=101,
        comment_type="issue",
        author="carol",
        body="Consider using a factory pattern here.",
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/1#comment-101",
        diff_hunk=None,
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=datetime(2026, 1, 15, tzinfo=timezone.utc))
    (tmp_path / "pr-1.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[
            ClassifiedComment(
                comment_id=101,
                category="code_pattern",
                confidence=0.80,
                summary="Use factory pattern for object creation",
                classified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
                needs_review=False,
            )
        ],
        classified_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-1.json").write_text(
        json.dumps(classified_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def make_malformed_classified(tmp_path: Path) -> Path:
    """Create an invalid JSON file classified-pr-99.json for error handling tests."""
    (tmp_path / "classified-pr-99.json").write_text("this is not valid json", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Task 1: slugify tests
# ---------------------------------------------------------------------------


def test_slugify_basic() -> None:
    from github_pr_kb.generator import slugify

    assert slugify("Avoid circular imports") == "avoid-circular-imports"


def test_slugify_unicode() -> None:
    from github_pr_kb.generator import slugify

    result = slugify("Caf\u00e9 au lait")
    assert result.isascii()
    assert result  # not empty


def test_slugify_max_length() -> None:
    from github_pr_kb.generator import slugify

    long_input = "This is a very long summary that exceeds the sixty character limit for slugs in the KB"
    result = slugify(long_input)
    assert len(result) <= 60


def test_slugify_special_chars() -> None:
    from github_pr_kb.generator import slugify

    result = slugify("C++ patterns: best & worst!")
    assert result == "c-patterns-best-worst"


def test_slugify_empty() -> None:
    from github_pr_kb.generator import slugify

    assert slugify("") == "untitled"


def test_slugify_collision_suffix(tmp_path: Path) -> None:
    """When a target file exists, the slug resolver appends -2 suffix."""
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    gotcha_dir = kb_dir / "gotcha"
    gotcha_dir.mkdir()
    # Pre-create a file that would collide with slug "avoid-circular-imports"
    (gotcha_dir / "avoid-circular-imports.md").write_text("existing article", encoding="utf-8")

    gen = KBGenerator(cache_dir=tmp_path, kb_dir=kb_dir)
    # _resolve_slug takes the summary text and checks for collisions
    slug = gen._resolve_slug("Avoid circular imports", "gotcha")
    assert slug == "avoid-circular-imports-2"


# ---------------------------------------------------------------------------
# Task 1: _yaml_str test
# ---------------------------------------------------------------------------


def test_yaml_str_newline() -> None:
    from github_pr_kb.generator import _yaml_str

    result = _yaml_str("Fix bug\nin middleware")
    assert "\n" not in result
    assert "Fix bug" in result
    assert "in middleware" in result


# ---------------------------------------------------------------------------
# Task 1: config test
# ---------------------------------------------------------------------------


def test_config_kb_output_dir_default() -> None:
    from github_pr_kb.config import Settings

    settings = Settings(
        github_token="ghp_test000000000000000000000000000fake",
        anthropic_api_key=None,
    )
    assert settings.kb_output_dir == "kb"


# ---------------------------------------------------------------------------
# Task 2: KBGenerator tests
# ---------------------------------------------------------------------------


def test_generate_creates_category_subdirs(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    assert (kb_dir / "gotcha").is_dir()


def test_article_written_to_category_subdir(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    expected = kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md"
    assert expected.exists()


def test_article_frontmatter_fields(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    article_path = kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md"
    content = article_path.read_text(encoding="utf-8")
    required_fields = [
        "pr_url:", "pr_title:", "comment_url:", "author:", "date:",
        "category:", "confidence:", "needs_review:", "comment_id:",
    ]
    for field in required_fields:
        assert field in content, f"Missing frontmatter field: {field}"


def test_diff_hunk_in_review_comment(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    article_path = kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md"
    content = article_path.read_text(encoding="utf-8")
    assert "```" in content
    assert "ctx.user = user" in content


def test_no_diff_hunk_for_issue_comment(make_issue_comment_classified: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_issue_comment_classified, kb_dir=kb_dir)
    gen.generate_all()
    # Find the generated article
    articles = list((kb_dir / "code_pattern").glob("*.md"))
    assert len(articles) == 1
    content = articles[0].read_text(encoding="utf-8")
    assert "```" not in content


def test_article_heading_is_summary(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    article_path = kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md"
    content = article_path.read_text(encoding="utf-8")
    assert "# Avoid circular imports in middleware" in content


def test_article_body_contains_comment(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    article_path = kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md"
    content = article_path.read_text(encoding="utf-8")
    assert "Always copy context before modifying" in content


def test_incremental_no_duplicate(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen1 = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    result1 = gen1.generate_all()

    gen2 = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    result2 = gen2.generate_all()

    assert result1.written == 1
    assert result2.written == 0
    assert result2.skipped == 1


def test_incremental_adds_new_articles(make_two_classified_files: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    cache_dir = make_two_classified_files

    # First run with only classified-pr-1.json (temporarily rename the second)
    classified2 = cache_dir / "classified-pr-2.json"
    classified2_backup = cache_dir / "classified-pr-2.json.bak"
    classified2.rename(classified2_backup)

    gen1 = KBGenerator(cache_dir=cache_dir, kb_dir=kb_dir)
    result1 = gen1.generate_all()
    assert result1.written == 1

    # Restore classified-pr-2.json and run again
    classified2_backup.rename(classified2)
    gen2 = KBGenerator(cache_dir=cache_dir, kb_dir=kb_dir)
    result2 = gen2.generate_all()
    assert result2.written == 1
    assert result2.skipped == 1


def test_manifest_written(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    manifest_path = kb_dir / ".manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "101" in manifest
    assert "gotcha" in manifest["101"]


def test_generate_result_summary(make_classified_file: Path, tmp_path: Path) -> None:
    from github_pr_kb.generator import GenerateResult, KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    result = gen.generate_all()
    assert isinstance(result, GenerateResult)
    assert result.written == 1
    assert result.skipped == 0
    assert result.failed == []


def test_malformed_classified_file(make_malformed_classified: Path, tmp_path: Path) -> None:
    """Generator logs warning and continues when a classified JSON is invalid."""
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_malformed_classified, kb_dir=kb_dir)
    result = gen.generate_all()
    assert len(result.failed) == 1
    assert result.failed[0]["file"] == "classified-pr-99.json"


def test_needs_review_in_frontmatter(tmp_path: Path) -> None:
    """Article with confidence < 0.75 has needs_review: true in frontmatter."""
    from github_pr_kb.generator import KBGenerator

    pr = PRRecord(
        number=3,
        title="Low Confidence PR",
        state="open",
        url="https://github.com/test/repo/pull/3",
    )
    comment = CommentRecord(
        comment_id=301,
        comment_type="issue",
        author="dave",
        body="This might be a gotcha.",
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/3#comment-301",
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=datetime(2026, 3, 1, tzinfo=timezone.utc))
    (tmp_path / "pr-3.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[
            ClassifiedComment(
                comment_id=301,
                category="gotcha",
                confidence=0.60,
                summary="Possible gotcha with low confidence",
                classified_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                needs_review=True,
            )
        ],
        classified_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-3.json").write_text(
        json.dumps(classified_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=tmp_path, kb_dir=kb_dir)
    gen.generate_all()

    articles = list((kb_dir / "gotcha").glob("*.md"))
    assert len(articles) == 1
    content = articles[0].read_text(encoding="utf-8")
    assert "needs_review: true" in content


def test_other_category_included(tmp_path: Path) -> None:
    """Articles with category 'other' are written to kb_dir/other/."""
    from github_pr_kb.generator import KBGenerator

    pr = PRRecord(
        number=4,
        title="Other Category PR",
        state="open",
        url="https://github.com/test/repo/pull/4",
    )
    comment = CommentRecord(
        comment_id=401,
        comment_type="issue",
        author="eve",
        body="Minor style comment.",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/4#comment-401",
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=datetime(2026, 4, 1, tzinfo=timezone.utc))
    (tmp_path / "pr-4.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[
            ClassifiedComment(
                comment_id=401,
                category="other",
                confidence=0.55,
                summary="Minor style comment about formatting",
                classified_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                needs_review=True,
            )
        ],
        classified_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-4.json").write_text(
        json.dumps(classified_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=tmp_path, kb_dir=kb_dir)
    gen.generate_all()

    assert (kb_dir / "other").is_dir()
    articles = list((kb_dir / "other").glob("*.md"))
    assert len(articles) == 1


# ---------------------------------------------------------------------------
# Task 1 (Plan 02): Index generation tests
# ---------------------------------------------------------------------------


def test_index_file_created(make_classified_file: Path, tmp_path: Path) -> None:
    """After generate_all(), kb_dir/INDEX.md must exist (D-11)."""
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    assert (kb_dir / "INDEX.md").exists()


def test_index_grouped_by_category(make_classified_file: Path, tmp_path: Path) -> None:
    """INDEX.md contains '## Gotcha (1)' heading for a single gotcha article (D-12)."""
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()
    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    assert "## Gotcha (1)" in content


def test_index_review_marker(tmp_path: Path) -> None:
    """An article with needs_review=True has '[review]' on its index entry line (D-13)."""
    from github_pr_kb.generator import KBGenerator

    pr = PRRecord(
        number=5,
        title="Low Confidence Review PR",
        state="open",
        url="https://github.com/test/repo/pull/5",
    )
    comment = CommentRecord(
        comment_id=501,
        comment_type="issue",
        author="frank",
        body="This might be a gotcha worth reviewing.",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        url="https://github.com/test/repo/pull/5#comment-501",
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=datetime(2026, 4, 1, tzinfo=timezone.utc))
    (tmp_path / "pr-5.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[
            ClassifiedComment(
                comment_id=501,
                category="gotcha",
                confidence=0.60,
                summary="Low confidence gotcha needs human review",
                classified_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                needs_review=True,
            )
        ],
        classified_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    (tmp_path / "classified-pr-5.json").write_text(
        json.dumps(classified_file.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=tmp_path, kb_dir=kb_dir)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    # The entry line for this article must contain [review]
    lines_with_review = [line for line in content.splitlines() if "[review]" in line]
    assert len(lines_with_review) >= 1


def test_index_regenerated_on_rerun(make_classified_file: Path, tmp_path: Path) -> None:
    """Calling generate_all() twice produces identical INDEX.md content (D-14)."""
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"

    gen1 = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen1.generate_all()
    content1 = (kb_dir / "INDEX.md").read_text(encoding="utf-8")

    gen2 = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen2.generate_all()
    content2 = (kb_dir / "INDEX.md").read_text(encoding="utf-8")

    assert content1 == content2


def test_index_multiple_categories(make_two_classified_files: Path, tmp_path: Path) -> None:
    """INDEX.md has two ## headings when articles span two categories."""
    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_two_classified_files, kb_dir=kb_dir)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    assert "## Gotcha (1)" in content
    assert "## Code Pattern (1)" in content


def test_index_entry_has_summary_and_link(make_classified_file: Path, tmp_path: Path) -> None:
    """Each index entry is a markdown link of the form '- [summary](category/slug.md)'."""
    import re as _re

    from github_pr_kb.generator import KBGenerator

    kb_dir = tmp_path / "kb"
    gen = KBGenerator(cache_dir=make_classified_file, kb_dir=kb_dir)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    # Match lines like: - [some text](gotcha/some-slug.md)
    link_pattern = _re.compile(r"^- \[.+\]\(.+/.+\.md\)", _re.MULTILINE)
    matches = link_pattern.findall(content)
    assert len(matches) >= 1


def test_index_empty_kb(tmp_path: Path) -> None:
    """When no articles exist, INDEX.md is produced with title but no ## category headings (R3 mitigation)."""
    from github_pr_kb.generator import KBGenerator

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    kb_dir = tmp_path / "kb"

    gen = KBGenerator(cache_dir=cache_dir, kb_dir=kb_dir)
    gen.generate_all()

    index_path = kb_dir / "INDEX.md"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")
    assert "# Knowledge Base Index" in content
    # No category headings when KB is empty
    assert "## " not in content
