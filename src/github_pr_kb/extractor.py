"""Extracts PR comments from GitHub API using PyGithub."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from github import Auth, Github

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


def _extract_reactions(raw_reactions) -> dict[str, int]:
    """Extract non-zero reaction counts from a reactions dict.

    Accepts a dict-like object (from mocks or PyGithub's reactions property).
    Returns only non-zero counts to keep JSON compact.
    """
    if not raw_reactions:
        return {}
    return {k: raw_reactions.get(k, 0) for k in REACTION_KEYS if raw_reactions.get(k, 0) > 0}


class GitHubExtractor:
    """Authenticates with GitHub via PAT and extracts PR comments into per-PR JSON cache files."""

    def __init__(self, repo_name: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        client = Github(auth=Auth.Token(settings.github_token))
        self.repo = client.get_repo(repo_name)

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
            until: Only include PRs updated at or before this datetime (skips, not stops).

        Returns:
            List of Paths for cache files written.
        """
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

            comments: list[CommentRecord] = []

            # Review comments (inline on code diffs) — per D-07, D-09
            for c in pr.get_review_comments():
                login = c.user.login if c.user is not None else "[deleted]"
                if is_noise(login, c.body):
                    continue
                comments.append(CommentRecord(
                    comment_id=c.id,
                    comment_type="review",
                    author=login,
                    body=c.body,
                    created_at=c.created_at,
                    url=c.html_url,
                    file_path=c.path,
                    diff_hunk=c.diff_hunk,
                    reactions=_extract_reactions(c.reactions),
                ))

            # Issue comments (PR thread comments) — per D-07, D-09
            for c in pr.get_issue_comments():
                login = c.user.login if c.user is not None else "[deleted]"
                if is_noise(login, c.body):
                    continue
                comments.append(CommentRecord(
                    comment_id=c.id,
                    comment_type="issue",
                    author=login,
                    body=c.body,
                    created_at=c.created_at,
                    url=c.html_url,
                    file_path=None,
                    diff_hunk=None,
                    reactions=_extract_reactions(c.reactions),
                ))

            pr_record = PRRecord(
                number=pr.number,
                title=pr.title,
                body=pr.body,  # may be None — PRRecord.body is Optional[str]
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
            written_paths.append(cache_path)

        return written_paths
