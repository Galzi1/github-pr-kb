"""Generates markdown KB articles from classified PR comments.

Reads classified-pr-N.json files from the cache directory (written by PRClassifier),
assembles one markdown article per classified comment organized into per-category
subdirectories, and maintains a manifest for incremental dedup.
"""
import contextlib
import json
import logging
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, ValidationError

from github_pr_kb.models import (
    ClassifiedComment,
    ClassifiedFile,
    CommentRecord,
    PRFile,
    PRRecord,
)

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")
_FRONTMATTER_DELIMITER = "---"


class IndexEntry(NamedTuple):
    stem: str
    rel_path: str
    summary: str
    needs_review: bool


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def slugify(text: str, max_len: int = 60) -> str:
    """Convert AI summary text to a URL-safe, filesystem-safe slug.

    Applies NFKD unicode normalization, lowercases, replaces non-alphanumeric
    runs with hyphens, and truncates at the last word boundary within max_len.
    """
    if not text:
        return "untitled"

    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slugged = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")

    if not slugged:
        return "untitled"

    if len(slugged) > max_len:
        truncated = slugged[:max_len]
        last_hyphen = truncated.rfind("-")
        slugged = truncated[:last_hyphen] if last_hyphen > 0 else truncated

    return slugged or "untitled"


def _yaml_str(value: str) -> str:
    """Wrap value in double quotes for safe YAML frontmatter output.

    Escapes backslashes and double quotes, and collapses embedded newlines to
    spaces so PR titles with line breaks produce valid single-line YAML values.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class GenerateResult(BaseModel):
    """Summary of a generate_all() run."""

    model_config = ConfigDict(extra="ignore")

    written: int
    skipped: int
    failed: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Atomic write (copied from classifier.py to avoid cross-module coupling)
# ---------------------------------------------------------------------------


def _write_atomic(path: Path, data: str) -> None:
    """Write data to path atomically using a temp file and os.replace."""
    tmp_name: str | None = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_name, str(path))
    except Exception:
        if tmp_name is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
        raise


# ---------------------------------------------------------------------------
# KBGenerator
# ---------------------------------------------------------------------------


class KBGenerator:
    """Reads classified-pr-N.json files and produces per-category KB articles.

    Mirrors the PRClassifier class shape for consistency with established project patterns.
    """

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        kb_dir: Path | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        if kb_dir is not None:
            self._kb_dir = kb_dir
        else:
            # Lazy import to avoid import-time errors in tests
            from github_pr_kb.config import settings
            self._kb_dir = Path(settings.kb_output_dir)

        self._manifest: dict[str, str] = self._load_manifest()
        # Lazily populated per-category slug cache to avoid repeated manifest scans
        # and filesystem globs in _resolve_slug during batch article generation.
        self._category_slugs: dict[str, set[str]] = {}
        self._written = 0
        self._skipped = 0
        self._failed: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # Manifest management
    # ------------------------------------------------------------------

    def _load_manifest(self) -> dict[str, str]:
        """Load kb/.manifest.json; keys are str(comment_id), values are relative paths."""
        path = self._kb_dir / ".manifest.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.warning("kb/.manifest.json is corrupt — rebuilding from scratch")
            return {}

    def _save_manifest(self) -> None:
        self._kb_dir.mkdir(parents=True, exist_ok=True)
        _write_atomic(self._kb_dir / ".manifest.json", json.dumps(self._manifest, indent=2))

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def _find_classified_files(self) -> list[Path]:
        return list(self._cache_dir.glob("classified-pr-*.json"))

    # ------------------------------------------------------------------
    # Slug resolution with collision handling
    # ------------------------------------------------------------------

    def _resolve_slug(self, summary: str, category: str) -> str:
        """Compute a unique slug for summary within category, appending -N on collision."""
        base_slug = slugify(summary)
        existing_slugs = self._slugs_for_category(category)

        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def _slugs_for_category(self, category: str) -> set[str]:
        """Return (and cache) the set of existing slugs for a category.

        Built once per category from both the manifest and the filesystem so that
        files written outside this tool are also considered for collision avoidance.
        Updated in-place after each successful write to avoid re-scanning.
        """
        if category not in self._category_slugs:
            slugs: set[str] = set()
            for rel_path in self._manifest.values():
                parts = rel_path.split("/")
                if len(parts) == 2 and parts[0] == category:
                    slugs.add(parts[1].removesuffix(".md"))
            category_dir = self._kb_dir / category
            if category_dir.exists():
                for md_file in category_dir.glob("*.md"):
                    slugs.add(md_file.stem)
            self._category_slugs[category] = slugs
        return self._category_slugs[category]

    # ------------------------------------------------------------------
    # Article construction
    # ------------------------------------------------------------------

    def _build_article(
        self,
        pr: PRRecord,
        comment: CommentRecord,
        classified: ClassifiedComment,
    ) -> str:
        frontmatter_lines = [
            _FRONTMATTER_DELIMITER,
            f"pr_url: {pr.url}",
            f"pr_title: {_yaml_str(pr.title)}",
            f"comment_url: {comment.url}",
            f"author: {_yaml_str(comment.author)}",
            f"date: {comment.created_at.isoformat()}",
            f"category: {classified.category}",
            f"confidence: {classified.confidence}",
            f"needs_review: {str(classified.needs_review).lower()}",
            f"comment_id: {comment.comment_id}",
            _FRONTMATTER_DELIMITER,
        ]

        body_parts = [
            "\n".join(frontmatter_lines),
            "",
            f"# {classified.summary}",
            "",
            comment.body,
        ]

        if comment.diff_hunk:
            body_parts.extend(["", "```", comment.diff_hunk, "```"])

        return "\n".join(body_parts) + "\n"

    # ------------------------------------------------------------------
    # Index generation
    # ------------------------------------------------------------------

    def _generate_index(self) -> None:
        """Regenerate kb/INDEX.md from all existing .md files on disk.

        Scans all per-category .md files, parses each file's YAML frontmatter,
        groups entries by category (sorted alphabetically), and writes INDEX.md.
        Files with unparseable frontmatter are skipped with a warning.
        An empty KB still produces a valid index with just the title.
        """
        entries = self._collect_index_entries()
        index_content = self._build_index_content(entries)
        self._kb_dir.mkdir(parents=True, exist_ok=True)
        _write_atomic(self._kb_dir / "INDEX.md", index_content)

    def _collect_index_entries(self) -> dict[str, list[IndexEntry]]:
        """Scan kb_dir for category/*.md files and extract their index metadata."""
        entries: dict[str, list[IndexEntry]] = {}

        for md_file in sorted(self._kb_dir.rglob("*.md")):
            if md_file.name == "INDEX.md":
                continue

            try:
                rel_path = md_file.relative_to(self._kb_dir)
            except ValueError:
                continue

            if len(rel_path.parts) != 2:
                continue

            category_slug = rel_path.parts[0]

            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Could not read article %s for index: %s — skipping", md_file.name, exc)
                continue

            frontmatter_fields, summary = self._parse_article_metadata(text)
            if frontmatter_fields is None:
                logger.warning("Could not parse frontmatter in %s — skipping from index", md_file.name)
                continue

            # needs_review is stored in frontmatter as the string "true" or "false"
            needs_review = frontmatter_fields.get("needs_review", "false").strip().lower() == "true"

            entries.setdefault(category_slug, []).append(
                IndexEntry(
                    stem=md_file.stem,
                    rel_path=str(rel_path).replace("\\", "/"),
                    summary=summary,
                    needs_review=needs_review,
                )
            )

        return entries

    def _build_index_content(self, entries: dict[str, list[IndexEntry]]) -> str:
        """Render INDEX.md markdown content from collected category entries."""
        lines: list[str] = ["# Knowledge Base Index", ""]

        for category_slug in sorted(entries.keys()):
            display_name = category_slug.replace("_", " ").title()
            category_entries = sorted(entries[category_slug], key=lambda e: e.stem)

            lines.append(f"## {display_name} ({len(category_entries)})")
            lines.append("")

            for entry in category_entries:
                entry_line = f"- [{entry.summary}]({entry.rel_path})"
                if entry.needs_review:
                    entry_line += " [review]"
                lines.append(entry_line)

            lines.append("")

        return "\n".join(lines)

    def _parse_article_metadata(
        self, text: str
    ) -> tuple[dict[str, str] | None, str]:
        """Parse YAML frontmatter and first # heading from article text.

        Returns (frontmatter_dict, summary_text). frontmatter_dict is None if
        the frontmatter delimiters are not found or malformed. summary_text is
        the first # heading found after the frontmatter, or empty string if absent.
        """
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
            return None, ""

        closing_idx: int | None = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == _FRONTMATTER_DELIMITER:
                closing_idx = i
                break

        if closing_idx is None:
            return None, ""

        fields: dict[str, str] = {}
        for fm_line in lines[1:closing_idx]:
            if ":" in fm_line:
                key, _, value = fm_line.partition(":")
                fields[key.strip()] = value.strip()

        summary = ""
        for line in lines[closing_idx + 1:]:
            if line.startswith("# "):
                summary = line[2:].strip()
                break

        return fields, summary

    # ------------------------------------------------------------------
    # Processing pipeline
    # ------------------------------------------------------------------

    def _write_article(
        self,
        pr: PRRecord,
        comment: CommentRecord,
        classification: ClassifiedComment,
    ) -> str | None:
        """Write a KB article for one classification; return rel_path or None on failure."""
        article = self._build_article(pr, comment, classification)
        slug = self._resolve_slug(classification.summary, classification.category)

        category_dir = self._kb_dir / classification.category
        category_dir.mkdir(parents=True, exist_ok=True)

        rel_path = f"{classification.category}/{slug}.md"
        try:
            _write_atomic(self._kb_dir / rel_path, article)
        except OSError as exc:
            logger.warning("Could not write article %s: %s", rel_path, exc)
            self._failed.append({
                "file": rel_path,
                "reason": type(exc).__name__,
                "detail": str(exc),
            })
            return None

        self._slugs_for_category(classification.category).add(slug)
        return rel_path

    def _process_classified_file(self, classified_path: Path) -> None:
        """Process one classified-pr-N.json file, writing articles for new comments."""
        try:
            classified_file = ClassifiedFile.model_validate_json(
                classified_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not parse classified file %s: %s — skipping",
                classified_path.name,
                exc,
            )
            self._failed.append({
                "file": classified_path.name,
                "reason": type(exc).__name__,
                "detail": str(exc),
            })
            return

        pr_number = classified_file.pr.number
        pr_path = self._cache_dir / f"pr-{pr_number}.json"
        try:
            pr_file = PRFile.model_validate_json(pr_path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load PR file pr-%d.json: %s — skipping classified file %s",
                pr_number,
                exc,
                classified_path.name,
            )
            self._failed.append({
                "file": f"pr-{pr_number}.json",
                "reason": type(exc).__name__,
                "detail": str(exc),
            })
            return

        comments_by_id: dict[int, CommentRecord] = {
            c.comment_id: c for c in pr_file.comments
        }

        for classification in classified_file.classifications:
            # Manifest keys are strings to match JSON serialization
            key = str(classification.comment_id)

            if key in self._manifest:
                self._skipped += 1
                continue

            comment = comments_by_id.get(classification.comment_id)
            if comment is None:
                logger.warning(
                    "Comment %d not found in pr-%d.json — skipping",
                    classification.comment_id,
                    pr_number,
                )
                self._failed.append({
                    "file": classified_path.name,
                    "reason": "CommentNotFound",
                    "detail": f"comment_id={classification.comment_id} missing from pr-{pr_number}.json",
                })
                continue

            rel_path = self._write_article(classified_file.pr, comment, classification)
            if rel_path is not None:
                self._manifest[key] = rel_path
                self._written += 1

    # ------------------------------------------------------------------
    # Main generation entry point
    # ------------------------------------------------------------------

    def generate_all(self) -> GenerateResult:
        """Read all classified-pr-N.json files, write new articles, update manifest."""
        self._written = 0
        self._skipped = 0
        self._failed = []
        self._category_slugs = {}

        for classified_path in self._find_classified_files():
            self._process_classified_file(classified_path)

        self._save_manifest()
        self._generate_index()
        return GenerateResult(written=self._written, skipped=self._skipped, failed=self._failed)
