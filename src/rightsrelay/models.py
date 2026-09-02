from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AuthorizationStatus = Literal["PENDING", "CLEARED_LIMITED", "BLOCKED", "CLEARED"]
DecisionStatus = Literal["BLOCKED", "CLEARED", "CLEARED_LIMITED"]


class UseAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    campaign_id: str
    channels: list[str]
    paid: bool
    territories: list[str]
    valid_from: date
    expires_on: date
    status: AuthorizationStatus
    blocking_reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    acp_job_id: str | None = None
    x402_tx: str | None = None
    version: int = Field(ge=1)
    last_actor: str


class ReleaseAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str
    paid: bool
    territories: list[str]
    date: date
    campaign_id: str
    asset_id: str


class GateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    status: DecisionStatus
    reasons: list[str]
