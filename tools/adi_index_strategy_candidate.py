#!/usr/bin/env python3
"""Safe candidate interfaces for Absolute Distance Spiral Index (ADI).

The production ADI algorithm is intentionally unspecified.  The disabled
strategy supplies executable fallback behavior, while the deterministic
fixture strategy exists only for fixed conformance vectors.  Neither strategy
changes a coordinate, creates governance facts, commits state, or adjudicates
a total-field decision.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
from typing import Literal, Protocol, TypeAlias, runtime_checkable


ADIStatus: TypeAlias = Literal["NOT_REQUESTED", "HOLD", "CANDIDATE"]
ADI_FORMAL_NAME = "Absolute Distance Spiral Index"
ADI_CHINESE_NAME = "絕對距離螺旋索引"


class ADIContractError(ValueError):
    """Raised when an ADI contract value cannot be represented safely."""

    def __init__(self, reason_code: str, detail: str) -> None:
        """Initialize a stable error that does not echo source data."""
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _canonical_json(value: object) -> str:
    """Serialize deterministic fixture material using the project contract."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ADIContractError(
            "INVALID_ADI_INPUT", "input is not canonical JSON"
        ) from error


def _sha256(value: object) -> str:
    """Return a lowercase SHA-256 digest for canonical fixture material."""
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nonempty(value: str | None) -> bool:
    """Report whether a candidate reference is a non-empty string."""
    return isinstance(value, str) and bool(value.strip())


def _is_versioned_ref(value: str | None) -> bool:
    """Recognize explicit version markers without defining a registry syntax."""
    if not _nonempty(value):
        return False
    assert value is not None
    if "@" in value:
        base, version = value.rsplit("@", 1)
        return bool(base and version)
    marker_index = value.rfind(":v")
    return marker_index > 0 and marker_index + 2 < len(value)


def _is_sha256(value: str | None) -> bool:
    """Recognize one lowercase hexadecimal SHA-256 digest."""

    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True, slots=True)
class ADIInputContract:
    """Complete opaque-reference contract for one optional ADI invocation."""

    requested: bool
    origin_ref: str | None = None
    metric_ref: str | None = None
    topology_ref: str | None = None
    quantization_rule_ref: str | None = None
    tie_break_rule_ref: str | None = None
    strategy_ref: str | None = None
    strategy_version: str | None = None
    source_coordinate_hash: str | None = None
    candidate_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize candidate references without mutating caller input."""
        if not isinstance(self.requested, bool):
            raise ADIContractError("INVALID_ADI_INPUT", "requested must be boolean")
        if isinstance(self.candidate_refs, str):
            raise ADIContractError(
                "INVALID_ADI_INPUT", "candidate_refs must be a sequence"
            )
        normalized = tuple(self.candidate_refs)
        if any(not _nonempty(reference) for reference in normalized):
            raise ADIContractError(
                "INVALID_ADI_INPUT", "candidate_refs contain an empty reference"
            )
        if len(set(normalized)) != len(normalized):
            raise ADIContractError(
                "INVALID_ADI_INPUT", "candidate_refs must be unique"
            )
        if self.source_coordinate_hash is not None and not _is_sha256(
            self.source_coordinate_hash
        ):
            raise ADIContractError(
                "INVALID_ADI_INPUT",
                "source_coordinate_hash must be lowercase SHA-256",
            )
        object.__setattr__(self, "candidate_refs", normalized)

    def is_complete_fixture_contract(self) -> bool:
        """Check that every algorithm-defining input is explicitly versioned."""
        versioned_refs = (
            self.origin_ref,
            self.metric_ref,
            self.topology_ref,
            self.quantization_rule_ref,
            self.tie_break_rule_ref,
            self.strategy_ref,
        )
        return (
            self.requested
            and all(_is_versioned_ref(reference) for reference in versioned_refs)
            and _nonempty(self.strategy_version)
            and _is_sha256(self.source_coordinate_hash)
            and all(_is_versioned_ref(reference) for reference in self.candidate_refs)
        )


@dataclass(frozen=True, slots=True)
class ADIResult:
    """Reference-only ADI result containing no coordinate or authority state."""

    status: ADIStatus
    reason_code: str
    source_coordinate_hash: str | None
    ordered_candidate_refs: tuple[str, ...]
    result_hash: str | None
    TEST_ONLY: bool
    strategy_ref: str | None = None
    strategy_version: str | None = None

    def __post_init__(self) -> None:
        """Normalize output references and validate the deterministic digest."""
        if self.status not in {"NOT_REQUESTED", "HOLD", "CANDIDATE"}:
            raise ADIContractError("INVALID_ADI_RESULT", "unknown result status")
        if not _nonempty(self.reason_code):
            raise ADIContractError("INVALID_ADI_RESULT", "reason_code is required")
        if not isinstance(self.TEST_ONLY, bool):
            raise ADIContractError("INVALID_ADI_RESULT", "TEST_ONLY must be boolean")
        object.__setattr__(self, "ordered_candidate_refs", tuple(self.ordered_candidate_refs))
        if self.result_hash is not None and (
            len(self.result_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.result_hash)
        ):
            raise ADIContractError(
                "INVALID_ADI_RESULT", "result_hash must be lowercase SHA-256"
            )
        if self.status == "CANDIDATE" and (
            self.TEST_ONLY is not True
            or self.reason_code != "ADI_TEST_FIXTURE_RESULT"
            or self.result_hash is None
        ):
            raise ADIContractError(
                "INVALID_ADI_RESULT",
                "candidate ADI output must be a marked deterministic fixture",
            )

    @property
    def test_only(self) -> bool:
        """Expose a conventional lowercase alias for the wire-level flag."""
        return self.TEST_ONLY

    def as_dict(self) -> dict[str, object]:
        """Return a fresh JSON-compatible result representation."""
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "source_coordinate_hash": self.source_coordinate_hash,
            "ordered_candidate_refs": list(self.ordered_candidate_refs),
            "result_hash": self.result_hash,
            "TEST_ONLY": self.TEST_ONLY,
            "strategy_ref": self.strategy_ref,
            "strategy_version": self.strategy_version,
        }


@runtime_checkable
class ADIIndexStrategy(Protocol):
    """Provider-neutral interface for an optional index strategy."""

    @abstractmethod
    def evaluate(self, contract: ADIInputContract) -> ADIResult:
        """Evaluate an immutable ADI input contract."""
        raise RuntimeError("PROTOCOL_INTERFACE_ONLY")


@dataclass(frozen=True, slots=True)
class DisabledADIIndexStrategy:
    """Safe executable fallback used while the ADI algorithm is unconfigured."""

    def evaluate(self, contract: ADIInputContract) -> ADIResult:
        """Return no-op or HOLD without changing downstream candidate state."""
        if not isinstance(contract, ADIInputContract):
            raise ADIContractError(
                "INVALID_ADI_INPUT", "contract must be ADIInputContract"
            )
        if not contract.requested:
            return ADIResult(
                status="NOT_REQUESTED",
                reason_code="ADI_NOT_REQUESTED",
                source_coordinate_hash=contract.source_coordinate_hash,
                ordered_candidate_refs=(),
                result_hash=None,
                TEST_ONLY=False,
                strategy_ref=contract.strategy_ref,
                strategy_version=contract.strategy_version,
            )
        return ADIResult(
            status="HOLD",
            reason_code="HOLD_ADI_NOT_CONFIGURED",
            source_coordinate_hash=contract.source_coordinate_hash,
            ordered_candidate_refs=(),
            result_hash=None,
            TEST_ONLY=False,
            strategy_ref=contract.strategy_ref,
            strategy_version=contract.strategy_version,
        )


@dataclass(frozen=True, slots=True)
class DeterministicFixtureADIIndexStrategy:
    """Fixed conformance-vector strategy that is never a production ADI."""

    fixture_profile_ref: str = "adi-fixture-profile:v0.1"

    def __post_init__(self) -> None:
        """Require an explicit versioned fixture profile reference."""
        if not _is_versioned_ref(self.fixture_profile_ref):
            raise ADIContractError(
                "INVALID_ADI_INPUT", "fixture_profile_ref must be versioned"
            )

    def evaluate(self, contract: ADIInputContract) -> ADIResult:
        """Order fixed reference vectors and bind them to a deterministic hash."""
        if not isinstance(contract, ADIInputContract):
            raise ADIContractError(
                "INVALID_ADI_INPUT", "contract must be ADIInputContract"
            )
        if not contract.requested:
            return ADIResult(
                status="NOT_REQUESTED",
                reason_code="ADI_NOT_REQUESTED",
                source_coordinate_hash=contract.source_coordinate_hash,
                ordered_candidate_refs=(),
                result_hash=None,
                TEST_ONLY=True,
                strategy_ref=contract.strategy_ref,
                strategy_version=contract.strategy_version,
            )
        if not contract.is_complete_fixture_contract():
            return ADIResult(
                status="HOLD",
                reason_code="HOLD_ADI_NOT_CONFIGURED",
                source_coordinate_hash=contract.source_coordinate_hash,
                ordered_candidate_refs=(),
                result_hash=None,
                TEST_ONLY=True,
                strategy_ref=contract.strategy_ref,
                strategy_version=contract.strategy_version,
            )

        ordered = tuple(
            sorted(contract.candidate_refs, key=lambda reference: _canonical_json(reference))
        )
        result_material = {
            "fixture_profile_ref": self.fixture_profile_ref,
            "origin_ref": contract.origin_ref,
            "metric_ref": contract.metric_ref,
            "topology_ref": contract.topology_ref,
            "quantization_rule_ref": contract.quantization_rule_ref,
            "tie_break_rule_ref": contract.tie_break_rule_ref,
            "strategy_ref": contract.strategy_ref,
            "strategy_version": contract.strategy_version,
            "source_coordinate_hash": contract.source_coordinate_hash,
            "ordered_candidate_refs": list(ordered),
            "TEST_ONLY": True,
        }
        return ADIResult(
            status="CANDIDATE",
            reason_code="ADI_TEST_FIXTURE_RESULT",
            source_coordinate_hash=contract.source_coordinate_hash,
            ordered_candidate_refs=ordered,
            result_hash=_sha256(result_material),
            TEST_ONLY=True,
            strategy_ref=contract.strategy_ref,
            strategy_version=contract.strategy_version,
        )


def evaluate_adi(
    strategy: ADIIndexStrategy, contract: ADIInputContract
) -> ADIResult:
    """Evaluate an injected strategy without selecting a hidden fallback."""
    return strategy.evaluate(contract)


__all__ = (
    "ADIContractError",
    "ADI_FORMAL_NAME",
    "ADI_CHINESE_NAME",
    "ADIIndexStrategy",
    "ADIInputContract",
    "ADIResult",
    "DeterministicFixtureADIIndexStrategy",
    "DisabledADIIndexStrategy",
    "evaluate_adi",
)
