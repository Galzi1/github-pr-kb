"""Tests for KBGenerator synthesis, indexing, and regenerate behavior."""

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest

from github_pr_kb.models import (
    ClassifiedComment,
    ClassifiedFile,
    CommentRecord,
    PRFile,
    PRRecord,
)


def _write_classified_pair(
    base_dir: Path,
    *,
    pr_number: int = 1,
    title: str = "Test PR",
    state: str = "open",
    comment_id: int = 101,
    comment_type: str = "review",
    author: str = "alice",
    comment_body: str = "Always copy context before modifying...",
    comment_url: str | None = None,
    diff_hunk: str | None = '@@ -12,3 +12,3 @@\n-    ctx.user = user\n+    ctx = ctx.copy(update={"user": user})',
    category: str = "gotcha",
    confidence: float = 0.85,
    summary: str = "Avoid circular imports in middleware",
    needs_review: bool = False,
) -> None:
    pr_url = f"https://github.com/test/repo/pull/{pr_number}"
    comment_url = comment_url or f"{pr_url}#comment-{comment_id}"
    created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)

    pr = PRRecord(number=pr_number, title=title, state=state, url=pr_url)
    comment = CommentRecord(
        comment_id=comment_id,
        comment_type=comment_type,
        author=author,
        body=comment_body,
        created_at=created_at,
        url=comment_url,
        diff_hunk=diff_hunk,
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=created_at)
    (base_dir / f"pr-{pr_number}.json").write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    classified = ClassifiedComment(
        comment_id=comment_id,
        category=category,
        confidence=confidence,
        summary=summary,
        classified_at=created_at,
        needs_review=needs_review,
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[classified],
        classified_at=created_at,
    )
    (base_dir / f"classified-pr-{pr_number}.json").write_text(
        json.dumps(classified_file.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def _make_text_response(*texts: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text) for text in texts]
    )


@pytest.fixture
def fake_anthropic_client() -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = _make_text_response(
        "## Symptom\nSynthesized symptom\n\n"
        "## Root Cause\nSynthesized cause\n\n"
        "## Fix or Workaround\nSynthesized fix"
    )
    return client


@pytest.fixture
def make_classified_file(tmp_path: Path) -> Path:
    _write_classified_pair(tmp_path)
    return tmp_path


@pytest.fixture
def make_two_classified_files(tmp_path: Path) -> Path:
    _write_classified_pair(tmp_path)
    _write_classified_pair(
        tmp_path,
        pr_number=2,
        title="Test PR 2",
        state="closed",
        comment_id=202,
        comment_type="issue",
        author="bob",
        comment_body="Use dependency injection to avoid tight coupling.",
        diff_hunk=None,
        category="code_pattern",
        confidence=0.90,
        summary="Use dependency injection to avoid tight coupling",
    )
    return tmp_path


@pytest.fixture
def make_issue_comment_classified(tmp_path: Path) -> Path:
    _write_classified_pair(
        tmp_path,
        title="Issue Comment PR",
        comment_type="issue",
        author="carol",
        comment_body="Consider using a factory pattern here.",
        diff_hunk=None,
        category="code_pattern",
        confidence=0.80,
        summary="Use factory pattern for object creation",
    )
    return tmp_path


@pytest.fixture
def make_malformed_classified(tmp_path: Path) -> Path:
    (tmp_path / "classified-pr-99.json").write_text(
        "this is not valid json",
        encoding="utf-8",
    )
    return tmp_path


def _make_generator(
    cache_dir: Path,
    kb_dir: Path,
    fake_anthropic_client: MagicMock,
    **kwargs,
):
    from github_pr_kb.generator import KBGenerator

    return KBGenerator(
        cache_dir=cache_dir,
        kb_dir=kb_dir,
        anthropic_client=fake_anthropic_client,
        **kwargs,
    )


def _article_paths(kb_dir: Path) -> list[Path]:
    return [
        path
        for path in kb_dir.rglob("*.md")
        if path.name != "INDEX.md"
    ]


def test_slugify_basic() -> None:
    from github_pr_kb.generator import slugify

    assert slugify("Avoid circular imports") == "avoid-circular-imports"


def test_slugify_unicode() -> None:
    from github_pr_kb.generator import slugify

    result = slugify("Cafe au lait")
    assert result.isascii()
    assert result


def test_slugify_max_length() -> None:
    from github_pr_kb.generator import slugify

    long_input = (
        "This is a very long summary that exceeds the sixty character limit "
        "for slugs in the KB"
    )
    result = slugify(long_input)
    assert len(result) <= 60


def test_slugify_special_chars() -> None:
    from github_pr_kb.generator import slugify

    assert slugify("C++ patterns: best & worst!") == "c-patterns-best-worst"


def test_slugify_empty() -> None:
    from github_pr_kb.generator import slugify

    assert slugify("") == "untitled"


def test_slugify_collision_suffix(
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    (kb_dir / "gotcha").mkdir(parents=True)
    (kb_dir / "gotcha" / "avoid-circular-imports.md").write_text(
        "existing article",
        encoding="utf-8",
    )

    gen = _make_generator(tmp_path, kb_dir, fake_anthropic_client)
    assert gen._resolve_slug("Avoid circular imports", "gotcha") == "avoid-circular-imports-2"


def test_yaml_str_newline() -> None:
    from github_pr_kb.generator import _yaml_str

    result = _yaml_str("Fix bug\nin middleware")
    assert "\n" not in result
    assert "Fix bug" in result
    assert "in middleware" in result


def test_config_kb_output_dir_default() -> None:
    from github_pr_kb.config import Settings

    settings = Settings(
        github_token="ghp_test000000000000000000000000000fake",
        anthropic_api_key=None,
    )
    assert settings.kb_output_dir == "kb"


def test_generate_creates_category_subdirs(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    assert (kb_dir / "gotcha").is_dir()


def test_article_written_to_category_subdir(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    assert (kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md").exists()


def test_article_frontmatter_fields(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    content = (kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md").read_text(
        encoding="utf-8"
    )
    required_fields = [
        "pr_url:",
        "pr_title:",
        "comment_url:",
        "author:",
        "date:",
        "category:",
        "confidence:",
        "needs_review:",
        "comment_id:",
    ]
    for field in required_fields:
        assert field in content


def test_diff_hunk_in_review_comment(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    content = (kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md").read_text(
        encoding="utf-8"
    )
    assert "```" in content
    assert "ctx.user = user" in content


def test_no_diff_hunk_for_issue_comment(
    make_issue_comment_classified: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_issue_comment_classified, kb_dir, fake_anthropic_client)
    gen.generate_all()
    articles = list((kb_dir / "code_pattern").glob("*.md"))
    assert len(articles) == 1
    assert "```" not in articles[0].read_text(encoding="utf-8")


def test_article_heading_is_summary(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    content = (kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md").read_text(
        encoding="utf-8"
    )
    assert "# Avoid circular imports in middleware" in content


def test_article_body_is_synthesized(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    content = (kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md").read_text(
        encoding="utf-8"
    )
    assert "Synthesized symptom" in content
    assert "Always copy context before modifying" not in content


def test_category_sections_in_prompt(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    prompt = fake_anthropic_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "## Symptom" in prompt
    assert "## Root Cause" in prompt
    assert "## Fix or Workaround" in prompt
    assert "Not stated in the source comment." in prompt


def test_incremental_no_duplicate(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    result1 = _make_generator(make_classified_file, kb_dir, fake_anthropic_client).generate_all()
    result2 = _make_generator(make_classified_file, kb_dir, fake_anthropic_client).generate_all()

    assert result1.written == 1
    assert result2.written == 0
    assert result2.skipped == 1


def test_incremental_adds_new_articles(
    make_two_classified_files: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    cache_dir = make_two_classified_files

    classified2 = cache_dir / "classified-pr-2.json"
    classified2_backup = cache_dir / "classified-pr-2.json.bak"
    classified2.rename(classified2_backup)

    result1 = _make_generator(cache_dir, kb_dir, fake_anthropic_client).generate_all()
    assert result1.written == 1

    classified2_backup.rename(classified2)
    result2 = _make_generator(cache_dir, kb_dir, fake_anthropic_client).generate_all()
    assert result2.written == 1
    assert result2.skipped == 1


def test_manifest_written(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    manifest = json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert manifest["101"] == "gotcha/avoid-circular-imports-in-middleware.md"


def test_generate_result_summary(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    from github_pr_kb.generator import GenerateResult

    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    result = gen.generate_all()
    assert isinstance(result, GenerateResult)
    assert result.written == 1
    assert result.skipped == 0
    assert result.filtered == 0
    assert result.failed == []


def test_malformed_classified_file(
    make_malformed_classified: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_malformed_classified, kb_dir, fake_anthropic_client)
    result = gen.generate_all()
    assert len(result.failed) == 1
    assert result.failed[0]["file"] == "classified-pr-99.json"


def test_empty_synthesis_output_skipped(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    fake_anthropic_client.messages.create.return_value = SimpleNamespace(content=[])
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    result = gen.generate_all()

    assert len(result.failed) == 1
    assert _article_paths(kb_dir) == []
    manifest = json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert "101" not in manifest


def test_source_echo_output_skipped(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    fake_anthropic_client.messages.create.return_value = _make_text_response(
        "Always copy context before modifying..."
    )
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    result = gen.generate_all()

    assert len(result.failed) == 1
    assert _article_paths(kb_dir) == []
    manifest = json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert "101" not in manifest


def test_low_confidence_filtered(
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    _write_classified_pair(
        tmp_path,
        comment_id=301,
        comment_body="This is too low confidence to publish.",
        confidence=0.30,
        summary="Low confidence comment",
        needs_review=True,
    )
    kb_dir = tmp_path / "kb"
    gen = _make_generator(tmp_path, kb_dir, fake_anthropic_client)
    result = gen.generate_all()

    assert result.filtered == 1
    assert result.written == 0
    assert _article_paths(kb_dir) == []
    manifest = json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert "301" not in manifest
    fake_anthropic_client.messages.create.assert_not_called()


def test_synthesis_failure_skipped(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    fake_anthropic_client.messages.create.side_effect = anthropic.APIError(
        "boom",
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        body=None,
    )
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    result = gen.generate_all()

    assert len(result.failed) == 1
    assert _article_paths(kb_dir) == []
    manifest = json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert "101" not in manifest


def test_needs_review_in_frontmatter(
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    _write_classified_pair(
        tmp_path,
        pr_number=3,
        title="Low Confidence PR",
        comment_id=301,
        comment_type="issue",
        author="dave",
        comment_body="This might be a gotcha.",
        diff_hunk=None,
        confidence=0.60,
        summary="Possible gotcha with low confidence",
        needs_review=True,
    )
    kb_dir = tmp_path / "kb"
    gen = _make_generator(tmp_path, kb_dir, fake_anthropic_client)
    gen.generate_all()

    article = next((kb_dir / "gotcha").glob("*.md"))
    assert "needs_review: true" in article.read_text(encoding="utf-8")


def test_other_category_included(
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    _write_classified_pair(
        tmp_path,
        pr_number=4,
        title="Other Category PR",
        comment_id=401,
        comment_type="issue",
        author="eve",
        comment_body="Minor style comment.",
        diff_hunk=None,
        category="other",
        confidence=0.55,
        summary="Minor style comment about formatting",
        needs_review=True,
    )
    kb_dir = tmp_path / "kb"
    gen = _make_generator(tmp_path, kb_dir, fake_anthropic_client)
    gen.generate_all()

    assert (kb_dir / "other").is_dir()
    assert len(list((kb_dir / "other").glob("*.md"))) == 1


def test_index_file_created(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    assert (kb_dir / "INDEX.md").exists()


def test_index_grouped_by_category(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()
    assert "## Gotcha (1)" in (kb_dir / "INDEX.md").read_text(encoding="utf-8")


def test_index_review_marker(
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    _write_classified_pair(
        tmp_path,
        pr_number=5,
        title="Low Confidence Review PR",
        comment_id=501,
        comment_type="issue",
        author="frank",
        comment_body="This might be a gotcha worth reviewing.",
        diff_hunk=None,
        confidence=0.60,
        summary="Low confidence gotcha needs human review",
        needs_review=True,
    )
    kb_dir = tmp_path / "kb"
    gen = _make_generator(tmp_path, kb_dir, fake_anthropic_client)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    assert any("[review]" in line for line in content.splitlines())


def test_index_regenerated_on_rerun(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen1 = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen1.generate_all()
    content1 = (kb_dir / "INDEX.md").read_text(encoding="utf-8")

    gen2 = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen2.generate_all()
    content2 = (kb_dir / "INDEX.md").read_text(encoding="utf-8")

    assert content1 == content2


def test_index_multiple_categories(
    make_two_classified_files: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_two_classified_files, kb_dir, fake_anthropic_client)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    assert "## Gotcha (1)" in content
    assert "## Code Pattern (1)" in content


def test_index_entry_has_summary_and_link(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    import re as _re

    kb_dir = tmp_path / "kb"
    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    assert _re.findall(r"^- \[.+\]\(.+/.+\.md\)", content, _re.MULTILINE)


def test_index_empty_kb(
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    kb_dir = tmp_path / "kb"

    gen = _make_generator(cache_dir, kb_dir, fake_anthropic_client)
    gen.generate_all()

    content = (kb_dir / "INDEX.md").read_text(encoding="utf-8")
    assert "# Knowledge Base Index" in content
    assert "## " not in content


def test_regenerate_success_replaces_existing_kb(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    kb_dir = tmp_path / "kb"
    (kb_dir / "gotcha").mkdir(parents=True)
    (kb_dir / "gotcha" / "old-article.md").write_text("old article", encoding="utf-8")
    (kb_dir / ".manifest.json").write_text(
        json.dumps({"999": "gotcha/old-article.md"}, indent=2),
        encoding="utf-8",
    )
    (kb_dir / "INDEX.md").write_text("# Old Index\n", encoding="utf-8")

    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    result = gen.generate_all(regenerate=True)

    assert result.written == 1
    assert not (kb_dir / "gotcha" / "old-article.md").exists()
    assert (kb_dir / "gotcha" / "avoid-circular-imports-in-middleware.md").exists()
    manifest = json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8"))
    assert manifest == {"101": "gotcha/avoid-circular-imports-in-middleware.md"}
    assert "Avoid circular imports in middleware" in (kb_dir / "INDEX.md").read_text(
        encoding="utf-8"
    )


def test_regenerate_abort_preserves_existing_kb(
    make_classified_file: Path,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kb_dir = tmp_path / "kb"
    (kb_dir / "gotcha").mkdir(parents=True)
    old_article = kb_dir / "gotcha" / "old-article.md"
    old_article.write_text("old article", encoding="utf-8")
    old_manifest = {"999": "gotcha/old-article.md"}
    (kb_dir / ".manifest.json").write_text(
        json.dumps(old_manifest, indent=2),
        encoding="utf-8",
    )
    (kb_dir / "INDEX.md").write_text("# Old Index\n", encoding="utf-8")

    gen = _make_generator(make_classified_file, kb_dir, fake_anthropic_client)
    original_generate_index = gen._generate_index

    def explode_during_staging() -> None:
        if gen._kb_dir != kb_dir:
            raise RuntimeError("staged generation failed")
        original_generate_index()

    monkeypatch.setattr(gen, "_generate_index", explode_during_staging)

    with pytest.raises(RuntimeError, match="staged generation failed"):
        gen.generate_all(regenerate=True)

    assert old_article.exists()
    assert json.loads((kb_dir / ".manifest.json").read_text(encoding="utf-8")) == old_manifest
    assert not any(path.name.startswith("kb-staging-") for path in tmp_path.iterdir())


def test_generate_requires_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import github_pr_kb.config as config_module
    from github_pr_kb.generator import KBGenerator

    monkeypatch.setattr(
        config_module,
        "settings",
        SimpleNamespace(
            kb_output_dir="kb",
            anthropic_api_key=None,
            anthropic_generate_model=None,
            min_confidence=0.5,
        ),
    )

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        KBGenerator(cache_dir=tmp_path, kb_dir=tmp_path / "kb")


def test_generate_model_env_var(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_anthropic_client: MagicMock,
) -> None:
    import github_pr_kb.config as config_module

    monkeypatch.setattr(
        config_module,
        "settings",
        SimpleNamespace(
            kb_output_dir="kb",
            anthropic_api_key="sk-ant-fake",
            anthropic_generate_model="claude-sonnet-test",
            min_confidence=0.5,
        ),
    )

    gen = _make_generator(tmp_path, tmp_path / "kb", fake_anthropic_client)
    assert gen._model == "claude-sonnet-test"
