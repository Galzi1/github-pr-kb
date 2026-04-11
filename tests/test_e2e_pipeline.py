"""End-to-end pipeline test: extract → classify → generate against github-pr-kb-demo.

Run with:
    RUN_INTEGRATION_TESTS=1 .venv/Scripts/python.exe -m pytest tests/test_e2e_pipeline.py -v -m e2e

Skipped automatically unless all conditions hold:
  - RUN_INTEGRATION_TESTS=1 env var is set
  - GITHUB_TOKEN is a real token (not the unit-test dummy value)
  - ANTHROPIC_API_KEY is a real key (not the unit-test dummy value)
"""

import json
import os
import re

import pytest

_DUMMY_GH_TOKEN = "ghp_test000000000000000000000000000fake"
_DUMMY_ANTHROPIC_KEY = "sk-ant-test000000000000000000000000000fake"
_SKIP_REASON = (
    "E2E pipeline tests require RUN_INTEGRATION_TESTS=1, "
    "a real GITHUB_TOKEN, and a real ANTHROPIC_API_KEY"
)

DEMO_REPO = "Galzi1/github-pr-kb-demo"
VALID_CATEGORIES = {
    "architecture_decision",
    "code_pattern",
    "gotcha",
    "domain_knowledge",
    "other",
}


def _e2e_enabled() -> bool:
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        return False
    from github_pr_kb.config import settings

    if settings.github_token == _DUMMY_GH_TOKEN:
        return False
    api_key = settings.anthropic_api_key
    return api_key is not None and api_key != _DUMMY_ANTHROPIC_KEY


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _e2e_enabled(), reason=_SKIP_REASON),
]


@pytest.fixture(scope="module")
def pipeline_dirs(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Run the full extract → classify → generate pipeline once, return paths."""
    cache_dir = tmp_path_factory.mktemp("e2e_cache")
    kb_dir = tmp_path_factory.mktemp("e2e_kb")

    # --- Extract ---
    from github_pr_kb.extractor import GitHubExtractor

    extractor = GitHubExtractor(DEMO_REPO, cache_dir=cache_dir)
    paths = extractor.extract(state="closed")
    assert len(paths) > 0, "Extraction produced no PR cache files"

    # --- Classify ---
    from github_pr_kb.classifier import PRClassifier

    classifier = PRClassifier(cache_dir=cache_dir)
    classifier.classify_all()

    # --- Generate ---
    from github_pr_kb.generator import KBGenerator

    generator = KBGenerator(cache_dir=cache_dir, kb_dir=kb_dir)
    result = generator.generate_all()
    assert result.written > 0 or result.skipped > 0, "Generation produced no articles"

    return {"cache_dir": cache_dir, "kb_dir": kb_dir, "gen_result": result}


# ---------------------------------------------------------------------------
# Extraction assertions
# ---------------------------------------------------------------------------


def test_extraction_produces_pr_cache_files(pipeline_dirs: dict) -> None:
    """At least one PR cache file exists and contains valid JSON."""
    cache_dir = pipeline_dirs["cache_dir"]
    pr_files = sorted(cache_dir.glob("pr-*.json"))
    assert len(pr_files) >= 1

    from github_pr_kb.models import PRFile

    for pf in pr_files:
        data = json.loads(pf.read_text(encoding="utf-8"))
        pr = PRFile.model_validate(data)
        assert pr.pr.number > 0
        assert len(pr.comments) > 0


def test_extraction_skips_automation_prs(pipeline_dirs: dict) -> None:
    """No cache file should correspond to an automation KB bot PR."""
    cache_dir = pipeline_dirs["cache_dir"]
    for pf in cache_dir.glob("pr-*.json"):
        data = json.loads(pf.read_text(encoding="utf-8"))
        title = data.get("pr", {}).get("title", "")
        assert "update PR knowledge base" not in title.lower(), (
            f"{pf.name} contains a bot PR: {title}"
        )


# ---------------------------------------------------------------------------
# Classification assertions
# ---------------------------------------------------------------------------


def test_classification_produces_classified_files(pipeline_dirs: dict) -> None:
    """At least one classified-pr-*.json exists with valid structure."""
    cache_dir = pipeline_dirs["cache_dir"]
    classified_files = sorted(cache_dir.glob("classified-pr-*.json"))
    assert len(classified_files) >= 1

    from github_pr_kb.models import ClassifiedFile

    for cf in classified_files:
        data = json.loads(cf.read_text(encoding="utf-8"))
        classified = ClassifiedFile.model_validate(data)
        assert classified.pr_number > 0
        for comment in classified.comments:
            assert comment.category in VALID_CATEGORIES
            assert 0.0 <= comment.confidence <= 1.0
            assert isinstance(comment.summary, str)
            assert len(comment.summary) > 0


def test_classification_index_exists(pipeline_dirs: dict) -> None:
    """classification-index.json exists and maps body hashes to classifications."""
    cache_dir = pipeline_dirs["cache_dir"]
    index_file = cache_dir / "classification-index.json"
    assert index_file.exists()
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert len(index) > 0
    for key, entry in index.items():
        assert len(key) == 64, f"Expected SHA-256 hash, got: {key}"
        assert entry.get("category") in VALID_CATEGORIES


# ---------------------------------------------------------------------------
# Generation assertions
# ---------------------------------------------------------------------------


def test_generation_creates_kb_articles(pipeline_dirs: dict) -> None:
    """At least one markdown article exists under kb/<category>/."""
    kb_dir = pipeline_dirs["kb_dir"]
    articles = list(kb_dir.glob("*/*.md"))
    content_articles = [a for a in articles if a.name != "INDEX.md"]
    assert len(content_articles) >= 1


def test_generation_articles_have_valid_frontmatter(pipeline_dirs: dict) -> None:
    """Every generated article has YAML frontmatter with required fields."""
    kb_dir = pipeline_dirs["kb_dir"]
    frontmatter_re = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

    for article_path in kb_dir.glob("*/*.md"):
        if article_path.name == "INDEX.md":
            continue
        content = article_path.read_text(encoding="utf-8")
        match = frontmatter_re.match(content)
        assert match, f"{article_path} missing YAML frontmatter"
        fm = match.group(1)
        assert "category:" in fm, f"{article_path} frontmatter missing category"
        assert "source_pr:" in fm, f"{article_path} frontmatter missing source_pr"


def test_generation_creates_index(pipeline_dirs: dict) -> None:
    """INDEX.md exists at kb root."""
    kb_dir = pipeline_dirs["kb_dir"]
    index = kb_dir / "INDEX.md"
    assert index.exists()
    text = index.read_text(encoding="utf-8")
    assert "# Knowledge Base Index" in text or "# PR Knowledge Base" in text


def test_generation_creates_manifest(pipeline_dirs: dict) -> None:
    """kb/.manifest.json exists and maps comment IDs to article paths."""
    kb_dir = pipeline_dirs["kb_dir"]
    manifest_file = kb_dir / ".manifest.json"
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert len(manifest) > 0
    for comment_id, rel_path in manifest.items():
        assert rel_path.endswith(".md")
        assert (kb_dir / rel_path).exists(), f"Manifest entry {rel_path} not found on disk"


def test_generation_articles_under_valid_categories(pipeline_dirs: dict) -> None:
    """Every article directory is a valid classification category."""
    kb_dir = pipeline_dirs["kb_dir"]
    category_dirs = {
        d.name for d in kb_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    }
    assert category_dirs, "No category directories found"
    unexpected = category_dirs - VALID_CATEGORIES
    assert not unexpected, f"Unexpected category directories: {unexpected}"
