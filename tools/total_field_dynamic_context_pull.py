"""Pointer-first Total Field dynamic-context pull bound to minimum State Cells.

The cloud/local model bootstrap receives only opaque coordinates and references.
The actual bounded context is built locally after an exact, single-use pull.
No model/provider authority or persistent expanded workset is created here.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from products.eight_dimensional_generative_memory.w7tp_origin_state_minimum_packet_v1 import (
    validate_minimum_packet,
    volatile_reconstruction,
)


BOOTSTRAP_SCHEMA = "w7tp-total-field-context-pull-bootstrap/1.0"
RESULT_SCHEMA = "w7tp-total-field-context-pull-result/1.0"
CONTEXT_SCHEMA = "w7tp-total-field-model-visible-context/1.0"
PERSISTENCE_POLICY_REF = "policy:total-field:cloud-context:references-only:v1"
MAX_MODEL_VISIBLE_CONTEXT_BYTES = 256 * 1024
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+:-]{0,511}$")
FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "credential",
        "credentials",
        "founder_intent_plaintext",
        "full_dynamic_context",
        "local_rule_ref",
        "member_plaintext",
        "password",
        "private_key",
        "raw_context",
        "raw_secret",
        "raw_token",
        "reconstruction_rules",
        "resident_plaintext",
        "rule_body",
        "secret",
        "token",
    }
)
FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "authority_granted",
        "canonical",
        "commit_applied",
        "d8_authority",
        "execution_authorized",
        "formal_authority",
        "total_field_decision",
    }
)
CONTEXT_KEYS = frozenset(
    {
        "context_ref",
        "state_projection",
        "evidence_refs",
        "capability_refs",
        "acceptance_conditions",
        "schema_refs",
        "interface_refs",
        "non_core_rule_capsule_refs",
    }
)
ContextBuilder = Callable[
    [Path, Mapping[str, Any], Mapping[str, Any]],
    Mapping[str, Any],
]


class DynamicContextPullHold(RuntimeError):
    """Fail-closed pointer-first context-pull error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_ref(value: Any, code: str) -> str:
    if not isinstance(value, str) or REF_RE.fullmatch(value) is None:
        raise DynamicContextPullHold(code)
    return value
def _parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise DynamicContextPullHold("HOLD_CONTEXT_PULL_EXPIRY_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DynamicContextPullHold(
            "HOLD_CONTEXT_PULL_EXPIRY_INVALID"
        ) from exc
    if parsed.tzinfo is None:
        raise DynamicContextPullHold("HOLD_CONTEXT_PULL_EXPIRY_INVALID")
    return parsed.astimezone(timezone.utc)


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise DynamicContextPullHold("HOLD_CONTEXT_PULL_CLOCK_INVALID")
    return current.astimezone(timezone.utc)


def _walk_items(value: Any, path: str = "$"):
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield path, str(key), nested
            yield from _walk_items(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk_items(nested, f"{path}[{index}]")


def _validate_no_forbidden_context(value: Any) -> None:
    for path, raw_key, nested in _walk_items(value):
        key = raw_key.strip().lower().replace("-", "_")
        if key in FORBIDDEN_CONTEXT_KEYS:
            raise DynamicContextPullHold(
                f"HOLD_CONTEXT_FORBIDDEN_KEY:{path}.{raw_key}"
            )
        if key in FORBIDDEN_AUTHORITY_KEYS:
            raise DynamicContextPullHold(
                f"HOLD_CONTEXT_AUTHORITY_CLAIM:{path}.{raw_key}"
            )
        if isinstance(nested, str) and (
            "-----BEGIN PRIVATE KEY-----" in nested
            or nested.startswith("Bearer ")
        ):
            raise DynamicContextPullHold(
                f"HOLD_CONTEXT_SECRET_VALUE:{path}.{raw_key}"
            )
def _validate_ref_list(value: Any, code: str) -> list[str]:
    if not isinstance(value, list):
        raise DynamicContextPullHold(code)
    refs: list[str] = []
    for item in value:
        refs.append(_require_ref(item, code))
    if len(refs) != len(set(refs)):
        raise DynamicContextPullHold(code)
    return refs


def validate_model_visible_context(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != CONTEXT_KEYS:
        raise DynamicContextPullHold("HOLD_MODEL_VISIBLE_CONTEXT_SHAPE_INVALID")
    copied = copy.deepcopy(dict(value))
    _require_ref(copied.get("context_ref"), "HOLD_CONTEXT_REF_INVALID")
    if not isinstance(copied.get("state_projection"), Mapping):
        raise DynamicContextPullHold("HOLD_STATE_PROJECTION_INVALID")
    for field in (
        "evidence_refs",
        "capability_refs",
        "acceptance_conditions",
        "schema_refs",
        "interface_refs",
        "non_core_rule_capsule_refs",
    ):
        copied[field] = _validate_ref_list(
            copied.get(field),
            f"HOLD_{field.upper()}_INVALID",
        )
    _validate_no_forbidden_context(copied)
    if len(canonical_json_bytes(copied)) > MAX_MODEL_VISIBLE_CONTEXT_BYTES:
        raise DynamicContextPullHold("HOLD_MODEL_VISIBLE_CONTEXT_TOO_LARGE")
    return copied


def _bootstrap_hash_basis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop("bootstrap_sha256", None)
    return copied


def _result_hash_basis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop("pull_result_sha256", None)
    return copied
class TotalFieldDynamicContextPullBroker:
    """In-memory exact-coordinate broker; no list/enumeration operation exists."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._consumed: set[str] = set()

    def register(
        self,
        *,
        packet: Mapping[str, Any],
        task_ref: str,
        provider_ref: str,
        model_ref: str,
        expires_at: str,
        return_coordinate: str,
        context_builder: ContextBuilder,
    ) -> dict[str, Any]:
        validated_packet = validate_minimum_packet(packet)
        packet_copy = copy.deepcopy(dict(packet))
        task = _require_ref(task_ref, "HOLD_CONTEXT_PULL_TASK_REF_INVALID")
        provider = _require_ref(
            provider_ref,
            "HOLD_CONTEXT_PULL_PROVIDER_REF_INVALID",
        )
        model = _require_ref(
            model_ref,
            "HOLD_CONTEXT_PULL_MODEL_REF_INVALID",
        )
        return_ref = _require_ref(
            return_coordinate,
            "HOLD_CONTEXT_PULL_RETURN_COORDINATE_INVALID",
        )
        expiry = _parse_time(expires_at)
        if expiry <= _now(None):
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_ALREADY_EXPIRED")
        if not callable(context_builder):
            raise DynamicContextPullHold("HOLD_CONTEXT_BUILDER_INVALID")

        coordinate = "tfctx:" + secrets.token_hex(16)
        packet_ref = _require_ref(
            packet_copy.get("packet_ref"),
            "HOLD_CONTEXT_PULL_PACKET_REF_INVALID",
        )
        adi_ref = _require_ref(
            packet_copy.get("adi_coordinate_ref"),
            "HOLD_CONTEXT_PULL_ADI_REF_INVALID",
        )
        packet_hash = _require_ref(
            packet_copy.get("packet_sha256"),
            "HOLD_CONTEXT_PULL_PACKET_HASH_INVALID",
        )
        bootstrap: dict[str, Any] = {
            "schema_version": BOOTSTRAP_SCHEMA,
            "pull_coordinate": coordinate,
            "packet_ref": packet_ref,
            "packet_sha256": packet_hash,
            "adi_coordinate_ref": adi_ref,
            "context_schema_ref": CONTEXT_SCHEMA,
            "persistence_policy_ref": PERSISTENCE_POLICY_REF,
            "return_coordinate": return_ref,
            "expires_at": expiry.isoformat(),
            "single_use": True,
            "bootstrap_sha256": "",
        }
        bootstrap["bootstrap_sha256"] = canonical_sha256(
            _bootstrap_hash_basis(bootstrap)
        )
        self._records[coordinate] = {
            "packet": packet_copy,
            "task_ref": task,
            "provider_ref": provider,
            "model_ref": model,
            "expires_at": expiry,
            "return_coordinate": return_ref,
            "context_builder": context_builder,
            "bootstrap": copy.deepcopy(bootstrap),
            "validated_packet": validated_packet,
        }
        return bootstrap
    def pull(
        self,
        pull_coordinate: str,
        *,
        task_ref: str,
        provider_ref: str,
        model_ref: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        coordinate = _require_ref(
            pull_coordinate,
            "HOLD_CONTEXT_PULL_COORDINATE_INVALID",
        )
        record = self._records.get(coordinate)
        if record is None:
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_NOT_FOUND")
        if coordinate in self._consumed:
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_REPLAY_BLOCKED")
        if _now(now) >= record["expires_at"]:
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_EXPIRED")
        if task_ref != record["task_ref"]:
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_TASK_DRIFT")
        if provider_ref != record["provider_ref"]:
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_PROVIDER_DRIFT")
        if model_ref != record["model_ref"]:
            raise DynamicContextPullHold("HOLD_CONTEXT_PULL_MODEL_DRIFT")

        # Consume before local reconstruction; failed pulls require a new coordinate.
        self._consumed.add(coordinate)
        packet = copy.deepcopy(record["packet"])
        validate_minimum_packet(packet)

        workset_path: Path | None = None
        with volatile_reconstruction(packet) as local_state:
            workset_path = local_state["workset_path"]
            local_receipt = local_state["receipt"]
            context = record["context_builder"](
                workset_path,
                packet,
                local_receipt,
            )
            if not isinstance(context, Mapping):
                raise DynamicContextPullHold(
                    "HOLD_MODEL_VISIBLE_CONTEXT_MAPPING_REQUIRED"
                )
            model_context = validate_model_visible_context(context)
        if workset_path is None or workset_path.exists():
            raise DynamicContextPullHold("HOLD_CONTEXT_WORKSET_CLEANUP_FAILED")

        persistent_refs = {
            "context_ref": model_context["context_ref"],
            "packet_ref": packet["packet_ref"],
            "packet_sha256": packet["packet_sha256"],
            "adi_coordinate_ref": packet["adi_coordinate_ref"],
            "evidence_refs": list(model_context["evidence_refs"]),
            "capability_refs": list(model_context["capability_refs"]),
            "schema_refs": list(model_context["schema_refs"]),
            "interface_refs": list(model_context["interface_refs"]),
            "non_core_rule_capsule_refs": list(
                model_context["non_core_rule_capsule_refs"]
            ),
        }
        result: dict[str, Any] = {
            "schema_version": RESULT_SCHEMA,
            "pull_coordinate": coordinate,
            "task_ref": record["task_ref"],
            "packet_ref": packet["packet_ref"],
            "adi_coordinate_ref": packet["adi_coordinate_ref"],
            "context_schema_ref": CONTEXT_SCHEMA,
            "model_visible_context": model_context,
            "persistent_refs": persistent_refs,
            "persistence_policy": {
                "mode": "EPHEMERAL_CONTEXT_REFERENCES_ONLY",
                "dynamic_context_persistence_allowed": False,
                "full_state_persistence_allowed": False,
                "core_rule_persistence_allowed": False,
                "local_rule_ref_persistence_allowed": False,
                "personal_plaintext_persistence_allowed": False,
                "credential_persistence_allowed": False,
                "persistent_reference_classes": [
                    "CONTEXT_REF",
                    "PACKET_REF",
                    "ADI_COORDINATE_REF",
                    "EVIDENCE_REF",
                    "CAPABILITY_REF",
                    "SCHEMA_REF",
                    "INTERFACE_REF",
                    "NON_CORE_RULE_CAPSULE_REF",
                ],
            },
            "reconstruction_evidence": {
                "packet_sha256": local_receipt["packet_sha256"],
                "target_manifest_sha256": local_receipt[
                    "target_manifest_sha256"
                ],
                "target_bytes": local_receipt["target_bytes"],
                "target_files": local_receipt["target_files"],
                "workset_backend": local_receipt["workset_backend"],
                "persistent_materialization": False,
                "workset_destroyed": True,
            },
            "authority": {
                "provider_authority": False,
                "model_authority": False,
                "candidate_only": True,
                "formal_effect_authority": "LOCAL_TOTAL_FIELD",
            },
            "return_coordinate": record["return_coordinate"],
            "pull_result_sha256": "",
        }
        _validate_no_forbidden_context(
            {
                "model_visible_context": result["model_visible_context"],
                "persistent_refs": result["persistent_refs"],
            }
        )
        result["pull_result_sha256"] = canonical_sha256(
            _result_hash_basis(result)
        )
        return result

    def is_consumed(self, pull_coordinate: str) -> bool:
        return pull_coordinate in self._consumed


__all__ = [
    "BOOTSTRAP_SCHEMA",
    "CONTEXT_SCHEMA",
    "DynamicContextPullHold",
    "PERSISTENCE_POLICY_REF",
    "RESULT_SCHEMA",
    "TotalFieldDynamicContextPullBroker",
    "canonical_sha256",
    "validate_model_visible_context",
]
