from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    token: str = Field(min_length=1, max_length=200)


class SourceImport(Input):
    url: str = Field(max_length=2000)
    text: str | None = Field(default=None, min_length=20, max_length=200_000)
    title: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=200)
    published_at: datetime | None = None
    fallback_published_at: datetime | None = None
    event_name: str | None = Field(default=None, max_length=200)
    season: int = Field(default=2026, ge=2026, le=2026)


class CandidateReview(Input):
    legacy_upgrade_id: UUID | None = None
    team_key: Literal["ferrari", "mercedes"] | None = None
    component: str | None = Field(default=None, max_length=60)
    event_name: str | None = Field(default=None, max_length=200)
    observed_at: datetime | None = None
    page: int | None = Field(default=None, ge=1, le=250)
    summary: str | None = Field(default=None, min_length=5, max_length=2000)
    supporting_passage: str | None = Field(default=None, min_length=5, max_length=4000)
    evidence_status: (
        Literal["unverified", "reported", "confirmed", "conflicting"] | None
    ) = None
    representation: Literal["annotation_only", "modeled"] | None = None
    review_notes: str = Field(default="", max_length=4000)
    status: Literal["draft", "approved", "rejected"] = "draft"

    @field_validator(
        "summary", "supporting_passage", "evidence_status", "representation"
    )
    @classmethod
    def required_when_supplied(cls, value):
        if value is None:
            raise ValueError("This field cannot be cleared.")
        return value


class RevisionInput(Input):
    component: str
    parameters: dict[str, float] = Field(default_factory=dict)
    source_ids: list[UUID] = Field(min_length=1, max_length=30)
    uncertainty: str = Field(min_length=10, max_length=4000)


class VersionInput(Input):
    team_key: Literal["ferrari", "mercedes"]
    season: Literal[2026] = 2026
    label: str = Field(min_length=3, max_length=200)
    configuration_event: str = Field(min_length=3, max_length=200)
    configuration_kind: Literal[
        "baseline",
        "evolution",
        "circuit_specific",
        "reversion",
        "no_change",
        "reconstruction",
    ] = "evolution"
    reverts_to_id: UUID | None = None
    as_of: datetime
    evidence_cutoff: datetime
    parent_id: UUID | None = None
    candidate_ids: list[UUID] = Field(default_factory=list, max_length=200)
    revisions: list[RevisionInput] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=4000)

    @field_validator("as_of", "evidence_cutoff")
    @classmethod
    def aware_date(cls, value):
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )


class VisualReview(Input):
    front: bool
    side: bool
    rear: bool
    three_quarter: bool
    reference_urls: list[str] = Field(min_length=1, max_length=20)
    notes: str = Field(min_length=20, max_length=4000)


class Rollback(Input):
    version_id: UUID
    reason: str = Field(min_length=5, max_length=1000)
