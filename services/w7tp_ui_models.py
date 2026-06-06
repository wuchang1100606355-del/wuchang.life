from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class IntentCompileIn(BaseModel):
    intent: str
    actor: Optional[str] = None
    node: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


class SecurityLintIn(BaseModel):
    intent: Optional[str] = None
    packet: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class StateTransitionIn(BaseModel):
    from_state: Optional[str] = None
    event: str
    packet: dict[str, Any] = Field(default_factory=dict)


class HashSealIn(BaseModel):
    packet: dict[str, Any] = Field(default_factory=dict)
    state: Optional[str] = None
    node: Optional[str] = None
    timestamp: Optional[int] = None
    coordinate: dict[str, Any] = Field(default_factory=dict)


class EvidenceCommitIn(BaseModel):
    packet: dict[str, Any] = Field(default_factory=dict)
    state: Optional[str] = None
    decision: dict[str, Any] = Field(default_factory=dict)
    hash: dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


class IntentCompileOut(BaseModel):
    ok: bool
    packet: dict[str, Any]
    source: str


class SecurityLintOut(BaseModel):
    allowed: bool
    state: str
    bagua: str
    reason: str
    dead_letter: bool
    rules: list[str]


class StateTransitionOut(BaseModel):
    ok: bool
    state: str
    bagua: str
    transition_id: str


class HashSealOut(BaseModel):
    ok: bool
    packet_hash: str
    state_hash: str
    coordinate_hash: str
    ledger_hash: str
    canonical: dict[str, Any]


class EvidenceCommitOut(BaseModel):
    ok: bool
    ledger_path: str
    event_hash: str
    dead_letter_path: Optional[str] = None
    timestamp: str
