"""PR and comment data models for github-pr-kb."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class CommentRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")  # forward-compatible with future field additions (per R4)

    comment_id: int
    comment_type: Literal["review", "issue"]  # enforced at validation (per risk review R2)
    author: str  # GitHub login, or "[deleted]"
    body: str
    created_at: datetime
    url: str
    file_path: Optional[str] = None  # review comments only (per D-07)
    diff_hunk: Optional[str] = None  # review comments only (per D-07)
    reactions: dict[str, int] = {}  # safe in Pydantic v2 — model __init__ deep-copies defaults (per A1)


class PRRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")  # forward-compatible with future field additions (per R4)

    number: int
    title: str
    body: Optional[str] = None  # PRs with no description (per pitfall 2)
    state: Literal["open", "closed"]  # enforced at validation (per risk review R2)
    url: str


class PRFile(BaseModel):
    model_config = ConfigDict(extra="ignore")  # forward-compatible with future field additions (per R4)

    pr: PRRecord
    comments: list[CommentRecord]
    extracted_at: datetime
