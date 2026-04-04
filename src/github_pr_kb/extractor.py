"""Extracts PR comments from GitHub API using PyGithub."""
import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from github import Auth, Github
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment

from github_pr_kb.config import settings
from github_pr_kb.models import CommentRecord, PRFile, PRRecord

# Per D-11, D-12: Known CI/automation bots to skip
SKIP_BOT_LOGINS = frozenset({
    "dependabot[bot]", "dependabot",
    "github-actions[bot]", "github-actions",
    "codecov[bot]", "codecov",
    "renovate[bot]", "renovate",
    "auto-labeler[bot]",
    "stale[bot]",
})

# Filters "LGTM", "+1", emoji-only etc. — requires at least one 5+ char word
_SUBSTANTIVE_RE = re.compile(r"[a-zA-Z]{5,}")

DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")

REACTION_KEYS = ["+1", "-1", "laugh", "hooray", "confused", "heart", "rocket", "eyes"]


def is_noise(login: str, body: str) -> bool:
    """Return True if the comment should be filtered out as noise.

    Filters:
    - Known CI/automation bot accounts (dependabot, codecov, etc.)
    - Comments with no substantive text (emoji-only, single short words like LGTM)
    """
    if login in SKIP_BOT_LOGINS:
        return True
    if not _SUBSTANTIVE_RE.search(body):
        return True
    return False


def _extract_reactions(raw_reactions: Mapping[str, int]) -> dict[str, int]:
    """Extract non-zero reaction counts from a reactions dict.

    Accepts a dict-like object (from mocks or PyGithub's reactions property).
    Returns only non-zero counts to keep JSON compact.
    """
    if not raw_reactions:
        return {}
    counts = {k: raw_reactions.get(k, 0) for k in REACTION_KEYS}
    return {k: v for k, v in counts.items() if v > 0}


def _ensure_tz_aware(dt: datetime) -> datetime:
    """Coerce a naive datetime to UTC; return tz-aware datetimes unchanged.

    PyGithub always returns tz-aware datetimes. Callers may pass naive datetimes
    (e.g. datetime.now()). We assume UTC for naive inputs rather than crash with
    a TypeError on comparison against pr.updated_at.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _comment_to_record(
    c: Union[PullRequestComment, IssueComment],
    comment_type: str,
    *,
    file_path: Optional[str] = None,
    diff_hunk: Optional[str] = None,
) -> Optional[CommentRecord]:
    """Build a CommentRecord from a PyGithub comment, or return None if noise."""
    login = c.user.login if c.user is not None else "[deleted]"
    if is_noise(login, c.body):
        return None
    return CommentRecord(
        comment_id=c.id,
        comment_type=comment_type,
        author=login,
        body=c.body,
        created_at=c.created_at,
        url=c.html_url,
        file_path=file_path,
        diff_hunk=diff_hunk,
        reactions=_extract_reactions(c.reactions),
    )


class GitHubExtractor:
    """Authenticates with GitHub via PAT and extracts PR comments into per-PR JSON cache files."""

    def __init__(self, repo_name: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        client = Github(auth=Auth.Token(settings.github_token))
        self.repo = client.get_repo(repo_name)

    def _collect_comments(self, pr: PullRequest) -> list[CommentRecord]:
        """Collect all non-noise review and issue comments for a PR."""
        comments: list[CommentRecord] = []
        for c in pr.get_review_comments():
            record = _comment_to_record(c, "review", file_path=c.path, diff_hunk=c.diff_hunk)
            if record:
                comments.append(record)
        for c in pr.get_issue_comments():
            record = _comment_to_record(c, "issue")
            if record:
                comments.append(record)
        return comments

    def _write_cache(self, pr: PullRequest, comments: list[CommentRecord]) -> Path:
        """Build a PRFile from a PR and its comments, then write it to the cache directory."""
        pr_record = PRRecord(
            number=pr.number,
            title=pr.title,
            body=pr.body,
            state=pr.state,
            url=pr.html_url,
        )
        pr_file = PRFile(
            pr=pr_record,
            comments=comments,
            extracted_at=datetime.now(timezone.utc),
        )
        cache_path = self.cache_dir / f"pr-{pr.number}.json"
        cache_path.write_text(
            json.dumps(pr_file.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return cache_path

    def extract(
        self,
        state: str = "all",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[Path]:
        """Extract PRs with optional state/date filters and write per-PR JSON cache files.

        Args:
            state: PR state to filter by: "open", "closed", or "all".
            since: Only include PRs updated at or after this datetime (uses updated_at).
                   PRs sorted desc by updated_at; stops iteration when past this boundary.
                   Naive datetimes are assumed to be UTC.
            until: Only include PRs updated at or before this datetime (skips, not stops).
                   Naive datetimes are assumed to be UTC.

        Returns:
            List of Paths for cache files written.
        """
        if since is not None:
            since = _ensure_tz_aware(since)
        if until is not None:
            until = _ensure_tz_aware(until)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        written_paths: list[Path] = []

        pulls = self.repo.get_pulls(state=state, sort="updated", direction="desc")

        for pr in pulls:
            # Early-stop: PRs are sorted desc by updated_at.
            # Once we see a PR older than since, all remaining are older too.
            if since is not None and pr.updated_at < since:
                break

            # Skip PRs updated after the until boundary (but don't stop — more may follow).
            if until is not None and pr.updated_at > until:
                continue

            written_paths.append(self._write_cache(pr, self._collect_comments(pr)))

        return written_paths
