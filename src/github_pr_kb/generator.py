"""Generates markdown KB articles from classified PR comments.

Reads classified-pr-N.json files from the cache directory (written by PRClassifier),
assembles one markdown article per classified comment organized into per-category
subdirectories, and maintains a manifest for incremental dedup.

Requirements: KB-01 (per-category dirs), KB-02 (frontmatter), KB-04 (manifest dedup).
"""
import contextlib
import json
import logging
import os
import re
import tempfile
import unicodedata
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def slugify(text: str, max_len: int = 60) -> str:
    """Convert AI summary text to a URL-safe, filesystem-safe slug (D-08).

    Rules: lowercase, ASCII-only (NFKD transliteration), hyphens for non-alphanumeric,
    max max_len characters truncated at word boundary, fallback 'untitled'.
    """
    if not text:
        return "untitled"

    # Normalize unicode to ASCII
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase and replace non-alphanumeric runs with hyphens
    lowered = ascii_text.lower()
    slugged = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")

    if not slugged:
        return "untitled"

    # Truncate at word boundary to stay within max_len
    if len(slugged) > max_len:
        truncated = slugged[:max_len]
        last_hyphen = truncated.rfind("-")
        slugged = truncated[:last_hyphen] if last_hyphen > 0 else truncated

    return slugged or "untitled"


def _yaml_str(value: str) -> str:
    """Wrap value in double quotes for safe YAML frontmatter output.

    Escapes backslashes, double quotes, and replaces newlines/carriage returns
    with a space so PR titles with embedded newlines produce valid single-line YAML.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class GenerateResult(BaseModel):
    """Summary of a generate_all() run (D-19)."""

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
            # Import inside __init__ to avoid import-time errors in tests
            from github_pr_kb.config import settings
            self._kb_dir = Path(settings.kb_output_dir)

        self._manifest: dict[str, str] = self._load_manifest()
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
        """Write self._manifest to kb_dir/.manifest.json atomically."""
        self._kb_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self._kb_dir / ".manifest.json"
        _write_atomic(manifest_path, json.dumps(self._manifest, indent=2))

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def _find_classified_files(self) -> list[Path]:
        """Return all classified-pr-*.json paths in the cache directory."""
        return list(self._cache_dir.glob("classified-pr-*.json"))

    # ------------------------------------------------------------------
    # Slug resolution with collision handling (D-09)
    # ------------------------------------------------------------------

    def _resolve_slug(self, summary: str, category: str) -> str:
        """Compute a unique slug for summary within category, appending -N on collision."""
        base_slug = slugify(summary)

        # Collect existing slugs for this category from manifest values
        existing_slugs: set[str] = set()
        for rel_path in self._manifest.values():
            parts = rel_path.split("/")
            if len(parts) == 2 and parts[0] == category:
                existing_slugs.add(parts[1].removesuffix(".md"))

        # Also check filesystem for files not yet in manifest
        category_dir = self._kb_dir / category
        if category_dir.exists():
            for md_file in category_dir.glob("*.md"):
                existing_slugs.add(md_file.stem)

        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    # ------------------------------------------------------------------
    # Article construction
    # ------------------------------------------------------------------

    def _build_article(
        self,
        pr: PRRecord,
        comment: CommentRecord,
        classified: ClassifiedComment,
    ) -> str:
        """Build the full markdown article string for a classified comment."""
        frontmatter_lines = [
            "---",
            f"pr_url: {pr.url}",
            f"pr_title: {_yaml_str(pr.title)}",
            f"comment_url: {comment.url}",
            f"author: {_yaml_str(comment.author)}",
            f"date: {comment.created_at.isoformat()}",
            f"category: {classified.category}",
            f"confidence: {classified.confidence}",
            f"needs_review: {str(classified.needs_review).lower()}",
            f"comment_id: {comment.comment_id}",
            "---",
        ]
        frontmatter = "\n".join(frontmatter_lines)

        # Article body: heading (D-01) + original comment body (D-01)
        body_parts = [
            frontmatter,
            "",
            f"# {classified.summary}",
            "",
            comment.body,
        ]

        # Append diff_hunk only for review comments that have one (D-03)
        if comment.diff_hunk:
            body_parts.extend([
                "",
                "```",
                comment.diff_hunk,
                "```",
            ])

        return "\n".join(body_parts) + "\n"

    # ------------------------------------------------------------------
    # Index generation (D-11 through D-14)
    # ------------------------------------------------------------------

    def _generate_index(self) -> None:
        """Regenerate kb/INDEX.md from all existing .md files on disk (D-14).

        Scans all .md files in per-category subdirectories (excluding INDEX.md itself),
        parses each file's YAML frontmatter to extract category, needs_review, and the
        first # heading as the summary text.  Groups entries by category (sorted
        alphabetically), builds INDEX.md content, and writes it atomically.

        Files with unparseable frontmatter are skipped with a warning (Pitfall 5).
        When the KB is empty the index is still written with just the title (R3 mitigation).
        """
        # category -> list of (filename_stem, relative_path_str, summary, needs_review)
        entries: dict[str, list[tuple[str, str, str, bool]]] = {}

        for md_file in sorted(self._kb_dir.rglob("*.md")):
            # Skip INDEX.md itself — it lives at the top level
            if md_file.name == "INDEX.md":
                continue

            # Determine the relative path from kb_dir (e.g. "gotcha/avoid-circular.md")
            try:
                rel_path = md_file.relative_to(self._kb_dir)
            except ValueError:
                continue

            # Only include files one level deep (category/slug.md), not nested deeper
            if len(rel_path.parts) != 2:
                continue

            category_slug = rel_path.parts[0]

            # Parse YAML frontmatter between first and second --- delimiters
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Could not read article %s for index: %s — skipping", md_file.name, exc)
                continue

            frontmatter_fields, summary = self._parse_article_metadata(text)
            if frontmatter_fields is None:
                logger.warning(
                    "Could not parse frontmatter in %s — skipping from index", md_file.name
                )
                continue

            # R3 mitigation: needs_review is stored as YAML string "true"/"false"
            raw_needs_review = frontmatter_fields.get("needs_review", "false")
            needs_review = raw_needs_review.strip().lower() == "true"

            entries.setdefault(category_slug, []).append(
                (md_file.stem, str(rel_path).replace("\\", "/"), summary, needs_review)
            )

        # Build INDEX.md content
        lines: list[str] = ["# Knowledge Base Index", ""]

        for category_slug in sorted(entries.keys()):
            display_name = category_slug.replace("_", " ").title()
            category_entries = sorted(entries[category_slug], key=lambda e: e[0])
            count = len(category_entries)

            lines.append(f"## {display_name} ({count})")
            lines.append("")

            for _stem, rel_path_str, summary, needs_review in category_entries:
                entry_line = f"- [{summary}]({rel_path_str})"
                if needs_review:
                    entry_line += " [review]"
                lines.append(entry_line)

            lines.append("")

        index_content = "\n".join(lines)

        self._kb_dir.mkdir(parents=True, exist_ok=True)
        _write_atomic(self._kb_dir / "INDEX.md", index_content)

    def _parse_article_metadata(
        self, text: str
    ) -> tuple[dict[str, str] | None, str]:
        """Parse YAML frontmatter and first # heading from article text.

        Returns (frontmatter_dict, summary_text).  frontmatter_dict is None if
        the frontmatter delimiters are not found or malformed.  summary_text is
        the first # heading found after the frontmatter, or empty string if absent.
        """
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return None, ""

        closing_idx: int | None = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_idx = i
                break

        if closing_idx is None:
            return None, ""

        frontmatter_lines = lines[1:closing_idx]
        fields: dict[str, str] = {}
        for fm_line in frontmatter_lines:
            if ":" in fm_line:
                key, _, value = fm_line.partition(":")
                fields[key.strip()] = value.strip()

        # Find first # heading after frontmatter
        summary = ""
        for line in lines[closing_idx + 1 :]:
            if line.startswith("# "):
                summary = line[2:].strip()
                break

        return fields, summary

    # ------------------------------------------------------------------
    # Main generation entry point
    # ------------------------------------------------------------------

    def generate_all(self) -> GenerateResult:
        """Read all classified-pr-N.json files, write new articles, update manifest."""
        for classified_path in self._find_classified_files():
            # Parse the classified file (D-18: log warning on error, continue)
            try:
                content = classified_path.read_text(encoding="utf-8")
                classified_file = ClassifiedFile.model_validate_json(content)
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
                continue

            # Load the corresponding pr-N.json for CommentRecord data
            pr_number = classified_file.pr.number
            pr_path = self._cache_dir / f"pr-{pr_number}.json"
            try:
                pr_content = pr_path.read_text(encoding="utf-8")
                pr_file = PRFile.model_validate_json(pr_content)
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
                continue

            # Build a lookup map from comment_id to CommentRecord
            comments_by_id: dict[int, CommentRecord] = {
                c.comment_id: c for c in pr_file.comments
            }

            for classification in classified_file.classifications:
                key = str(classification.comment_id)  # str for JSON key consistency (Pitfall 1)

                # Skip already-generated articles (KB-04 dedup)
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

                article = self._build_article(classified_file.pr, comment, classification)
                slug = self._resolve_slug(classification.summary, classification.category)

                category_dir = self._kb_dir / classification.category
                category_dir.mkdir(parents=True, exist_ok=True)  # D-10

                rel_path = f"{classification.category}/{slug}.md"
                try:
                    _write_atomic(self._kb_dir / rel_path, article)
                except OSError as exc:
                    logger.warning(
                        "Could not write article %s: %s",
                        rel_path,
                        exc,
                    )
                    self._failed.append({
                        "file": rel_path,
                        "reason": type(exc).__name__,
                        "detail": str(exc),
                    })
                    continue

                self._manifest[key] = rel_path
                self._written += 1

        self._save_manifest()
        self._generate_index()
        return GenerateResult(written=self._written, skipped=self._skipped, failed=self._failed)
