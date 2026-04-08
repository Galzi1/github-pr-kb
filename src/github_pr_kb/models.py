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


# Phase 4: Classification types (CLASS-01, CLASS-02, CLASS-04)

CategoryLiteral = Literal[
    "architecture_decision", "code_pattern", "gotcha", "domain_knowledge", "other"
]


class ClassifiedComment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    comment_id: int
    category: CategoryLiteral
    confidence: float
    summary: str
    classified_at: datetime
    needs_review: bool  # True when confidence falls below the review threshold (per D-06)


class ClassifiedFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pr: PRRecord
    classifications: list[ClassifiedComment]
    classified_at: datetime
