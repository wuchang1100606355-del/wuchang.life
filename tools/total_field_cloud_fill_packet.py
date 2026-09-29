"""Build minimal, deidentified cloud-fill request packets."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from tools.total_field.xiaoj_fusion_rules import (
    CLOUD_REQUEST_ALLOWED_KEYS,
    FORBIDDEN_CLOUD_CONTEXT_KEYS,
)


class CloudFillPacketBroker:
    """Total Field broker for deciding whether a cloud fill packet is worth sending."""

    def __init__(self, *, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._candidate_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
        self._invalid_packets: set[str] = set()

    def pull_request(
        self,
        *,
        request_hash: str,
        rule_capsule_hash: str,
        locked_fields: Mapping[str, Any],
        fillable_paths: Sequence[str],
        minimal_context: Mapping[str, Any],
        acceptance_criteria: Mapping[str, Any],
        expected_quality_gain: float,
        cost: float,
        active_cloud_use_threshold: float = 0.0,
        now: float | None = None,
    ) -> dict[str, Any]:
        """Return either a reusable cached candidate or a minimal cloud packet."""

        current_time = time.time() if now is None else now
        cache_key = (request_hash, rule_capsule_hash)
        cached = self._valid_cached_candidate(cache_key, current_time)
        if cached is not None:
            return {
                "should_call_cloud": False,
                "cloud_call": 0,
                "reason": "valid_cached_candidate_reused",
                "cached_candidate": cached,
                "packet": None,
            }

        value = expected_quality_gain - cost
        if not fillable_paths:
            return _no_cloud("no_explicit_fillable_paths")
        if value <= active_cloud_use_threshold:
            return _no_cloud("expected_quality_gain_not_worth_cost")

        packet = {
            "request_hash": request_hash,
            "rule_capsule_hash": rule_capsule_hash,
            "locked_fields": _lock_field_values(locked_fields),
            "fillable_paths": sorted(str(path) for path in fillable_paths),
            "minimal_deidentified_context": _sanitize_for_cloud(minimal_context),
            "acceptance_criteria": _sanitize_for_cloud(acceptance_criteria),
            "nonce": _sha256_obj({"request_hash": request_hash, "time": current_time})[:24],
            "ttl_seconds": self.ttl_seconds,
            "single_use": True,
            "return_schema": "Candidate",
        }
        extra = sorted(set(packet) - CLOUD_REQUEST_ALLOWED_KEYS)
        if extra:
            raise ValueError("cloud_packet_contains_unapproved_keys:" + ",".join(extra))

        packet_hash = _sha256_obj(packet)
        if packet_hash in self._invalid_packets:
            return _no_cloud("identical_invalid_packet_not_retried")

        return {
            "should_call_cloud": True,
            "cloud_call": 1,
            "reason": "quality_gap_cloud_expected_value_positive",
            "cached_candidate": None,
            "packet": packet,
            "packet_hash": packet_hash,
        }

    def remember_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        request_hash: str,
        rule_capsule_hash: str,
        now: float | None = None,
    ) -> None:
        current_time = time.time() if now is None else now
        expires_at = current_time + self.ttl_seconds
        self._candidate_cache[(request_hash, rule_capsule_hash)] = (expires_at, dict(candidate))

    def mark_invalid_packet(self, packet: Mapping[str, Any]) -> None:
        self._invalid_packets.add(_sha256_obj(packet))

    def _valid_cached_candidate(self, cache_key: tuple[str, str], now: float) -> dict[str, Any] | None:
        entry = self._candidate_cache.get(cache_key)
        if entry is None:
            return None
        expires_at, candidate = entry
        if expires_at <= now:
            self._candidate_cache.pop(cache_key, None)
            return None
        return dict(candidate)


def _no_cloud(reason: str) -> dict[str, Any]:
    return {
        "should_call_cloud": False,
        "cloud_call": 0,
        "reason": reason,
        "cached_candidate": None,
        "packet": None,
    }


def _lock_field_values(locked_fields: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    locked: dict[str, dict[str, Any]] = {}
    for key, value in locked_fields.items():
        path = str(key)
        locked[path] = {
            "locked": True,
            "value_hash": _sha256_obj(value),
        }
    return locked


def _sanitize_for_cloud(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_CLOUD_CONTEXT_KEYS:
                continue
            sanitized[str(key)] = _sanitize_for_cloud(child)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_cloud(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_cloud(item) for item in value]
    return value


def _sha256_obj(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()

