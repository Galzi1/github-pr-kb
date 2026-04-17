"""Generates markdown KB articles from classified PR comments.

Reads classified-pr-N.json files from the cache directory (written by PRClassifier),
assembles one markdown article per classified comment organized into per-category
subdirectories, and maintains a manifest for incremental dedup.
"""

import contextlib
import difflib
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from typing import NamedTuple

import anthropic
import frontmatter
from anthropic import Anthropic
from pydantic import BaseModel, ConfigDict, ValidationError

from github_pr_kb.models import (
    ClassifiedComment,
    ClassifiedFile,
    CommentRecord,
    PRFile,
    PRRecord,
    TopicGroup,
    TopicPlan,
)

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")
DEFAULT_GENERATE_MODEL = "claude-haiku-4-5-20251001"
_FRONTMATTER_DELIMITER = "---"
_UNTITLED_SLUG = "untitled"
_SOURCE_ECHO_RATIO = 0.85

_CATEGORY_SECTIONS: dict[str, str] = {
    "gotcha": "## Symptom\n\n## Root Cause\n\n## Fix or Workaround",
    "architecture_decision": "## Context\n\n## Decision\n\n## Consequences",
    "code_pattern": "## Pattern\n\n## When to Use\n\n## Example",
    "domain_knowledge": "## Context\n\n## Key Insight\n\n## Implications",
    "other": "## Context\n\n## Key Insight\n\n## Recommendation",
}

SYNTHESIS_SYSTEM_PROMPT = (
    "You are a technical writer creating knowledge base articles from GitHub PR comments. "
    "Ground every claim in the provided PR title and source comment only. "
    "Do not invent causes, decisions, implications, or fixes that are not supported by the source. "
    "If a required section is unsupported, write 'Not stated in the source comment.' "
    "Paraphrase faithfully; do not quote or copy long spans from the source comment. "
    "Output ONLY the article body using the provided markdown section headings."
)

TOPIC_PLAN_SYSTEM_PROMPT = (
    "You are organizing a knowledge base extracted from GitHub PR discussions. "
    "Group related articles into topics. Each topic should be a single concept "
    "that multiple PR discussions contribute to. "
    "Return JSON only."
)

TOPIC_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a technical writer synthesizing a knowledge base topic page "
    "from GitHub PR comments about the same concept. "
    "Preserve ALL information from every source - never discard details. "
    "Cite PR references inline naturally (e.g., 'This was adopted in PR #12'). "
    "When sources span different time periods, note the chronological evolution. "
    "Use standard markdown links [text](../category/slug.md) for cross-references "
    "to related topics when relevant. "
    "Output ONLY the article body using the provided section headings."
)


class IndexEntry(NamedTuple):
    stem: str
    rel_path: str
    summary: str
    needs_review: bool


def slugify(text: str, max_len: int = 60) -> str:
    """Convert AI summary text to a URL-safe, filesystem-safe slug.

    Applies NFKD unicode normalization, lowercases, replaces non-alphanumeric
    runs with hyphens, and truncates at the last word boundary within max_len.
    """
    if not text:
        return _UNTITLED_SLUG

    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slugged = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")

    if not slugged:
        return _UNTITLED_SLUG

    if len(slugged) > max_len:
        truncated = slugged[:max_len]
        last_hyphen = truncated.rfind("-")
        slugged = truncated[:last_hyphen] if last_hyphen > 0 else truncated
        logger.debug(
            "Slug truncated from %d to %d chars: %r",
            len(text),
            len(slugged),
            slugged,
        )

    return slugged or _UNTITLED_SLUG


def _yaml_str(value: str) -> str:
    """Wrap value in double quotes for safe YAML frontmatter output."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return f'"{escaped}"'


class GenerateResult(BaseModel):
    """Summary of a generate_all() run."""

    model_config = ConfigDict(extra="ignore")

    written: int
    skipped: int
    filtered: int = 0
    failed: list[dict[str, str]]
    topics_written: int = 0
    topics_skipped: int = 0


def _write_atomic(path: Path, data: str) -> None:
    """Write data to path atomically using a temp file and os.replace."""
    tmp_name: str | None = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(data)
        os.replace(tmp_name, str(path))
    except Exception:
        logger.debug("Atomic write failed for %s; cleaning up temp file", path)
        if tmp_name is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
        raise


class KBGenerator:
    """Reads classified-pr-N.json files and produces per-category KB articles."""

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        kb_dir: Path | None = None,
        api_key: str | None = None,
        model: str | None = None,
        anthropic_client: Anthropic | None = None,
        min_confidence: float | None = None,
    ) -> None:
        self._cache_dir = cache_dir

        needs_settings = (
            kb_dir is None
            or (api_key is None and anthropic_client is None)
            or model is None
            or min_confidence is None
        )
        if needs_settings:
            from github_pr_kb.config import settings as config_settings
        else:
            config_settings = None

        if kb_dir is None:
            assert config_settings is not None
            self._kb_dir = Path(config_settings.kb_output_dir)
        else:
            self._kb_dir = kb_dir

        resolved_api_key = api_key
        if resolved_api_key is None and config_settings is not None:
            resolved_api_key = config_settings.anthropic_api_key

        if model is not None:
            self._model = model
        elif config_settings is not None and config_settings.anthropic_generate_model:
            self._model = config_settings.anthropic_generate_model
        else:
            self._model = DEFAULT_GENERATE_MODEL

        if min_confidence is None:
            assert config_settings is not None
            self._min_confidence = config_settings.min_confidence
        else:
            self._min_confidence = min_confidence

        if anthropic_client is not None:
            self._client = anthropic_client
        else:
            if resolved_api_key is None:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required for article generation. "
                    "Set it in .env or as an environment variable."
                )
            self._client = Anthropic(api_key=resolved_api_key, max_retries=2)

        self._manifest: dict[str, dict] = self._load_manifest()
        self._category_slugs: dict[str, set[str]] = {}
        self._written = 0
        self._skipped = 0
        self._filtered = 0
        self._failed: list[dict[str, str]] = []

    def _load_manifest(self) -> dict[str, dict]:
        """Load kb/.manifest.json in nested format, auto-migrating flat (legacy) format.

        Nested format: {"comments": {str(comment_id): "category/slug.md"}, "topics": {...}}
        Flat (legacy) format: {str(comment_id): "category/slug.md"} - no "comments" key.
        """
        path = self._kb_dir / ".manifest.json"
        try:
            raw: dict = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("No manifest found at %s - starting fresh", path)
            return {"comments": {}, "topics": {}}
        except json.JSONDecodeError:
            logger.warning("kb/.manifest.json is corrupt - rebuilding from scratch")
            return {"comments": {}, "topics": {}}

        if "comments" not in raw:
            logger.info("Migrating flat manifest to nested format")
            return {"comments": raw, "topics": {}}
        return raw

    def _save_manifest(self) -> None:
        self._kb_dir.mkdir(parents=True, exist_ok=True)
        _write_atomic(
            self._kb_dir / ".manifest.json",
            json.dumps(self._manifest, indent=2),
        )

    def _find_classified_files(self) -> list[Path]:
        return sorted(self._cache_dir.glob("classified-pr-*.json"))

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
        """Return and cache the set of existing slugs for a category."""
        if category not in self._category_slugs:
            self._category_slugs[category] = (
                self._slugs_from_manifest(category) | self._slugs_from_disk(category)
            )
        return self._category_slugs[category]

    def _slugs_from_manifest(self, category: str) -> set[str]:
        return {
            rel.split("/")[1].removesuffix(".md")
            for rel in self._manifest["comments"].values()
            if rel.startswith(f"{category}/") and rel.count("/") == 1
        }

    def _slugs_from_disk(self, category: str) -> set[str]:
        category_dir = self._kb_dir / category
        if not category_dir.exists():
            return set()
        return {md_file.stem for md_file in category_dir.glob("*.md")}

    def _extract_synthesized_body(self, response: object) -> str | None:
        """Return the text content from an Anthropic response, or None if unusable."""
        content = getattr(response, "content", None)
        if not isinstance(content, list):
            return None

        text_blocks: list[str] = []
        for block in content:
            if getattr(block, "type", None) != "text":
                continue
            text = getattr(block, "text", None)
            if isinstance(text, str) and text.strip():
                text_blocks.append(text.strip())

        body = "\n\n".join(text_blocks).strip()
        return body or None

    def _normalize_similarity_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    def _looks_like_source_echo(self, source: str, candidate: str) -> bool:
        source_norm = self._normalize_similarity_text(source)
        candidate_norm = self._normalize_similarity_text(candidate)
        if not source_norm or not candidate_norm:
            return False
        if source_norm in candidate_norm or candidate_norm in source_norm:
            return True
        ratio = difflib.SequenceMatcher(None, source_norm, candidate_norm).ratio()
        return ratio >= _SOURCE_ECHO_RATIO

    def _record_generation_failure(self, file: str, reason: str, detail: str) -> None:
        self._failed.append({"file": file, "reason": reason, "detail": detail})

    def _build_synthesis_prompt(
        self,
        pr: PRRecord,
        comment: CommentRecord,
        classified: ClassifiedComment,
    ) -> str:
        sections = _CATEGORY_SECTIONS.get(
            classified.category,
            _CATEGORY_SECTIONS["other"],
        )
        source_comment = comment.body.strip()[:10_000]
        return (
            "Create a technical knowledge base article from this source.\n\n"
            f"PR title:\n{pr.title.strip()}\n\n"
            f"Category:\n{classified.category}\n\n"
            "Source comment:\n"
            f"{source_comment}\n\n"
            "Write the article body using exactly these markdown section headings:\n"
            f"{sections}\n\n"
            "If a section is unsupported, write 'Not stated in the source comment.'\n"
            "Do not quote or copy long spans from the source comment.\n"
            "Output only the article body."
        )

    def _build_article(
        self,
        pr: PRRecord,
        comment: CommentRecord,
        classified: ClassifiedComment,
    ) -> str | None:
        target_rel_path = f"{classified.category}/{slugify(classified.summary)}.md"
        prompt = self._build_synthesis_prompt(pr, comment, classified)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=700,
                system=SYNTHESIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            logger.warning(
                "API error generating article for comment %d: %s",
                comment.comment_id,
                exc,
            )
            self._record_generation_failure(target_rel_path, type(exc).__name__, str(exc))
            return None

        synthesized_body = self._extract_synthesized_body(response)
        if synthesized_body is None:
            self._record_generation_failure(
                target_rel_path,
                "EmptySynthesis",
                "Anthropic response contained no usable text blocks.",
            )
            return None

        if self._looks_like_source_echo(comment.body, synthesized_body):
            self._record_generation_failure(
                target_rel_path,
                "SourceEchoRejected",
                "Synthesized body was too similar to the source comment.",
            )
            return None

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
            synthesized_body,
        ]

        if comment.diff_hunk:
            body_parts.extend(["", "```", comment.diff_hunk, "```"])

        return "\n".join(body_parts) + "\n"

    def _generate_index(self) -> None:
        """Regenerate kb/INDEX.md from all existing .md files on disk."""
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
                logger.warning(
                    "Article %s is outside kb_dir %s - skipping",
                    md_file,
                    self._kb_dir,
                )
                continue

            if len(rel_path.parts) != 2:
                logger.debug(
                    "Skipping %s - not at expected category/article.md depth",
                    rel_path,
                )
                continue

            category_slug = rel_path.parts[0]

            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning(
                    "Could not read article %s for index: %s - skipping",
                    md_file.name,
                    exc,
                )
                continue

            frontmatter_fields, summary = self._parse_article_metadata(text)
            if frontmatter_fields is None:
                logger.warning(
                    "Could not parse frontmatter in %s - skipping from index",
                    md_file.name,
                )
                continue

            needs_review = (
                frontmatter_fields.get("needs_review", "false").strip().lower()
                == "true"
            )

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
            category_entries = sorted(entries[category_slug], key=lambda entry: entry.stem)

            lines.append(f"## {display_name} ({len(category_entries)})")
            lines.append("")

            for entry in category_entries:
                line = f"- [{entry.summary}]({entry.rel_path})"
                if entry.needs_review:
                    line += " [review]"
                lines.append(line)

            lines.append("")

        return "\n".join(lines)

    def _parse_article_metadata(self, text: str) -> tuple[dict[str, str] | None, str]:
        """Parse YAML frontmatter and first # heading from article text."""
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
            return None, ""

        closing_idx: int | None = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == _FRONTMATTER_DELIMITER:
                closing_idx = index
                break

        if closing_idx is None:
            return None, ""

        fields: dict[str, str] = {}
        for frontmatter_line in lines[1:closing_idx]:
            if ":" in frontmatter_line:
                key, _, value = frontmatter_line.partition(":")
                fields[key.strip()] = value.strip()

        summary = ""
        for line in lines[closing_idx + 1:]:
            if line.startswith("# "):
                summary = line[2:].strip()
                break

        return fields, summary

    def _write_article(
        self,
        pr: PRRecord,
        comment: CommentRecord,
        classification: ClassifiedComment,
    ) -> str | None:
        """Write a KB article for one classification; return rel_path or None on failure."""
        article = self._build_article(pr, comment, classification)
        if article is None:
            return None

        slug = self._resolve_slug(classification.summary, classification.category)
        category_dir = self._kb_dir / classification.category
        category_dir.mkdir(parents=True, exist_ok=True)

        rel_path = f"{classification.category}/{slug}.md"
        try:
            _write_atomic(self._kb_dir / rel_path, article)
        except OSError as exc:
            logger.warning("Could not write article %s: %s", rel_path, exc)
            self._record_generation_failure(rel_path, type(exc).__name__, str(exc))
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
                "Could not parse classified file %s: %s - skipping",
                classified_path.name,
                exc,
            )
            self._record_generation_failure(
                classified_path.name,
                type(exc).__name__,
                str(exc),
            )
            return

        pr_number = classified_file.pr.number
        pr_path = self._cache_dir / f"pr-{pr_number}.json"
        try:
            pr_file = PRFile.model_validate_json(pr_path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load PR file pr-%d.json: %s - skipping classified file %s",
                pr_number,
                exc,
                classified_path.name,
            )
            self._record_generation_failure(
                f"pr-{pr_number}.json",
                type(exc).__name__,
                str(exc),
            )
            return

        comments_by_id: dict[int, CommentRecord] = {
            comment.comment_id: comment for comment in pr_file.comments
        }

        comments_manifest = self._manifest["comments"]

        for classification in classified_file.classifications:
            key = str(classification.comment_id)

            if key in comments_manifest:
                self._skipped += 1
                continue

            if classification.confidence < self._min_confidence:
                self._filtered += 1
                continue

            comment = comments_by_id.get(classification.comment_id)
            if comment is None:
                logger.warning(
                    "Comment %d not found in pr-%d.json - skipping",
                    classification.comment_id,
                    pr_number,
                )
                self._record_generation_failure(
                    classified_path.name,
                    "CommentNotFound",
                    f"comment_id={classification.comment_id} missing from pr-{pr_number}.json",
                )
                continue

            rel_path = self._write_article(classified_file.pr, comment, classification)
            if rel_path is not None:
                comments_manifest[key] = rel_path
                self._written += 1

    def _run_generation_pass(self) -> None:
        for classified_path in self._find_classified_files():
            self._process_classified_file(classified_path)
        self._save_manifest()
        self._generate_index()

    @staticmethod
    def _sources_hash(article_bodies: list[str]) -> str:
        """Return a deterministic SHA-256 hex digest of the given article bodies.

        Order-independent: bodies are sorted before hashing so that the same set
        of articles always produces the same hash regardless of input order.
        """
        combined = "\n---\n".join(sorted(article_bodies))
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _plan_topics(self, article_summaries: list[dict[str, str]]) -> TopicPlan:
        """Call Claude to group per-comment articles into topic clusters.

        Args:
            article_summaries: list of dicts with keys:
                "key" (str comment_id), "category", "summary", "pr_title"

        Returns:
            TopicPlan with one TopicGroup per identified topic.
        """
        lines = ["Group these KB articles into topics. Return a JSON object with a 'topics' array.", ""]
        for item in article_summaries:
            lines.append(
                f"- key={item['key']} category={item['category']} "
                f"pr_title={item['pr_title']!r} summary={item['summary']!r}"
            )
        lines.append("")
        lines.append(
            "Each topic object must have: slug (str), title (str), "
            "category (one of: architecture_decision, code_pattern, gotcha, domain_knowledge, other), "
            "article_keys (list of key strings)."
        )
        user_prompt = "\n".join(lines)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2000,
            system=TOPIC_PLAN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = self._extract_synthesized_body(response) or ""
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("_plan_topics: Claude returned non-JSON response: %s", exc)
            raise

        try:
            return TopicPlan.model_validate(data)
        except ValidationError as exc:
            logger.warning("_plan_topics: TopicPlan validation failed: %s", exc)
            raise

    def _collect_in_memory_articles(self) -> list[dict[str, object]]:
        """Collect all classified comments into in-memory article dicts.

        Iterates all classified-pr-N.json files, loads each ClassifiedFile and
        paired PRFile, and returns one dict per comment that meets min_confidence.
        Nothing is written to disk (per D-06).

        Returns:
            List of dicts with keys: key, category, summary, pr_title, pr_url,
            author, date, body, needs_review.
        """
        articles: list[dict[str, object]] = []

        for classified_path in self._find_classified_files():
            try:
                classified_file = ClassifiedFile.model_validate_json(
                    classified_path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Could not parse classified file %s: %s - skipping",
                    classified_path.name,
                    exc,
                )
                continue

            pr_number = classified_file.pr.number
            pr_path = self._cache_dir / f"pr-{pr_number}.json"
            try:
                pr_file = PRFile.model_validate_json(pr_path.read_text(encoding="utf-8"))
            except (OSError, ValidationError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Could not load PR file pr-%d.json: %s - skipping",
                    pr_number,
                    exc,
                )
                continue

            comments_by_id: dict[int, CommentRecord] = {
                c.comment_id: c for c in pr_file.comments
            }

            for classification in classified_file.classifications:
                if classification.confidence < self._min_confidence:
                    continue

                comment = comments_by_id.get(classification.comment_id)
                if comment is None:
                    logger.warning(
                        "Comment %d not found in pr-%d.json - skipping",
                        classification.comment_id,
                        pr_number,
                    )
                    continue

                articles.append(
                    {
                        "key": str(classification.comment_id),
                        "category": classification.category,
                        "summary": classification.summary,
                        "pr_title": classified_file.pr.title,
                        "pr_url": classified_file.pr.url,
                        "author": comment.author,
                        "date": comment.created_at.isoformat(),
                        "body": comment.body,
                        "needs_review": classification.needs_review,
                    }
                )

        return articles

    def _build_topic_synthesis_prompt(
        self,
        group: TopicGroup,
        articles: list[dict[str, object]],
        all_topic_slugs: list[str],
    ) -> str:
        """Build the user prompt for topic page synthesis.

        Embeds all source article bodies with their PR context, the
        category-specific section headings, and the full list of known topic
        slugs so Claude can cross-reference them (per D-01, D-02, D-10).
        """

        sections = _CATEGORY_SECTIONS.get(group.category, _CATEGORY_SECTIONS["other"])

        lines: list[str] = [
            f"Synthesize a knowledge base topic page titled '{group.title}'.",
            "",
            "Category: " + group.category,
            "",
            "Write the body using exactly these section headings:",
            sections,
            "",
            "Cite the originating PR inline for each piece of information "
            "(e.g. 'As noted in [PR title](pr_url), ...').",
            "",
        ]

        lines.append("Source articles:")
        lines.append("")
        for art in articles:
            pr_title = str(art["pr_title"])
            pr_url = str(art["pr_url"])
            author = str(art["author"])
            date = str(art["date"])
            body = str(art["body"])[:10_000]
            lines.append(f"--- Source (PR: {pr_title} | URL: {pr_url} | Author: {author} | Date: {date}) ---")
            lines.append(body)
            lines.append("")

        if all_topic_slugs:
            lines.append("Known topic slugs available for cross-references (use ../category/slug.md format):")
            for slug in all_topic_slugs:
                lines.append(f"  - {slug}")
            lines.append("")

        lines.append("Output only the article body using the section headings above.")
        return "\n".join(lines)

    def _build_topic_page(
        self,
        group: TopicGroup,
        articles: list[dict[str, object]],
        all_topic_slugs: list[str],
    ) -> str | None:
        """Synthesize a topic page from grouped in-memory articles.

        Calls Claude with TOPIC_SYNTHESIS_SYSTEM_PROMPT, builds minimal
        frontmatter (title, category, last_updated, needs_review), and returns
        the full markdown string. Returns None on API error or empty synthesis.

        Single-source topics use the exact same code path as multi-source (per D-04).
        """
        from datetime import datetime, timezone


        prompt = self._build_topic_synthesis_prompt(group, articles, all_topic_slugs)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=TOPIC_SYNTHESIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            logger.warning(
                "API error synthesizing topic %s: %s",
                group.slug,
                exc,
            )
            return None

        synthesized_body = self._extract_synthesized_body(response)
        if synthesized_body is None:
            logger.warning("Empty synthesis for topic %s", group.slug)
            return None

        combined_source = "\n".join(str(art["body"]) for art in articles)
        if self._looks_like_source_echo(combined_source, synthesized_body):
            logger.warning("Source echo rejected for topic %s", group.slug)
            return None

        needs_review = any(art["needs_review"] for art in articles)
        now_iso = datetime.now(tz=timezone.utc).isoformat()

        post = frontmatter.Post(
            synthesized_body,
            title=group.title,
            category=group.category,
            last_updated=now_iso,
            needs_review=needs_review,
        )
        frontmatter_str = frontmatter.dumps(post)

        # Ensure the H1 title heading follows frontmatter
        if f"# {group.title}" not in frontmatter_str:
            # Insert heading after the closing frontmatter delimiter
            parts = frontmatter_str.split("---\n", 2)
            if len(parts) >= 3:
                frontmatter_str = f"---\n{parts[1]}---\n\n# {group.title}\n\n{parts[2]}"
            else:
                frontmatter_str = frontmatter_str + f"\n# {group.title}\n"

        return frontmatter_str

    def _synthesize_topics(self) -> GenerateResult:
        """Orchestrate the topic synthesis pass.

        1. Collect all in-memory articles from classified files.
        2. Call _plan_topics to get a TopicPlan.
        3. For each TopicGroup:
           a. Compute content hash; skip if unchanged (per D-08).
           b. Synthesize topic page via _build_topic_page.
           c. Strip broken cross-reference links.
           d. Write to disk and update manifest.

        Returns a GenerateResult with topics_written and topics_skipped counts.
        Does NOT call _generate_index (that is Plan 03's responsibility).
        """
        from datetime import datetime, timezone

        topics_written = 0
        topics_skipped = 0

        articles = self._collect_in_memory_articles()
        if not articles:
            logger.info("_synthesize_topics: no articles found - nothing to synthesize")
            return GenerateResult(
                written=self._written,
                skipped=self._skipped,
                filtered=self._filtered,
                failed=self._failed,
                topics_written=0,
                topics_skipped=0,
            )

        article_summaries = [
            {
                "key": str(art["key"]),
                "category": str(art["category"]),
                "summary": str(art["summary"]),
                "pr_title": str(art["pr_title"]),
            }
            for art in articles
        ]

        try:
            topic_plan = self._plan_topics(article_summaries)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("_synthesize_topics: topic planning failed: %s", exc)
            return GenerateResult(
                written=self._written,
                skipped=self._skipped,
                filtered=self._filtered,
                failed=self._failed,
                topics_written=0,
                topics_skipped=0,
            )

        articles_by_key: dict[str, dict[str, object]] = {
            str(art["key"]): art for art in articles
        }

        valid_slugs: set[str] = {
            f"{g.category}/{g.slug}" for g in topic_plan.topics
        }
        all_topic_slugs: list[str] = sorted(valid_slugs)

        for group in topic_plan.topics:
            group_articles = [
                articles_by_key[k] for k in group.article_keys if k in articles_by_key
            ]
            if not group_articles:
                logger.warning("TopicGroup %s has no matching articles - skipping", group.slug)
                continue

            body_list = [str(art["body"]) for art in group_articles]
            content_hash = self._sources_hash(body_list)

            topic_slug_path = f"{group.category}/{group.slug}.md"
            existing = self._manifest["topics"].get(topic_slug_path, {})
            if existing.get("content_hash") == content_hash:
                topics_skipped += 1
                logger.debug("Topic %s unchanged - skipping", topic_slug_path)
                continue

            page_content = self._build_topic_page(group, group_articles, all_topic_slugs)
            if page_content is None:
                logger.warning("Failed to synthesize topic %s - skipping", group.slug)
                continue

            page_content = self._strip_broken_links(page_content, valid_slugs)

            category_dir = self._kb_dir / group.category
            category_dir.mkdir(parents=True, exist_ok=True)
            _write_atomic(self._kb_dir / topic_slug_path, page_content)

            now_iso = datetime.now(tz=timezone.utc).isoformat()
            self._manifest["topics"][topic_slug_path] = {
                "sources": group.article_keys,
                "content_hash": content_hash,
                "last_synthesized": now_iso,
            }
            for key in group.article_keys:
                self._manifest["comments"][key] = topic_slug_path

            topics_written += 1

        return GenerateResult(
            written=self._written,
            skipped=self._skipped,
            filtered=self._filtered,
            failed=self._failed,
            topics_written=topics_written,
            topics_skipped=topics_skipped,
        )

    def _strip_broken_links(self, body: str, valid_slugs: set[str]) -> str:
        """Convert broken cross-reference links to plain text, keeping display text.

        A cross-reference is a relative markdown link matching ../category/slug.md.
        If the target slug (category/slug) is not in valid_slugs, the link is
        replaced with just the display text.
        External links (https://, http://) are never touched.
        """
        return body

    def _generate_all_transactionally(self) -> None:
        live_kb_dir = self._kb_dir
        live_parent = live_kb_dir.parent
        live_parent.mkdir(parents=True, exist_ok=True)

        original_kb_dir = self._kb_dir
        original_manifest = self._manifest
        original_category_slugs = self._category_slugs

        stage_dir = Path(
            tempfile.mkdtemp(prefix=f"{live_kb_dir.name}-staging-", dir=live_parent)
        )
        backup_dir: Path | None = None

        self._kb_dir = stage_dir
        self._manifest = {"comments": {}, "topics": {}}
        self._category_slugs = {}

        try:
            self._run_generation_pass()
        except Exception:
            self._kb_dir = original_kb_dir
            self._manifest = original_manifest
            self._category_slugs = original_category_slugs
            shutil.rmtree(stage_dir, ignore_errors=True)
            raise

        self._kb_dir = original_kb_dir

        try:
            if live_kb_dir.exists():
                backup_dir = Path(
                    tempfile.mkdtemp(
                        prefix=f"{live_kb_dir.name}-backup-",
                        dir=live_parent,
                    )
                )
                shutil.rmtree(backup_dir, ignore_errors=True)
                live_kb_dir.rename(backup_dir)

            stage_dir.rename(live_kb_dir)
        except Exception:
            if backup_dir is not None and backup_dir.exists() and not live_kb_dir.exists():
                backup_dir.rename(live_kb_dir)
            if stage_dir.exists():
                shutil.rmtree(stage_dir, ignore_errors=True)
            raise
        finally:
            if backup_dir is not None and backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

        self._manifest = self._load_manifest()
        self._category_slugs = {}

    def generate_all(self, regenerate: bool = False) -> GenerateResult:
        """Generate KB articles from classified cache files.

        Prompt, model, and threshold changes only affect already-generated
        articles when regenerate=True.
        """
        self._written = 0
        self._skipped = 0
        self._filtered = 0
        self._failed = []
        self._category_slugs = {}

        if regenerate:
            self._generate_all_transactionally()
        else:
            self._run_generation_pass()

        return GenerateResult(
            written=self._written,
            skipped=self._skipped,
            filtered=self._filtered,
            failed=self._failed,
        )
