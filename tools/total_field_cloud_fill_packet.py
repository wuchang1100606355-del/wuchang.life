#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed cloud-fill packet contract over the existing Total Field receiver.

This module is deliberately side-effect free.  It builds and validates one
single-use question packet, accepts only the declared fill zone, projects the
answer through the existing domain adapter, and emits a hash-bound receipt.
Cloud output is never authority and no receipt validation executes an effect.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from tools.domain_completion_total_field_gateway import (
    DomainCompletionTotalFieldGateway,
)
from tools.sovereign_ai_domain_completion_candidate import build_candidate
from tools.total_field.human_response_renderer import render_human_response


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "W7TP_TOTAL_FIELD_CLOUD_FILL_PACKET_P1_STATIC_CANDIDATE_V1"
DEFINITION = "TOTAL_FIELD_QUESTION_CLOUD_PULL_AND_FILL_TOTAL_FIELD_VERIFY"
REQUEST_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-CLOUD-FILL-PACKET/1.0"
RESPONSE_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-CLOUD-FILL-RESPONSE/1.0"
REQUEST_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_total_field_cloud_fill_request_v1.schema.json"
)
RESPONSE_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_total_field_cloud_fill_response_v1.schema.json"
)
CAPSULE_PATH = (
    ROOT / "configs/total_field/w7tp_static_cloud_fill_rule_capsule_v1.json"
)
AUTHORITY_RULES_PATH = (
    ROOT / "configs/total_field/w7tp_total_field_cloud_fill_rules_v1.json"
)
RECEIVE_CANDIDATE_PATH = "tools.total_field_candidate_gateway.receive_candidate"
DOMAIN_ADAPTER_PATH = (
    "tools.domain_completion_total_field_gateway."
    "DomainCompletionTotalFieldGateway.receive_candidate"
)
RECEIPT_ADAPTER_PATH = (
    "tools.total_field_cloud_fill_packet.StaticTotalFieldReceiptAdapter.verify"
)

FILLABLE_PATHS = (
    "/cloud_fillable/candidate_answer",
    "/cloud_fillable/concise_rationale",
    "/cloud_fillable/assumptions",
    "/cloud_fillable/uncertainties",
    "/cloud_fillable/risk_candidates",
    "/cloud_fillable/verification_candidate",
    "/cloud_fillable/evidence_refs",
)
FORBIDDEN_CLAIMS = (
    "ALLOW",
    "COMMITTED",
    "TFS",
    "TFID",
    "TOTAL_FIELD_HASH",
    "CANONICAL_POINTER",
    "DEPLOYED",
    "FORMALLY_APPROVED",
)
PROTECTED_KEYS = frozenset(
    {
        "adi",
        "adi_content",
        "credential",
        "credentials",
        "cross_member_data",
        "founder_long_term_memory",
        "founder_memory_plaintext",
        "h64",
        "h64_td",
        "member_plaintext",
        "password",
        "private_key",
        "protected_codebook",
        "raw_secret",
        "raw_token",
        "secret",
    }
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
)
AUTHORITY_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:ALLOW|COMMITTED|TFS|TFID|TOTAL_FIELD_HASH|"
    r"CANONICAL_POINTER|DEPLOYED|FORMALLY_APPROVED|CANONICAL)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


JSONValue = (
    None
    | bool
    | int
    | float
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)


class CloudFillPacketError(ValueError):
    """Stable rejection that never includes protected field contents."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def canonical_json(value: Any) -> str:
    """Return strict deterministic JSON without NaN or non-JSON objects."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CloudFillPacketError("CLOUD_FILL_JSON_INVALID") from exc


def deep_copy_json(value: Any) -> JSONValue:
    """Detach one strict finite JSON value."""

    try:
        copied = json.loads(
            canonical_json(value),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise CloudFillPacketError("CLOUD_FILL_JSON_INVALID") from exc
    return cast(JSONValue, copied)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise CloudFillPacketError("CLOUD_FILL_LOCAL_CONTRACT_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise CloudFillPacketError("CLOUD_FILL_LOCAL_CONTRACT_INVALID")
    return value


def _validator(path: Path) -> Draft202012Validator:
    schema = _load_json(path)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise CloudFillPacketError("CLOUD_FILL_SCHEMA_INVALID") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _error_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _validate_schema(value: Mapping[str, Any], path: Path, code: str) -> None:
    errors = sorted(
        _validator(path).iter_errors(dict(value)),
        key=lambda item: ([str(part) for part in item.absolute_path], item.message),
    )
    if errors:
        raise CloudFillPacketError(code, _error_path(errors[0]))


def calculate_capsule_sha256(capsule: Mapping[str, Any]) -> str:
    payload = dict(capsule)
    payload.pop("capsule_sha256", None)
    return canonical_sha256(payload)


def calculate_request_sha256(packet: Mapping[str, Any]) -> str:
    copied = deep_copy_json(dict(packet))
    if not isinstance(copied, dict) or not isinstance(copied.get("locked"), dict):
        raise CloudFillPacketError("CLOUD_FILL_REQUEST_MAPPING_REQUIRED")
    copied["locked"].pop("request_sha256", None)
    return canonical_sha256(copied)


def calculate_response_sha256(response: Mapping[str, Any]) -> str:
    copied = deep_copy_json(dict(response))
    if not isinstance(copied, dict):
        raise CloudFillPacketError("CLOUD_FILL_RESPONSE_MAPPING_REQUIRED")
    copied.pop("response_sha256", None)
    return canonical_sha256(copied)


def calculate_receipt_sha256(receipt: Mapping[str, Any]) -> str:
    copied = deep_copy_json(dict(receipt))
    if not isinstance(copied, dict):
        raise CloudFillPacketError("TOTAL_FIELD_RECEIPT_MAPPING_REQUIRED")
    copied.pop("receipt_sha256", None)
    return canonical_sha256(copied)


def _matching_protected_path(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            normalized = str(key).strip().casefold().replace("-", "_")
            child = f"{path}.{key}"
            if normalized in PROTECTED_KEYS:
                return child
            found = _matching_protected_path(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = _matching_protected_path(item, f"{path}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
            return path
    return None


def _authority_injection_path(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            child = f"{path}.{key}"
            if AUTHORITY_PATTERN.search(str(key)):
                return child
            found = _authority_injection_path(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = _authority_injection_path(item, f"{path}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and AUTHORITY_PATTERN.search(value):
        return path
    return None


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CloudFillPacketError("CLOUD_FILL_EXPIRY_INVALID", "$.expires_at") from exc
    if parsed.tzinfo is None:
        raise CloudFillPacketError("CLOUD_FILL_EXPIRY_INVALID", "$.expires_at")
    return parsed.astimezone(timezone.utc)


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise CloudFillPacketError("CLOUD_FILL_NOW_MUST_BE_TIMEZONE_AWARE")
    return current.astimezone(timezone.utc)


def _capsule_identity(capsule: Mapping[str, Any]) -> dict[str, str]:
    actual = calculate_capsule_sha256(capsule)
    declared = capsule.get("capsule_sha256")
    if declared != actual:
        raise CloudFillPacketError("HOLD_RULE_CAPSULE_HASH_MISMATCH")
    required = (
        "capsule_id",
        "version",
        "receiver_version",
        "reconstructor_version",
        "validator_version",
    )
    if not all(isinstance(capsule.get(key), str) and capsule[key] for key in required):
        raise CloudFillPacketError("HOLD_RULE_CAPSULE_IDENTITY_INVALID")
    return {
        "capsule_id": cast(str, capsule["capsule_id"]),
        "version": cast(str, capsule["version"]),
        "sha256": actual,
        "receiver_version": cast(str, capsule["receiver_version"]),
        "reconstructor_version": cast(str, capsule["reconstructor_version"]),
        "validator_version": cast(str, capsule["validator_version"]),
    }


def validate_cloud_fill_request(
    packet: Mapping[str, Any], *, capsule_path: Path = CAPSULE_PATH
) -> dict[str, JSONValue]:
    """Validate immutable/fillable boundaries and every local capsule binding."""

    copied = deep_copy_json(dict(packet))
    if not isinstance(copied, dict):
        raise CloudFillPacketError("CLOUD_FILL_REQUEST_MAPPING_REQUIRED")
    _validate_schema(copied, REQUEST_SCHEMA_PATH, "CLOUD_FILL_REQUEST_SCHEMA_INVALID")
    locked = cast(dict[str, Any], copied["locked"])
    if tuple(locked["fillable_paths"]) != FILLABLE_PATHS:
        raise CloudFillPacketError("CLOUD_FILL_FILLABLE_PATHS_MISMATCH", "$.locked.fillable_paths")
    if tuple(locked["forbidden_claims"]) != FORBIDDEN_CLAIMS:
        raise CloudFillPacketError("CLOUD_FILL_AUTHORITY_RULES_MISMATCH", "$.locked.forbidden_claims")
    if locked["request_sha256"] != calculate_request_sha256(copied):
        raise CloudFillPacketError("CLOUD_FILL_REQUEST_HASH_MISMATCH", "$.locked.request_sha256")
    capsule = _load_json(capsule_path)
    identity = _capsule_identity(capsule)
    if locked["static_rule_capsule_ref"] != identity:
        raise CloudFillPacketError("HOLD_RULE_CAPSULE_HASH_MISMATCH", "$.locked.static_rule_capsule_ref")
    protected = _matching_protected_path(locked)
    if protected is not None:
        raise CloudFillPacketError("CLOUD_FILL_PROTECTED_CONTEXT_BLOCKED", protected)
    reconstructed = {
        "sanitized_question": locked["sanitized_question"],
        "product_output_contract": locked["product_output_contract"],
        "dynamic_rule_projection": locked["dynamic_rule_projection"],
        "resource_refs": locked["resource_refs"],
        "reconstruction_conditions": locked["reconstruction_conditions"],
        "verification_conditions": locked["verification_conditions"],
    }
    measured = len(canonical_json(reconstructed).encode("utf-8"))
    if locked["accounting"]["reconstructed_bytes"] != measured:
        raise CloudFillPacketError("CLOUD_FILL_RECONSTRUCTED_BYTES_MISMATCH", "$.locked.accounting.reconstructed_bytes")
    request_bytes = len(canonical_json(copied).encode("utf-8"))
    if locked["accounting"]["request_transport_bytes"] != request_bytes:
        raise CloudFillPacketError("CLOUD_FILL_REQUEST_BYTES_MISMATCH", "$.locked.accounting.request_transport_bytes")
    return cast(dict[str, JSONValue], copied)


def build_cloud_fill_request(
    *,
    packet_id: str,
    question_type_ref: str,
    sanitized_question: str,
    product_output_contract: Mapping[str, Any],
    dynamic_rule_projection: Mapping[str, Any],
    allowed_information_scope: list[str],
    state_coordinate: str,
    relationship_refs: list[str],
    resource_refs: list[str],
    reconstruction_conditions: Mapping[str, Any],
    equivalent_candidate_state_rules: list[str],
    verification_conditions: Mapping[str, Any],
    evidence_refs: list[str],
    allowed_provider_refs: list[str],
    allowed_model_refs: list[str],
    nonce: str,
    expires_at: str,
    return_coordinate: str,
    capsule_path: Path = CAPSULE_PATH,
    max_input_tokens: int = 2048,
    max_output_tokens: int = 768,
) -> dict[str, JSONValue]:
    """Build one closed blank packet and measure bytes independently of tokens."""

    capsule = _load_json(capsule_path)
    capsule_ref = _capsule_identity(capsule)
    reconstructed = {
        "sanitized_question": sanitized_question,
        "product_output_contract": dict(product_output_contract),
        "dynamic_rule_projection": dict(dynamic_rule_projection),
        "resource_refs": list(resource_refs),
        "reconstruction_conditions": dict(reconstruction_conditions),
        "verification_conditions": dict(verification_conditions),
    }
    packet: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "locked": {
            "packet_id": packet_id,
            "request_mode": "TOTAL_FIELD_PULL",
            "question_type_ref": question_type_ref,
            "sanitized_question": sanitized_question,
            "product_output_contract": dict(product_output_contract),
            "static_rule_capsule_ref": capsule_ref,
            "dynamic_rule_projection": dict(dynamic_rule_projection),
            "allowed_information_scope": list(allowed_information_scope),
            "fillable_paths": list(FILLABLE_PATHS),
            "forbidden_claims": list(FORBIDDEN_CLAIMS),
            "response_schema_ref": RESPONSE_SCHEMA_VERSION,
            "state_coordinate": state_coordinate,
            "relationship_refs": list(relationship_refs),
            "resource_refs": list(resource_refs),
            "receiver_contract_ref": RECEIVE_CANDIDATE_PATH,
            "reconstruction_conditions": dict(reconstruction_conditions),
            "equivalent_candidate_state_rules": list(equivalent_candidate_state_rules),
            "verification_conditions": dict(verification_conditions),
            "evidence_refs": list(evidence_refs),
            "allowed_provider_refs": list(allowed_provider_refs),
            "allowed_model_refs": list(allowed_model_refs),
            "accounting": {
                "request_transport_bytes": 1,
                "reconstructed_bytes": len(canonical_json(reconstructed).encode("utf-8")),
                "model_input_tokens": 0,
                "model_output_tokens": 0,
            },
            "request_sha256": "0" * 64,
            "nonce": nonce,
            "expires_at": expires_at,
            "single_use": True,
            "cloud_required": False,
            "context_mode": "MINIMUM_AUTHORIZED_FRAGMENTS",
            "duplicate_request": "REUSE_BY_EXACT_REQUEST_HASH",
            "full_chain_of_thought": "PROHIBITED",
            "max_input_tokens": max_input_tokens,
            "max_output_tokens": max_output_tokens,
            "max_cloud_calls": 1,
            "return_coordinate": return_coordinate,
        },
        "cloud_fillable": {
            "candidate_answer": None,
            "concise_rationale": None,
            "assumptions": [],
            "uncertainties": [],
            "risk_candidates": [],
            "verification_candidate": [],
            "evidence_refs": [],
        },
    }
    for _ in range(8):
        measured = len(canonical_json(packet).encode("utf-8"))
        if packet["locked"]["accounting"]["request_transport_bytes"] == measured:
            break
        packet["locked"]["accounting"]["request_transport_bytes"] = measured
    packet["locked"]["request_sha256"] = calculate_request_sha256(packet)
    return validate_cloud_fill_request(packet, capsule_path=capsule_path)


def validate_cloud_fill_response(response: Mapping[str, Any]) -> dict[str, JSONValue]:
    copied = deep_copy_json(dict(response))
    if not isinstance(copied, dict):
        raise CloudFillPacketError("CLOUD_FILL_RESPONSE_MAPPING_REQUIRED")
    _validate_schema(copied, RESPONSE_SCHEMA_PATH, "CLOUD_FILL_RESPONSE_SCHEMA_INVALID")
    if copied["response_sha256"] != calculate_response_sha256(copied):
        raise CloudFillPacketError("CLOUD_FILL_RESPONSE_HASH_MISMATCH", "$.response_sha256")
    measured = len(canonical_json(copied).encode("utf-8"))
    accounting = cast(dict[str, Any], copied["accounting"])
    if accounting["response_transport_bytes"] != measured:
        raise CloudFillPacketError("CLOUD_FILL_RESPONSE_BYTES_MISMATCH", "$.accounting.response_transport_bytes")
    injection = _authority_injection_path(copied["cloud_fillable"])
    if injection is not None:
        raise CloudFillPacketError("CLOUD_FILL_AUTHORITY_INJECTION_BLOCKED", injection)
    protected = _matching_protected_path(copied["cloud_fillable"])
    if protected is not None:
        raise CloudFillPacketError("CLOUD_FILL_PROTECTED_CONTEXT_BLOCKED", protected)
    return cast(dict[str, JSONValue], copied)


def build_cloud_fill_response(
    request: Mapping[str, Any],
    *,
    cloud_fillable: Mapping[str, Any],
    provider_ref: str,
    model_ref: str,
    model_version: str,
    model_input_tokens: int,
    model_output_tokens: int,
) -> dict[str, JSONValue]:
    """Build a hash-bound response from reported provider token usage."""

    validated = validate_cloud_fill_request(request)
    locked = cast(dict[str, Any], validated["locked"])
    response: dict[str, Any] = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "packet_id": locked["packet_id"],
        "request_mode": "TOTAL_FIELD_PULL",
        "request_sha256": locked["request_sha256"],
        "nonce": locked["nonce"],
        "expires_at": locked["expires_at"],
        "capsule_sha256": locked["static_rule_capsule_ref"]["sha256"],
        "provider_ref": provider_ref,
        "model_ref": model_ref,
        "model_version": model_version,
        "response_schema_ref": RESPONSE_SCHEMA_VERSION,
        "cloud_fillable": dict(cloud_fillable),
        "accounting": {
            "request_transport_bytes": locked["accounting"]["request_transport_bytes"],
            "response_transport_bytes": 1,
            "reconstructed_bytes": locked["accounting"]["reconstructed_bytes"],
            "model_input_tokens": model_input_tokens,
            "model_output_tokens": model_output_tokens,
            "cloud_calls": 1,
        },
        "response_sha256": "0" * 64,
    }
    for _ in range(8):
        measured = len(canonical_json(response).encode("utf-8"))
        if response["accounting"]["response_transport_bytes"] == measured:
            break
        response["accounting"]["response_transport_bytes"] = measured
    response["response_sha256"] = calculate_response_sha256(response)
    return validate_cloud_fill_response(response)


def normalize_llm_push_to_fill_response(
    request: Mapping[str, Any], legacy: Mapping[str, Any]
) -> dict[str, JSONValue]:
    """Normalize legacy LLM_PUSH output into the same closed response contract."""

    required = {
        "source_mode",
        "cloud_fillable",
        "provider_ref",
        "model_ref",
        "model_version",
        "model_input_tokens",
        "model_output_tokens",
    }
    if set(legacy) != required or legacy.get("source_mode") != "LLM_PUSH":
        raise CloudFillPacketError("LLM_PUSH_FILL_NORMALIZATION_INVALID")
    return build_cloud_fill_response(
        request,
        cloud_fillable=cast(Mapping[str, Any], legacy["cloud_fillable"]),
        provider_ref=cast(str, legacy["provider_ref"]),
        model_ref=cast(str, legacy["model_ref"]),
        model_version=cast(str, legacy["model_version"]),
        model_input_tokens=cast(int, legacy["model_input_tokens"]),
        model_output_tokens=cast(int, legacy["model_output_tokens"]),
    )


def render_cloud_fill_hold(reason_code: str) -> dict[str, JSONValue]:
    """Render one actionable Traditional-Chinese HOLD without raw internals."""

    repairs = {
        "HOLD_RULE_CAPSULE_HASH_MISMATCH": "重新提供相同版本且雜湊吻合的規則膠囊後，我會自動續驗。",
        "CLOUD_FILL_EXPIRED": "請建立一份新的單次限時題目封包，我會自動重新驗證。",
        "CLOUD_FILL_RECONSTRUCTOR_DRIFT": "請提供封包指定版本的接收器與重構器，再重新送交。",
        "CLOUD_FILL_BUDGET_EXCEEDED": "請縮小必要題目片段或重新核定單次預算後再送交。",
    }
    repair = repairs.get(
        reason_code,
        "請依原題目重新建立一份邊界與雜湊都吻合的候選封包。",
    )
    reply = (
        "我想完成這次雲端候選填空並交回總場驗證，但目前只有一個必要條件未吻合。"
        "這可能讓候選無法可靠對回原題，因此我沒有改動資料、服務或任何正式狀態。"
        f"{repair}"
    )
    rendered = render_human_response(
        {
            "decision": "HOLD",
            "risk_level": "MEDIUM",
            "gate_code": "HOLD_CLOUD_FILL_BOUNDARY",
        },
        channel="web",
    )
    return {
        "decision": "HOLD",
        "reply_text": reply,
        "product_goal": "完成雲端候選填空並由總場驗證",
        "single_blocker": "題目封包的必要邊界或版本尚未吻合",
        "impact": "候選無法可靠綁定原題並進入總場",
        "unchanged_state": "資料、服務、權威狀態與執行環境均未變更",
        "exact_repair": repair,
        "automation": "修復後可自動重新驗證並提交候選",
        "founder_question": None,
        "next": "APPLY_ONE_EXACT_REPAIR_AND_REVALIDATE",
        "renderer_ref": "tools.total_field.human_response_renderer.render_human_response",
        "renderer_decision": cast(str, rendered["decision"]),
    }


class StaticTotalFieldReceiptAdapter:
    """Validate receipt identity only; P1 never executes a real-world effect."""

    REQUIRED_KEYS = frozenset(
        {
            "packet_id",
            "request_sha256",
            "response_sha256",
            "candidate_hash",
            "final_decision",
            "total_field_hash",
            "receipt_sha256",
        }
    )

    @classmethod
    def verify(
        cls,
        receipt: Mapping[str, Any],
        *,
        packet_id: str,
        request_sha256: str,
        response_sha256: str,
    ) -> dict[str, JSONValue]:
        copied = deep_copy_json(dict(receipt))
        if not isinstance(copied, dict) or frozenset(copied) != cls.REQUIRED_KEYS:
            raise CloudFillPacketError("TOTAL_FIELD_RECEIPT_SCHEMA_INVALID")
        if copied["receipt_sha256"] != calculate_receipt_sha256(copied):
            raise CloudFillPacketError("TOTAL_FIELD_RECEIPT_HASH_MISMATCH")
        if (
            copied["packet_id"] != packet_id
            or copied["request_sha256"] != request_sha256
            or copied["response_sha256"] != response_sha256
        ):
            raise CloudFillPacketError("TOTAL_FIELD_RECEIPT_BINDING_MISMATCH")
        return {
            "receipt_match": True,
            "governed_decision": cast(str, copied["final_decision"]),
            "effect_candidate_authorized": copied["final_decision"] == "ALLOW",
            "effect_executed": False,
            "runtime_activation_required": True,
            "adapter_ref": RECEIPT_ADAPTER_PATH,
        }


class CloudFillPacketBroker:
    """In-memory P1 capability broker with no enumeration or persistent state."""

    def __init__(
        self,
        *,
        observation_domains: Mapping[str, Any],
        capsule_path: Path = CAPSULE_PATH,
    ) -> None:
        domains = deep_copy_json(dict(observation_domains))
        if not isinstance(domains, dict):
            raise CloudFillPacketError("OBSERVATION_DOMAINS_INVALID")
        self._observation_domains = domains
        self._capsule_path = capsule_path
        self._requests: dict[str, dict[str, JSONValue]] = {}
        self._pulled: set[str] = set()
        self._cloud_calls: dict[str, int] = {}
        self._consumed_nonces: set[str] = set()
        self._cache: dict[tuple[str, str, str, str], dict[str, JSONValue]] = {}

    def register_request(self, packet: Mapping[str, Any]) -> str:
        validated = validate_cloud_fill_request(packet, capsule_path=self._capsule_path)
        locked = cast(dict[str, Any], validated["locked"])
        packet_id = cast(str, locked["packet_id"])
        existing = self._requests.get(packet_id)
        if existing is not None and existing != validated:
            raise CloudFillPacketError("CLOUD_FILL_PACKET_ID_COLLISION")
        self._requests[packet_id] = validated
        return packet_id

    def pull_request(
        self, packet_id: str, *, now: datetime | None = None
    ) -> dict[str, JSONValue]:
        """Pull one named packet once; no list operation exists."""

        request = self._requests.get(packet_id)
        if request is None:
            raise CloudFillPacketError("CLOUD_FILL_PACKET_NOT_FOUND")
        expires_at = cast(str, cast(dict[str, Any], request["locked"])["expires_at"])
        if _now(now) >= _parse_time(expires_at):
            raise CloudFillPacketError("CLOUD_FILL_EXPIRED")
        if packet_id in self._pulled:
            raise CloudFillPacketError("CLOUD_FILL_PULL_REPLAY_BLOCKED")
        self._pulled.add(packet_id)
        return cast(dict[str, JSONValue], deep_copy_json(request))

    def record_cloud_call(self, packet_id: str) -> int:
        if packet_id not in self._pulled:
            raise CloudFillPacketError("CLOUD_FILL_PULL_REQUIRED")
        count = self._cloud_calls.get(packet_id, 0) + 1
        maximum = cast(
            int,
            cast(dict[str, Any], self._requests[packet_id]["locked"])["max_cloud_calls"],
        )
        if count > maximum:
            raise CloudFillPacketError("CLOUD_FILL_MAX_CALLS_EXCEEDED")
        self._cloud_calls[packet_id] = count
        return count

    def cloud_call_count(self, packet_id: str) -> int:
        return self._cloud_calls.get(packet_id, 0)

    def reuse_valid_result(
        self,
        *,
        request_sha256: str,
        capsule_sha256: str,
        model_ref: str,
        model_version: str,
    ) -> dict[str, JSONValue] | None:
        cached = self._cache.get(
            (request_sha256, capsule_sha256, model_ref, model_version)
        )
        if cached is None:
            return None
        copied = deep_copy_json(cached)
        assert isinstance(copied, dict)
        copied["cloud_call_reused"] = True
        return cast(dict[str, JSONValue], copied)

    def receive_cloud_response(
        self,
        response: Mapping[str, Any],
        *,
        previous_value: JSONValue,
        now: datetime | None = None,
    ) -> dict[str, JSONValue]:
        """Verify, normalize, project, and adjudicate one cloud-filled candidate."""

        filled = validate_cloud_fill_response(response)
        packet_id = cast(str, filled["packet_id"])
        request = self._requests.get(packet_id)
        if request is None:
            raise CloudFillPacketError("CLOUD_FILL_PACKET_NOT_FOUND")
        if packet_id not in self._pulled:
            raise CloudFillPacketError("CLOUD_FILL_PULL_REQUIRED")
        locked = cast(dict[str, Any], request["locked"])
        bindings = {
            "request_sha256": locked["request_sha256"],
            "nonce": locked["nonce"],
            "expires_at": locked["expires_at"],
            "capsule_sha256": locked["static_rule_capsule_ref"]["sha256"],
        }
        for key, expected in bindings.items():
            if filled[key] != expected:
                raise CloudFillPacketError("CLOUD_FILL_RESPONSE_BINDING_MISMATCH", f"$.{key}")
        if _now(now) >= _parse_time(cast(str, filled["expires_at"])):
            raise CloudFillPacketError("CLOUD_FILL_EXPIRED")
        nonce = cast(str, filled["nonce"])
        if nonce in self._consumed_nonces:
            raise CloudFillPacketError("CLOUD_FILL_REPLAY_BLOCKED")
        if filled["provider_ref"] not in locked["allowed_provider_refs"]:
            raise CloudFillPacketError("CLOUD_FILL_PROVIDER_DRIFT")
        model_binding = f"{filled['model_ref']}@{filled['model_version']}"
        if model_binding not in locked["allowed_model_refs"]:
            raise CloudFillPacketError("CLOUD_FILL_MODEL_VERSION_DRIFT")
        accounting = cast(dict[str, Any], filled["accounting"])
        if accounting["request_transport_bytes"] != locked["accounting"]["request_transport_bytes"]:
            raise CloudFillPacketError("CLOUD_FILL_REQUEST_BYTES_MISMATCH")
        if accounting["reconstructed_bytes"] != locked["accounting"]["reconstructed_bytes"]:
            raise CloudFillPacketError("CLOUD_FILL_RECONSTRUCTED_BYTES_MISMATCH")
        if accounting["model_input_tokens"] > locked["max_input_tokens"]:
            raise CloudFillPacketError("CLOUD_FILL_BUDGET_EXCEEDED")
        if accounting["model_output_tokens"] > locked["max_output_tokens"]:
            raise CloudFillPacketError("CLOUD_FILL_BUDGET_EXCEEDED")
        if self._cloud_calls.get(packet_id, 0) != accounting["cloud_calls"]:
            raise CloudFillPacketError("CLOUD_FILL_CALL_ACCOUNTING_MISMATCH")
        answer = cast(dict[str, Any], cast(dict[str, Any], filled["cloud_fillable"])["candidate_answer"])
        contract = cast(dict[str, Any], locked["product_output_contract"])
        candidate = build_candidate(
            domain=contract["domain"],
            entity_ref=contract["entity_ref"],
            attribute_name=contract["attribute_name"],
            candidate_value=answer["value"],
            source_mode="TOTAL_FIELD_PULL",
            model_ref=cast(str, filled["model_ref"]),
            provider_ref=cast(str, filled["provider_ref"]),
            event_ref=contract["event_ref"],
            observation_domain_ref=contract["observation_domain_ref"],
            rule_ref=contract["rule_ref"],
            evidence_refs=cast(dict[str, Any], filled["cloud_fillable"])["evidence_refs"],
            confidence=answer["confidence"],
            sensitivity=contract["sensitivity"],
            requires_human_confirmation=contract["requires_human_confirmation"],
        )
        governed = DomainCompletionTotalFieldGateway(
            observation_domains=self._observation_domains
        ).receive_candidate(candidate, previous_value=previous_value)
        receipt: dict[str, Any] = {
            "packet_id": packet_id,
            "request_sha256": filled["request_sha256"],
            "response_sha256": filled["response_sha256"],
            "candidate_hash": candidate["candidate_hash"],
            "final_decision": governed["final_decision"],
            "total_field_hash": governed["total_field_hash"],
        }
        receipt["receipt_sha256"] = calculate_receipt_sha256(receipt)
        rationale = cast(dict[str, Any], filled["cloud_fillable"])["concise_rationale"]
        if governed["final_decision"] == "ALLOW":
            natural = render_human_response(
                {
                    "decision": "PASS",
                    "risk_level": "LOW",
                    "reply_candidate": {
                        "text": rationale or "候選已由總場完成驗證。"
                    },
                },
                channel="web",
            )
            human_response: JSONValue = {
                "decision": "PASS",
                "reply_text": natural["reply_text"],
                "renderer_ref": "tools.total_field.human_response_renderer.render_human_response",
            }
        else:
            human_response = render_cloud_fill_hold("TOTAL_FIELD_DECISION_HOLD")
        result: dict[str, Any] = {
            "state": "CANDIDATE_GOVERNED",
            "run_id": RUN_ID,
            "definition": DEFINITION,
            "request_mode": "TOTAL_FIELD_PULL",
            "source_was_authority": False,
            "receive_candidate_path": RECEIVE_CANDIDATE_PATH,
            "domain_adapter_path": DOMAIN_ADAPTER_PATH,
            "governed_result": governed,
            "total_field_receipt": receipt,
            "human_response": human_response,
            "cloud_call_reused": False,
            "effect_executed": False,
        }
        self._consumed_nonces.add(nonce)
        cache_key = (
            cast(str, filled["request_sha256"]),
            cast(str, filled["capsule_sha256"]),
            cast(str, filled["model_ref"]),
            cast(str, filled["model_version"]),
        )
        copied = deep_copy_json(result)
        assert isinstance(copied, dict)
        self._cache[cache_key] = copied
        return cast(dict[str, JSONValue], deep_copy_json(copied))


def should_call_cloud(*, cloud_required: bool = False, local_can_complete: bool = True) -> bool:
    """Default ordinary/local-completable work to zero cloud calls."""

    if not isinstance(cloud_required, bool) or not isinstance(local_can_complete, bool):
        raise CloudFillPacketError("CLOUD_FILL_ROUTING_FLAGS_INVALID")
    return cloud_required and not local_can_complete


__all__ = [
    "AUTHORITY_RULES_PATH",
    "CAPSULE_PATH",
    "CloudFillPacketBroker",
    "CloudFillPacketError",
    "DEFINITION",
    "DOMAIN_ADAPTER_PATH",
    "FILLABLE_PATHS",
    "FORBIDDEN_CLAIMS",
    "RECEIPT_ADAPTER_PATH",
    "RECEIVE_CANDIDATE_PATH",
    "REQUEST_SCHEMA_PATH",
    "RESPONSE_SCHEMA_PATH",
    "RUN_ID",
    "StaticTotalFieldReceiptAdapter",
    "build_cloud_fill_request",
    "build_cloud_fill_response",
    "calculate_capsule_sha256",
    "calculate_receipt_sha256",
    "calculate_request_sha256",
    "calculate_response_sha256",
    "normalize_llm_push_to_fill_response",
    "render_cloud_fill_hold",
    "should_call_cloud",
    "validate_cloud_fill_request",
    "validate_cloud_fill_response",
]
