"""Classifies PR comments via Claude API with SHA-256 content-hash dedup."""
import contextlib
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from anthropic import Anthropic

from github_pr_kb.models import (
    CategoryLiteral,
    ClassifiedComment,
    ClassifiedFile,
    CommentRecord,
    PRFile,
)

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_REVIEW_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_COMMENT_CHUNK_SIZE = 10_000
LEGACY_FAILURE_SUMMARY = "classification failed"

VALID_CATEGORIES: set[str] = {
    "architecture_decision",
    "code_pattern",
    "gotcha",
    "domain_knowledge",
    "other",
}

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)

SYSTEM_PROMPT = """You are a technical knowledge classifier for GitHub PR comments.

Classify the given comment into exactly one of these 5 categories:
1. architecture_decision — choices about system design, trade-offs, or structural patterns
2. code_pattern — recurring implementation techniques, idioms, or best practices
3. gotcha — warnings, pitfalls, non-obvious behaviors, or things that surprised the author
4. domain_knowledge — business logic, domain-specific rules, or project-specific context
5. other — comments that do not fit any of the above categories

Respond with ONLY a JSON object, no other text, no backticks, no explanation.
The confidence field is a float between 0.0 and 1.0.
The summary field is a single sentence describing the key insight.

Example:
{"category": "gotcha", "confidence": 0.85, "summary": "One line summary"}"""


def body_hash(body: str) -> str:
    """Return the SHA-256 hex digest of the comment body (UTF-8 encoded)."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


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


def _parse_classification_response(text: str) -> dict | None:
    """Extract a JSON object from bare, fenced, or prose-wrapped model output."""
    stripped = text.strip()
    if not stripped:
        return None

    decoder = json.JSONDecoder()
    candidates: list[str] = [stripped]
    candidates.extend(match.group(1).strip() for match in _JSON_FENCE_RE.finditer(stripped))

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    for idx, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None


class PRClassifier:
    """Reads cached PR comment files, classifies via Claude API, deduplicates by SHA-256 hash."""

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        model: str | None = None,
        api_key: str | None = None,
        review_confidence_threshold: float = DEFAULT_REVIEW_CONFIDENCE_THRESHOLD,
        comment_chunk_size: int = DEFAULT_COMMENT_CHUNK_SIZE,
    ) -> None:
        from github_pr_kb.config import settings
        if api_key is None:
            api_key = settings.anthropic_api_key
        if model is None:
            model = settings.anthropic_model or DEFAULT_MODEL
        if api_key is None:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for classification. "
                "Set it in .env or as an environment variable."
            )
        self._client = Anthropic(api_key=api_key, max_retries=2)
        self._cache_dir = cache_dir
        self._model = model
        self._review_confidence_threshold = review_confidence_threshold
        self._comment_chunk_size = comment_chunk_size
        self._index: dict[str, dict] = self._load_index()
        self._classified_count = 0
        self._cache_hit_count = 0
        self._failed_count = 0
        self._review_count = 0

    def _is_legacy_failure_entry(self, cached_entry: dict) -> bool:
        """Return True for stale cache entries that recorded failed classifications."""
        return (
            cached_entry.get("summary") == LEGACY_FAILURE_SUMMARY
            and cached_entry.get("confidence") == 0.0
            and cached_entry.get("category") == "other"
        )

    def _needs_review(self, confidence: float) -> bool:
        """Return True when a classification falls below the review threshold."""
        return confidence < self._review_confidence_threshold

    def _build_api_body(self, body: str) -> str:
        """Preserve the full comment body, chunking only for transport readability."""
        chunks = [
            body[start:start + self._comment_chunk_size]
            for start in range(0, len(body), self._comment_chunk_size)
        ]
        if len(chunks) == 1:
            return body

        formatted_chunks = "\n\n".join(
            (
                f"<comment_chunk index=\"{index}\" total=\"{len(chunks)}\">\n"
                f"{chunk}\n"
                "</comment_chunk>"
            )
            for index, chunk in enumerate(chunks, start=1)
        )
        return (
            "The GitHub PR comment below is split into sequential chunks to preserve the full "
            "body. Read all chunks as one comment before classifying.\n\n"
            f"{formatted_chunks}"
        )

    def _load_index(self) -> dict[str, dict]:
        """Load classification-index.json from cache dir, or return empty dict."""
        index_path = self._cache_dir / "classification-index.json"
        try:
            content = index_path.read_text(encoding="utf-8")
            data: dict[str, dict] = json.loads(content)
            data = {
                key: value
                for key, value in data.items()
                if not self._is_legacy_failure_entry(value)
            }
            logger.debug(
                "Loaded classification index with %d entries (failed entries pruned)",
                len(data),
            )
            return data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.warning(
                "classification-index.json is corrupt, rebuilding from scratch"
            )
            return {}

    def _save_index(self) -> None:
        """Write self._index to classification-index.json atomically."""
        index_path = self._cache_dir / "classification-index.json"
        _write_atomic(index_path, json.dumps(self._index, indent=2, default=str))

    def _classify_comment(self, comment: CommentRecord) -> ClassifiedComment | None:
        """Classify a single comment via Claude API or return cached result."""
        if not comment.body.strip():
            logger.debug("Skipping empty comment %d", comment.comment_id)
            return None

        h = body_hash(comment.body)

        if h in self._index:
            cached = self._index[h]
            logger.debug("Cache hit for comment %d (hash %s)", comment.comment_id, h[:8])
            self._cache_hit_count += 1
            cached_confidence = float(cached.get("confidence", 0.0))
            needs_review = self._needs_review(cached_confidence)
            if needs_review:
                self._review_count += 1
            return ClassifiedComment(
                comment_id=comment.comment_id,
                category=cached["category"],
                confidence=cached_confidence,
                summary=cached.get("summary", ""),
                classified_at=datetime.fromisoformat(cached["classified_at"]),
                needs_review=needs_review,
            )

        api_body = self._build_api_body(comment.body)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=256,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": api_body}],
            )
        except anthropic.APIError as exc:
            logger.warning(
                "API error classifying comment %d: %s", comment.comment_id, exc
            )
            self._failed_count += 1
            return None

        text = response.content[0].text
        result = _parse_classification_response(text)
        if result is None:
            logger.warning(
                "Could not parse classification JSON for comment %d", comment.comment_id
            )
            logger.debug("Raw response text: %s", text)
            self._failed_count += 1
            return None

        raw_category = result.get("category", "other")
        category: CategoryLiteral = raw_category if raw_category in VALID_CATEGORIES else "other"  # type: ignore[assignment]
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
        summary = str(result.get("summary", ""))[:200]
        needs_review = self._needs_review(confidence)

        classified_at = datetime.now(timezone.utc)
        self._index[h] = {
            "category": category,
            "confidence": confidence,
            "summary": summary,
            "classified_at": classified_at.isoformat(),
        }
        self._save_index()

        self._classified_count += 1
        if needs_review:
            self._review_count += 1

        return ClassifiedComment(
            comment_id=comment.comment_id,
            category=category,
            confidence=confidence,
            summary=summary,
            classified_at=classified_at,
            needs_review=needs_review,
        )

    def classify_pr(self, pr_number: int) -> ClassifiedFile:
        """Classify all comments in a cached PR file and write classified-pr-N.json."""
        cache_path = self._cache_dir / f"pr-{pr_number}.json"
        content = cache_path.read_text(encoding="utf-8")
        pr_file = PRFile.model_validate_json(content)

        results: list[ClassifiedComment] = []
        for comment in pr_file.comments:
            classified = self._classify_comment(comment)
            if classified is not None:
                results.append(classified)

        classified_file = ClassifiedFile(
            pr=pr_file.pr,
            classifications=results,
            classified_at=datetime.now(timezone.utc),
        )

        output_path = self._cache_dir / f"classified-pr-{pr_number}.json"
        _write_atomic(
            output_path,
            json.dumps(classified_file.model_dump(mode="json"), indent=2),
        )

        return classified_file

    def classify_all(self) -> list[Path]:
        """Classify all cached PR files and return list of output file paths."""
        pr_files = list(self._cache_dir.glob("pr-*.json"))
        pr_numbers: list[int] = []
        for p in pr_files:
            stem = p.stem  # e.g. "pr-42"
            try:
                pr_numbers.append(int(stem.split("-", 1)[1]))
            except (IndexError, ValueError):
                logger.warning("Unexpected cache file name: %s — skipping", p.name)

        output_paths: list[Path] = []
        for pr_number in pr_numbers:
            try:
                self.classify_pr(pr_number)
                output_paths.append(self._cache_dir / f"classified-pr-{pr_number}.json")
            except FileNotFoundError:
                logger.warning("pr-%d.json not found — skipping", pr_number)

        self.print_summary()
        return output_paths

    def print_summary(self) -> None:
        """Print and log a summary of the classification run."""
        counts = self.get_summary_counts()
        msg = (
            f"Classification complete: {counts['new']} classified, "
            f"{counts['cached']} cache hits, "
            f"{counts['need_review']} need review, "
            f"{counts['failed']} failed"
        )
        print(msg)
        logger.info(msg)

    def get_summary_counts(self) -> dict[str, int]:
        """Return the published classify summary counters for the current run."""
        return {
            "new": self._classified_count,
            "cached": self._cache_hit_count,
            "need_review": self._review_count,
            "failed": self._failed_count,
        }
