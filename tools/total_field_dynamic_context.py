#!/usr/bin/env python3
"""Read-only, hash-bound dynamic context for the local XiaoJ model."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping


TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY = "NONE"


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_RELATIVE_PATH = Path("runtime/developer_memory/packets/developer_bootstrap.json")
MEMORY_ROOT_RELATIVE_PATH = Path("runtime/developer_memory")
CAPABILITY_PACK_RELATIVE_PATH = Path("manifests/ollama_xiaoj_total_field_v0_1")
CAPABILITY_PACK_FILES = (
    "capability_registry.json",
    "founder_all_skills_8d_index.json",
    "root_model_contract.json",
    "routing_policy.json",
    "tool_contracts.json",
    "voice_pronunciation_routing_contract.json",
)
SAFE_SEARCH_ROOTS = (
    Path("runtime/total_field"),
    Path("runtime/developer_memory/canonical"),
    Path("runtime/developer_memory/registry"),
    Path("manifests"),
    Path("schemas"),
    Path("configs/total_field"),
    Path("tools"),
    Path("docs/total_field"),
)
EXCLUDED_SEARCH_PATHS = {"tools/total_field_dynamic_context.py"}
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".txt", ".yaml", ".yml", ".sha256"}
DENIED_PATH_MARKERS = {
    ".git",
    "__pycache__",
    "cache",
    "credential",
    "credentials",
    "member_plaintext",
    "oauth",
    "private_key",
    "quarantine",
    "secret",
    "secrets",
    "service_account",
    "session",
    "sessions",
    "token",
    "tokens",
}
SENSITIVE_VALUE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"\bsk-[A-Za-z0-9_-]{16,}",
        r"\bgh[pousr]_[A-Za-z0-9]{16,}",
        r"\bAIza[0-9A-Za-z_-]{20,}",
        r"\bBearer\s+[A-Za-z0-9._-]{16,}",
        r'"(?:access_token|client_secret|password|private_key|refresh_token|token)"\s*:\s*"[^\"]+"',
    )
)
PERSONAL_DATA_PATTERNS = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[REDACTED_EMAIL]"),
    (re.compile(r"CHIANG Cheng-Lung|江政隆", re.IGNORECASE), "[REDACTED_PERSON]"),
)
MAX_FILE_BYTES = 1_000_000
MAX_SNIPPET_CHARS = 1400
MAX_QUERY_TERMS = 24
QUERY_ALIASES = {
    "語音": ("voice", "speech", "audio", "stt", "tts"),
    "聲音": ("voice", "speech", "audio", "tts"),
    "總場": ("total_field", "governance"),
    "模型": ("model", "ollama", "llm"),
    "動態上下文": ("dynamic_context", "context"),
    "審查": ("review", "receipt", "manifest"),
    "雲端": ("cloud", "external_candidate"),
}


ACTIVE_TOTAL_FIELD_AUTHORITY_LOOKUP_REF = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVER_MODULE = "tools.total_field_authority_resolver"
ACTIVE_TOTAL_FIELD_AUTHORITY_ADAPTER_MODULE = (
    "tools.total_field_receive_candidate_authority_adapter"
)


def _load_capability_pack(root: Path) -> dict[str, Any] | None:
    pack_root = _resolve_inside(root, CAPABILITY_PACK_RELATIVE_PATH)
    if not pack_root.exists():
        return None
    manifest_path = pack_root / "source_manifest.sha256"
    if not manifest_path.is_file():
        raise ValueError("capability pack source_manifest.sha256 missing")

    bindings: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if match is None:
            raise ValueError("capability pack source manifest line invalid")
        bindings[match.group(2)] = match.group(1)

    for relative_path, expected_sha256 in bindings.items():
        path = _resolve_inside(root, relative_path)
        if not path.is_file() or sha256_bytes(path.read_bytes()) != expected_sha256:
            raise ValueError(f"capability pack source mismatch:{relative_path}")

    documents: dict[str, Any] = {}
    for filename in CAPABILITY_PACK_FILES:
        relative = (CAPABILITY_PACK_RELATIVE_PATH / filename).as_posix()
        if relative not in bindings:
            raise ValueError(f"capability pack binding missing:{relative}")
        documents[filename] = _load_json(pack_root / filename)

    registry = documents["capability_registry.json"]
    if registry.get("version") != "1.0.0" or registry.get("model_authority") != "LOCAL_CANDIDATE_ONLY":
        raise ValueError("capability pack version or authority invalid")
    root_model = documents["root_model_contract.json"]
    identity = root_model.get("identity") or {}
    unfenced = root_model.get("unfenced_reasoning") or {}
    if (
        root_model.get("schema_id") != "W7TP_XIAOJ_ROOT_MODEL_8B_V1"
        or identity.get("system_root_model") is not True
        or identity.get("parameter_class") != "8B"
        or unfenced.get("execution_is_unfenced") is not False
        or root_model.get("red_team_alert", {}).get("enabled") is not True
    ):
        raise ValueError("root model contract invalid")
    voice_routing = documents["voice_pronunciation_routing_contract.json"]
    if (
        voice_routing.get("schema_id") != "W7TP_XIAOJ_MULTI_PRONUNCIATION_ROUTING_V1"
        or voice_routing.get("provider_registry_contract", {}).get("providers_may_be_multiple") is not True
        or voice_routing.get("fallback", {}).get("never_call_taiji01_model") is not True
    ):
        raise ValueError("voice pronunciation routing contract invalid")
    return {
        "root": pack_root,
        "registry": registry,
        "skill_index": documents["founder_all_skills_8d_index.json"],
        "routing": documents["routing_policy.json"],
        "root_model": root_model,
        "voice_routing": voice_routing,
        "tool_contracts": documents["tool_contracts.json"],
        "source_manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
    }


def _select_capability_route(query: str, pack: Mapping[str, Any], identity_class: str) -> dict[str, Any]:
    registry = pack["registry"]
    routing = pack["routing"]
    lowered = query.casefold()
    skills = registry.get("skills") or []
    ranked: list[tuple[int, int, Mapping[str, Any]]] = []
    for index, skill in enumerate(skills):
        matched = [str(trigger) for trigger in skill.get("triggers") or [] if str(trigger).casefold() in lowered]
        ranked.append((sum(len(item) for item in matched), -index, {**skill, "matched_triggers": matched}))
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    selected = ranked[0][2] if ranked and ranked[0][0] > 0 else next(
        skill for skill in skills if skill.get("id") == routing["selection"]["no_match_skill"]
    )

    hard_markers = [
        marker for marker in routing.get("hard_block_markers") or [] if str(marker).casefold() in lowered
    ]
    if hard_markers:
        selected = next(skill for skill in skills if skill.get("id") == routing["selection"]["unsafe_intent_skill"])

    claimed_identity = identity_class if identity_class in {"founder", "general_member", "unknown"} else "unknown"
    founder_packets: list[dict[str, Any]] = []
    if claimed_identity == "founder":
        terms = _query_terms(query)
        packet_scores: list[tuple[int, str, dict[str, Any]]] = []
        for packet in pack["skill_index"].get("skill_packets") or []:
            intent = packet.get("D1_INTENT") or {}
            skill_id = str(packet.get("skill_id", ""))
            skill_name = str(packet.get("skill_name", ""))
            description = str(intent.get("description", ""))
            triggers = [str(item) for item in intent.get("triggers") or []]
            searchable = " ".join([skill_id, skill_name, description, *triggers]).casefold()
            score = 0
            if skill_id.casefold() in lowered or skill_name.casefold() in lowered:
                score += 1000
            score += sum(80 + min(len(trigger), 40) for trigger in triggers if trigger.casefold() in lowered)
            score += sum(10 + min(len(term), 20) for term in terms if term in searchable)
            if packet.get("status") in {"READY_LOCAL", "READY_MCP"}:
                score += 5
            if score > 0:
                packet_scores.append((score, skill_id, packet))
        packet_scores.sort(key=lambda item: (-item[0], item[1]))
        founder_packets = [item[2] for item in packet_scores[:2]]

    selected_packet = founder_packets[0] if founder_packets else None
    selected_status = selected_packet.get("status") if selected_packet else None
    if selected_packet and not hard_markers:
        disposition = {
            "READY_LOCAL": "CANDIDATE_ONLY",
            "READY_MCP": "CANDIDATE_ONLY",
            "NEEDS_CONNECTOR": "HOLD_CONNECTOR_REQUIRED",
            "NEEDS_LOCAL_ADAPTER": "HOLD_LOCAL_ADAPTER_REQUIRED",
            "PLATFORM_INTERNAL_UNEXPORTABLE": "HOLD_PLATFORM_INTERNAL_UNEXPORTABLE",
        }[selected_status]
    else:
        disposition = "BLOCK" if hard_markers else "CANDIDATE_ONLY"
    return {
        "flow": routing["flow"],
        "d1_intent_projection": {
            "normalized_terms": _query_terms(query),
            "query_sha256": sha256_bytes(query.encode("utf-8")),
            "raw_input_retained": False,
        },
        "identity_projection": {
            "claimed_identity": claimed_identity,
            "skill_scope_verified": claimed_identity == "founder",
            "authority_verified": False,
            "production_authority_verified": False,
            "effective_profile": (
                "FOUNDER_ALL_SKILLS"
                if claimed_identity == "founder" and not hard_markers
                else "general_member_minimum_privilege"
            ),
            "member_boundary": "OWNER_ONLY" if claimed_identity == "founder" else "MINIMUM_PRIVILEGE",
            "self_elevation_allowed": False,
        },
        "skill_lookup": {
            "selected_skill": selected_packet.get("skill_id") if selected_packet else selected.get("id"),
            "selected_status": selected_status,
            "purpose": (
                (selected_packet.get("D1_INTENT") or {}).get("description")
                if selected_packet
                else selected.get("purpose")
            ),
            "matched_triggers": (
                (selected_packet.get("D1_INTENT") or {}).get("triggers", [])
                if selected_packet
                else selected.get("matched_triggers", [])
            ),
            "registry_version": registry.get("version"),
            "lookup_method": "DETERMINISTIC_INTEGER_TRIGGER_SCORE",
            "matched_packet_count": len(founder_packets),
            "max_packets_per_query": 2,
        },
        "matched_skill_packets": founder_packets,
        "tool_contract_validation": {
            "allowed_mcp_tools": [
                tool.get("name") for tool in pack["tool_contracts"].get("mcp_exposed_tools") or []
            ],
            "side_effect_class": "NONE",
            "validated": True,
        },
        "total_field_gate": {
            "disposition": disposition,
            "hard_block_markers": hard_markers,
            "receive_candidate_required": True,
            "model_commit_allowed": False,
        },
        "capability_pack_source_manifest_sha256": pack["source_manifest_sha256"],
        "root_model_projection": {
            "schema_id": pack["root_model"].get("schema_id"),
            "runtime_model_name": (pack["root_model"].get("identity") or {}).get("runtime_model_name"),
            "base_model": (pack["root_model"].get("identity") or {}).get("base_model"),
            "parameter_class": (pack["root_model"].get("identity") or {}).get("parameter_class"),
            "core_model_count": (pack["root_model"].get("identity") or {}).get("core_model_count"),
            "unified_model_mode": (
                pack["root_model"].get("unified_model_architecture") or {}
            ).get("mode"),
            "frontbrain_is_separate_model": (
                pack["root_model"].get("unified_model_architecture") or {}
            ).get("frontbrain_is_separate_model"),
            "backbrain_is_separate_model": (
                pack["root_model"].get("unified_model_architecture") or {}
            ).get("backbrain_is_separate_model"),
            "unfenced_reasoning": (pack["root_model"].get("unfenced_reasoning") or {}).get("enabled"),
            "execution_is_unfenced": (pack["root_model"].get("unfenced_reasoning") or {}).get(
                "execution_is_unfenced"
            ),
            "cloud_context_detail_policy": (
                pack["root_model"].get("cloud_candidate_precision") or {}
            ).get("context_detail_policy"),
            "red_team_alert_enabled": (pack["root_model"].get("red_team_alert") or {}).get("enabled"),
        },
        "voice_routing_projection": {
            "schema_id": pack["voice_routing"].get("schema_id"),
            "principle": pack["voice_routing"].get("principle"),
            "task_profiles": [
                item.get("profile") for item in pack["voice_routing"].get("task_profiles") or []
            ],
            "provider_names_runtime_discovered": (
                pack["voice_routing"].get("provider_registry_contract") or {}
            ).get("provider_names_are_runtime_discovered"),
            "homepod_role": (pack["voice_routing"].get("homepod") or {}).get("role"),
            "emotionless_recitation_accepted": (
                pack["voice_routing"].get("non_negotiable_quality_gate") or {}
            ).get("emotionless_recitation_accepted"),
            "emotionless_failure_state": (
                pack["voice_routing"].get("non_negotiable_quality_gate") or {}
            ).get("failure_state"),
            "reference_endpoint_state": (
                pack["voice_routing"].get("reference_only_endpoint_observation") or {}
            ).get("state"),
            "reference_endpoint_evidence_status": (
                pack["voice_routing"].get("reference_only_endpoint_observation") or {}
            ).get("evidence_status"),
        },
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def _finalize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet


def _decision_result(
    decision: str,
    *,
    reason: str,
    candidate_packet: Mapping[str, Any] | None,
    dynamic_context_packet: Mapping[str, Any] | None,
    authority_ref: Any,
) -> dict[str, Any]:
    candidate_digest = canonical_sha256(candidate_packet) if candidate_packet is not None else None
    context_digest = (
        str(dynamic_context_packet.get("packet_sha256"))
        if dynamic_context_packet is not None
        else None
    )
    authority_digest = (
        sha256_bytes(
            json.dumps(authority_ref, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        if authority_ref not in (None, "", {})
        else None
    )
    return {
        "state": decision,
        "decision": decision,
        "reason": reason,
        "decision_authority": "ACTIVE_LOCAL_TOTAL_FIELD_OWNER",
        "candidate_authority": False,
        "execution_authorized": False,
        "candidate_packet_sha256": candidate_digest,
        "dynamic_context_packet_sha256": context_digest,
        "authority_ref_sha256": authority_digest,
        "policy": {
            "candidate_only": True,
            "model_decision_is_authoritative": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "canonical_pointer_write": False,
        },
    }


def _valid_dynamic_context_evidence(packet: Any) -> bool:
    if not isinstance(packet, Mapping):
        return False
    if packet.get("state") != "TOTAL_FIELD_DYNAMIC_CONTEXT_READY":
        return False
    packet_sha256 = packet.get("packet_sha256")
    if not isinstance(packet_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", packet_sha256) is None:
        return False
    unsigned_packet = dict(packet)
    unsigned_packet.pop("packet_sha256", None)
    if canonical_sha256(unsigned_packet) != packet_sha256:
        return False
    if not (packet.get("source_bindings") or packet.get("context_items")):
        return False
    policy = packet.get("policy")
    return isinstance(policy, Mapping) and policy.get("evidence_only") is True


def _breakpoint_disposition(candidate_packet: Mapping[str, Any]) -> str:
    values: list[Any] = [candidate_packet.get("breakpoint_disposition")]
    for key in ("breakpoint", "breakpoint_gate", "governance"):
        nested = candidate_packet.get(key)
        if isinstance(nested, Mapping):
            values.extend(nested.get(field) for field in ("decision", "disposition", "state"))
    normalized = {str(value).strip().upper() for value in values if value not in (None, "")}
    if any(value in {"DENY", "BLOCK", "BLOCK_BREAKPOINT_OR_POLICY"} for value in normalized):
        return "DENY"
    if any(value == "HOLD" or value.startswith("HOLD_") for value in normalized):
        return "HOLD"
    return "ALLOW"


def receive_candidate(
    candidate_packet: Mapping[str, Any],
    dynamic_context_packet: Mapping[str, Any] | None,
    authority_ref: Any,
) -> dict[str, Any]:
    """Apply the active local Total Field candidate-only decision contract."""

    candidate = dict(candidate_packet) if isinstance(candidate_packet, Mapping) else None
    context = dict(dynamic_context_packet) if isinstance(dynamic_context_packet, Mapping) else None
    if not _valid_dynamic_context_evidence(context):
        return _decision_result(
            "HOLD_EVIDENCE_INCOMPLETE",
            reason="dynamic_context_packet is missing, unbound, or has no governed evidence",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )
    if authority_ref in (None, "", {}):
        return _decision_result(
            "HOLD_AUTHORITY_INCOMPLETE",
            reason="authority_ref is required",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )
    if candidate is None:
        return _decision_result(
            "HOLD_EVIDENCE_INCOMPLETE",
            reason="candidate_packet is missing",
            candidate_packet=None,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )

    breakpoint = _breakpoint_disposition(candidate)
    if breakpoint == "DENY":
        return _decision_result(
            "BLOCK_BREAKPOINT_OR_POLICY",
            reason="breakpoint or policy denied the candidate before decision",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )
    if breakpoint == "HOLD":
        return _decision_result(
            "HOLD_BREAKPOINT_OR_POLICY",
            reason="breakpoint or policy held the candidate before decision",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )

    allowed_candidate_states = {
        "CANDIDATE_ONLY",
        "CANDIDATE_ONLY_WITH_FORBIDDEN_FIELDS_REMOVED",
    }
    if candidate.get("state") not in allowed_candidate_states:
        return _decision_result(
            "HOLD_EVIDENCE_INCOMPLETE",
            reason="candidate state is unknown and cannot be normalized",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )
    if candidate.get("execution_authorized") not in (None, False) or any(
        candidate.get(key) not in (None, "", False)
        for key in ("decision", "total_field_decision", "verdict")
    ):
        return _decision_result(
            "HOLD_EVIDENCE_INCOMPLETE",
            reason="candidate supplied a decision or execution claim that cannot be promoted",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_ref=authority_ref,
        )

    return _decision_result(
        "ALLOW_CANDIDATE_ACCEPTED",
        reason="candidate accepted for governed review without execution authority",
        candidate_packet=candidate,
        dynamic_context_packet=context,
        authority_ref=authority_ref,
    )


def build_active_authority_receive_candidate(
    *,
    repo_root: str | Path = ROOT,
    nonce_ledger: Any,
    signature_verifier: Any,
    trusted_verifier_refs: Collection[str],
) -> Callable[
    [Mapping[str, Any], Mapping[str, Any] | None, Any],
    dict[str, Any],
]:
    """
    Build the future formal candidate ingress as a runtime-bound closure.

    The trusted runtime supplies the persistent nonce ledger and signature verifier
    once at startup. Candidate callers receive only the returned three-argument
    receiver and cannot inject resolver, verifier, ledger, or Founder/D8 fields.
    This builder does not create or modify ACTIVE_TOTAL_FIELD_AUTHORITY.
    """
    try:
        resolver_module = importlib.import_module(
            ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVER_MODULE
        )
        adapter_module = importlib.import_module(
            ACTIVE_TOTAL_FIELD_AUTHORITY_ADAPTER_MODULE
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "HOLD_AUTHORITY_RUNTIME_COMPONENT_UNAVAILABLE"
        ) from exc

    authority_resolver = getattr(
        resolver_module,
        "resolve_active_total_field_authority",
        None,
    )
    authority_adapter = getattr(
        adapter_module,
        "receive_candidate_authority_bound",
        None,
    )
    if not callable(authority_resolver) or not callable(authority_adapter):
        raise RuntimeError("BLOCK_AUTHORITY_RUNTIME_COMPONENT_INVALID")

    bound_root = Path(repo_root).resolve()
    bound_trusted_verifier_refs = tuple(str(item) for item in trusted_verifier_refs)
    owner_receive_candidate = receive_candidate

    def authority_bound_receiver(
        candidate_packet: Mapping[str, Any],
        dynamic_context_packet: Mapping[str, Any] | None,
        authority_ref: Any,
    ) -> dict[str, Any]:
        if authority_ref != ACTIVE_TOTAL_FIELD_AUTHORITY_LOOKUP_REF:
            return _decision_result(
                "HOLD_AUTHORITY_INCOMPLETE",
                reason=(
                    "authority_ref must be the fixed ACTIVE_TOTAL_FIELD_AUTHORITY "
                    "runtime lookup reference"
                ),
                candidate_packet=(
                    dict(candidate_packet)
                    if isinstance(candidate_packet, Mapping)
                    else None
                ),
                dynamic_context_packet=(
                    dict(dynamic_context_packet)
                    if isinstance(dynamic_context_packet, Mapping)
                    else None
                ),
                authority_ref=authority_ref,
            )

        try:
            result = authority_adapter(
                candidate_packet,
                dynamic_context_packet,
                repo_root=bound_root,
                nonce_ledger=nonce_ledger,
                signature_verifier=signature_verifier,
                trusted_verifier_refs=bound_trusted_verifier_refs,
                authority_resolver=authority_resolver,
                owner_receive_candidate=owner_receive_candidate,
            )
        except Exception as exc:
            return _decision_result(
                "HOLD_AUTHORITY_BOUND_RECEIVER_FAILED",
                reason=(
                    "authority-bound candidate receiver failed closed: "
                    f"{type(exc).__name__}"
                ),
                candidate_packet=(
                    dict(candidate_packet)
                    if isinstance(candidate_packet, Mapping)
                    else None
                ),
                dynamic_context_packet=(
                    dict(dynamic_context_packet)
                    if isinstance(dynamic_context_packet, Mapping)
                    else None
                ),
                authority_ref=authority_ref,
            )

        if not isinstance(result, Mapping):
            return _decision_result(
                "BLOCK_AUTHORITY_BOUND_RESULT_INVALID",
                reason="authority-bound candidate receiver returned a non-mapping result",
                candidate_packet=(
                    dict(candidate_packet)
                    if isinstance(candidate_packet, Mapping)
                    else None
                ),
                dynamic_context_packet=(
                    dict(dynamic_context_packet)
                    if isinstance(dynamic_context_packet, Mapping)
                    else None
                ),
                authority_ref=authority_ref,
            )

        if (
            result.get("candidate_authority") is not False
            or result.get("execution_authorized") is not False
            or result.get("formal_decision_authority") not in (None, False)
            or result.get("formal_seal_authority") not in (None, False)
        ):
            return _decision_result(
                "BLOCK_AUTHORITY_BOUNDARY_VIOLATION",
                reason="authority-bound result attempted to grant forbidden authority",
                candidate_packet=(
                    dict(candidate_packet)
                    if isinstance(candidate_packet, Mapping)
                    else None
                ),
                dynamic_context_packet=(
                    dict(dynamic_context_packet)
                    if isinstance(dynamic_context_packet, Mapping)
                    else None
                ),
                authority_ref=authority_ref,
            )

        output = dict(result)
        output["candidate_authority"] = False
        output["execution_authorized"] = False
        output["formal_decision_authority"] = False
        output["formal_seal_authority"] = False
        output.setdefault("policy", {})
        if isinstance(output["policy"], Mapping):
            policy = dict(output["policy"])
        else:
            policy = {}
        policy.update(
            {
                "candidate_only": True,
                "active_pointer_write": False,
                "db_write": False,
                "deploy": False,
                "restart": False,
                "formal_send": False,
            }
        )
        output["policy"] = policy
        return output

    return authority_bound_receiver


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _resolve_inside(root: Path, relative_path: str | Path) -> Path:
    candidate = (root / relative_path).resolve()
    candidate.relative_to(root.resolve())
    return candidate


def _path_is_allowed(relative_path: str) -> bool:
    return not any(part.lower() in DENIED_PATH_MARKERS for part in Path(relative_path).parts)


def _redact_personal_data(text: str) -> str:
    redacted = text
    for pattern, replacement in PERSONAL_DATA_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _contains_sensitive_value(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_VALUE_PATTERNS)


def _query_terms(query: str) -> list[str]:
    lowered_query = query.lower()
    raw_terms = list(
        dict.fromkeys(re.findall(r"[a-zA-Z0-9_./:-]{2,}|[\u3400-\u9fff]{2,}", query.lower()))
    )
    terms: list[str] = []
    for raw in raw_terms:
        if raw not in terms:
            terms.append(raw)
    for marker, aliases in QUERY_ALIASES.items():
        if marker not in lowered_query:
            continue
        for alias in aliases:
            if alias not in terms:
                terms.append(alias)
    terms = terms[:MAX_QUERY_TERMS]
    if len(terms) >= MAX_QUERY_TERMS:
        return terms
    # Add Chinese n-grams only after preserving terms from the complete query.
    # This keeps trailing identifiers such as "voice runtime" searchable.
    for raw in raw_terms:
        if not re.fullmatch(r"[\u3400-\u9fff]+", raw):
            continue
        for width in (2, 3, 4):
            for index in range(max(0, len(raw) - width + 1)):
                candidate = raw[index : index + width]
                if candidate not in terms:
                    terms.append(candidate)
                if len(terms) >= MAX_QUERY_TERMS:
                    return terms
    return terms


def _match_score(text: str, terms: Iterable[str]) -> tuple[int, list[str]]:
    lowered = text.lower()
    matched = [term for term in terms if term in lowered]
    score = sum(min(len(term), 24) for term in matched)
    return score, matched


def _snippet(text: str, terms: list[str]) -> str | None:
    if _contains_sensitive_value(text):
        return None
    lowered = text.lower()
    offsets = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    start = max(0, (min(offsets) if offsets else 0) - 240)
    excerpt = text[start : start + MAX_SNIPPET_CHARS]
    return _redact_personal_data(excerpt)


def _file_binding(root: Path, path: Path, *, source_kind: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "relative_path": _relative_path(root, path),
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
        "source_kind": source_kind,
    }


def _evidence_class(relative_path: str) -> str:
    if relative_path.startswith("schemas/"):
        return "CONTRACT_DEFINITION_NOT_RUNTIME_PROOF"
    if relative_path.startswith("configs/"):
        return "CONFIGURATION_NOT_RUNTIME_PROOF"
    if relative_path.startswith("manifests/"):
        return "MANIFEST_DECLARATION_REQUIRES_ARTIFACT_VALIDATION"
    if relative_path.startswith("tools/"):
        return "IMPLEMENTATION_SOURCE_NOT_EXECUTION_PROOF"
    if relative_path.startswith("docs/"):
        return "DOCUMENTATION_NOT_RUNTIME_PROOF"
    if relative_path.startswith("runtime/developer_memory/"):
        return "CONTEXT_SNAPSHOT_NOT_RUNTIME_PROOF"
    if relative_path.startswith("runtime/total_field/"):
        return "TOTAL_FIELD_ARTIFACT_REQUIRES_STATE_TIME_AND_BINDING_VALIDATION"
    return "READ_ONLY_EVIDENCE_REQUIRES_VALIDATION"


def _hold_packet(state: str, *, query: str, reason: str, generated_at: str) -> dict[str, Any]:
    return _finalize_packet(
        {
            "schema_version": "1.0",
            "state": state,
            "packet_type": "TOTAL_FIELD_MODEL_DYNAMIC_CONTEXT_EVIDENCE",
            "generated_at": generated_at,
            "query": _redact_personal_data(query[:2000]),
            "reason": reason,
            "authority": "READ_ONLY_CONTEXT_EVIDENCE_NO_DECISION_AUTHORITY",
            "policy": {
                "evidence_only": True,
                "candidate_only": True,
                "db_write": False,
                "deploy": False,
                "restart": False,
                "router_write": False,
                "canonical_pointer_write": False,
                "personal_data_included": False,
            },
        }
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _bootstrap_bindings(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], set[str], Path]:
    bootstrap_path = _resolve_inside(root, BOOTSTRAP_RELATIVE_PATH)
    bootstrap = _load_json(bootstrap_path)
    memory_root = _resolve_inside(root, MEMORY_ROOT_RELATIVE_PATH)
    bindings = [_file_binding(root, bootstrap_path, source_kind="dynamic_context_bootstrap")]
    for relative in bootstrap.get("read_first", []):
        if not isinstance(relative, str):
            raise ValueError("bootstrap read_first contains a non-string path")
        path = _resolve_inside(memory_root, relative)
        if not path.is_file():
            raise FileNotFoundError(path)
        bindings.append(_file_binding(root, path, source_kind="bootstrap_read_first"))
    policy = bootstrap.get("retrieval_policy") or {}
    excluded = {str(item) for item in policy.get("exclude_categories_by_default", [])}
    return bootstrap, bindings, excluded, memory_root


def _memory_items(
    root: Path,
    memory_root: Path,
    excluded_categories: set[str],
    terms: list[str],
) -> tuple[list[tuple[int, dict[str, Any]]], list[str]]:
    index_path = memory_root / "indexes/memory_index.jsonl"
    rows = []
    for line_number, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"memory index line {line_number} is not an object")
        rows.append(value)

    ranked: list[tuple[int, dict[str, Any]]] = []
    issues: list[str] = []
    for row in rows:
        category = str(row.get("category", ""))
        if category in excluded_categories or str(row.get("status")) == "quarantined":
            continue
        record_relative = str(row.get("record_path", ""))
        if not record_relative or not _path_is_allowed(record_relative):
            continue
        record_path = _resolve_inside(memory_root, record_relative)
        if not record_path.is_file() or record_path.stat().st_size > MAX_FILE_BYTES:
            continue
        data = record_path.read_bytes()
        text = data.decode("utf-8")
        record = json.loads(text)
        source = record.get("source") if isinstance(record, dict) else None
        row_source_sha = str(row.get("source_sha256", ""))
        record_source_sha = str(source.get("sha256", "")) if isinstance(source, dict) else ""
        memory_id = str(record.get("memory_id", "")) if isinstance(record, dict) else ""
        if not row_source_sha or row_source_sha != record_source_sha or memory_id != row_source_sha:
            issues.append(f"MEMORY_BINDING_MISMATCH:{record_relative}")
            continue
        searchable = " ".join(
            [
                category,
                str(row.get("source_path", "")),
                record_relative,
                text,
            ]
        )
        score, matched = _match_score(searchable, terms)
        if terms and score == 0:
            continue
        source_path_value = str(row.get("source_path", ""))
        source_current_sha256 = None
        source_current_matches_snapshot = None
        try:
            source_path = _resolve_inside(root, source_path_value)
            if source_path.is_file():
                source_current_sha256 = sha256_bytes(source_path.read_bytes())
                source_current_matches_snapshot = source_current_sha256 == row_source_sha
        except (OSError, ValueError):
            pass
        item = {
            "relative_path": _relative_path(root, record_path),
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "source_kind": "verified_memory_record",
            "evidence_class": (
                "HISTORICAL_SNAPSHOT_NOT_RUNTIME_PROOF"
                if row.get("status") == "historical_snapshot"
                else "ACTIVE_DECLARATION_REQUIRES_CURRENT_SOURCE_MATCH"
            ),
            "category": category,
            "status": row.get("status"),
            "trust": row.get("trust"),
            "source_relative_path": source_path_value,
            "source_snapshot_sha256": row_source_sha,
            "source_current_sha256": source_current_sha256,
            "source_current_matches_snapshot": source_current_matches_snapshot,
            "matched_terms": matched[:8],
            "snippet": _snippet(text, terms),
        }
        ranked.append((score, item))
    return ranked, issues


def _iter_workspace_files(root: Path) -> Iterable[Path]:
    for relative_root in SAFE_SEARCH_ROOTS:
        search_root = _resolve_inside(root, relative_root)
        if not search_root.is_dir():
            continue
        for path in sorted(search_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            relative = _relative_path(root, path)
            if relative in EXCLUDED_SEARCH_PATHS:
                continue
            if not _path_is_allowed(relative):
                continue
            try:
                if path.stat().st_size <= MAX_FILE_BYTES:
                    yield path
            except OSError:
                continue


def _workspace_items(root: Path, terms: list[str]) -> tuple[list[tuple[int, dict[str, Any]]], int]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    sensitive_omitted = 0
    for path in _iter_workspace_files(root):
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        relative = _relative_path(root, path)
        path_score, path_matched = _match_score(relative, terms)
        content_score, content_matched = _match_score(text, terms)
        score = path_score * 8 + content_score
        matched = list(dict.fromkeys(path_matched + content_matched))
        if terms and score == 0:
            continue
        if _contains_sensitive_value(text):
            sensitive_omitted += 1
            continue
        ranked.append(
            (
                score,
                {
                    "relative_path": relative,
                    "size_bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "source_kind": "current_workspace_evidence",
                    "evidence_class": _evidence_class(relative),
                    "matched_terms": matched[:8],
                    "snippet": _snippet(text, terms),
                },
            )
        )
    return ranked, sensitive_omitted


def build_dynamic_context(
    query: str,
    *,
    root: str | Path = ROOT,
    max_items: int = 8,
    identity_class: str = "unknown",
    generated_at: str | None = None,
) -> dict[str, Any]:
    workspace_root = Path(root).resolve()
    timestamp = generated_at or utc_now()
    if not query.strip():
        query = "current total field governed workspace context"
    if len(query) > 20_000:
        return _hold_packet(
            "HOLD_TOTAL_FIELD_CONTEXT_QUERY_TOO_LARGE",
            query=query,
            reason="query exceeds 20000 characters",
            generated_at=timestamp,
        )
    max_items = max(1, min(int(max_items), 20))
    try:
        capability_pack = _load_capability_pack(workspace_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _hold_packet(
            "HOLD_LOCAL_CAPABILITY_PACK_INVALID",
            query=query,
            reason=f"{type(exc).__name__}:{exc}",
            generated_at=timestamp,
        )
    try:
        bootstrap, bindings, excluded, memory_root = _bootstrap_bindings(workspace_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _hold_packet(
            "HOLD_TOTAL_FIELD_CONTEXT_SOURCE_UNREADABLE",
            query=query,
            reason=f"{type(exc).__name__}:{exc}",
            generated_at=timestamp,
        )

    terms = _query_terms(query)
    try:
        memory_ranked, binding_issues = _memory_items(workspace_root, memory_root, excluded, terms)
        workspace_ranked, sensitive_omitted = _workspace_items(workspace_root, terms)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _hold_packet(
            "HOLD_TOTAL_FIELD_CONTEXT_SOURCE_UNREADABLE",
            query=query,
            reason=f"{type(exc).__name__}:{exc}",
            generated_at=timestamp,
        )
    if binding_issues:
        return _hold_packet(
            "HOLD_TOTAL_FIELD_CONTEXT_HASH_MISMATCH",
            query=query,
            reason=";".join(binding_issues[:8]),
            generated_at=timestamp,
        )

    combined = memory_ranked + workspace_ranked
    combined.sort(key=lambda pair: (-pair[0], pair[1]["relative_path"]))
    selected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for _, item in combined:
        relative = str(item["relative_path"])
        if relative in seen_paths:
            continue
        selected.append(item)
        seen_paths.add(relative)
        if len(selected) >= max_items:
            break

    retrieval_state = "MATCHED_CURRENT_AND_SNAPSHOT_EVIDENCE" if selected else "NOT_YET_EVIDENCED"
    packet = {
        "schema_version": "1.0",
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "packet_type": "TOTAL_FIELD_MODEL_DYNAMIC_CONTEXT_EVIDENCE",
        "generated_at": timestamp,
        "query": _redact_personal_data(query[:2000]),
        "retrieval_state": retrieval_state,
        "claim_gate": "EVIDENCE_REQUIRES_TOTAL_FIELD_VALIDATION",
        "authority": "READ_ONLY_CONTEXT_EVIDENCE_NO_DECISION_AUTHORITY",
        "source_bootstrap_generated_at": bootstrap.get("generated_at"),
        "source_bindings": bindings,
        "context_items": selected,
        "excluded_categories": sorted(excluded),
        "sensitive_files_omitted": sensitive_omitted,
        "capability_route": (
            _select_capability_route(query, capability_pack, identity_class)
            if capability_pack is not None
            else None
        ),
        "policy": {
            "evidence_only": True,
            "candidate_only": True,
            "verified_claim_requires_matching_evidence_path_and_sha256": True,
            "historical_snapshot_is_not_current_runtime_proof": True,
            "schema_config_manifest_source_and_docs_are_not_runtime_proof": True,
            "missing_evidence_must_be_reported_as_not_yet_evidenced": True,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "canonical_pointer_write": False,
            "personal_data_included": False,
        },
        "governance_tensor": {
            "Identity": "LOCAL_XIAOJ_MODEL_CONTEXT",
            "Intent": "READ_ONLY_DYNAMIC_EVIDENCE_RETRIEVAL",
            "Authority": "CONTEXT_ONLY_NO_DECISION",
            "Relation": "TOTAL_FIELD_TO_LOCAL_MODEL",
            "Resource": "GOVERNED_WORKSPACE_EVIDENCE",
            "Time": timestamp,
            "Risk": "FAIL_CLOSED_ON_UNREADABLE_OR_HASH_MISMATCH",
            "Governance": "MODEL_OUTPUT_REMAINS_CANDIDATE",
        },
    }
    return _finalize_packet(packet)


CAPABILITY_MISSING_FIELDS = frozenset(
    {
        "task_id",
        "receiver_id",
        "receiver_version",
        "current_intent_ref",
        "missing_capability_id",
        "missing_input_class",
        "missing_schema_version",
        "missing_lookup_resource",
        "missing_verification_capability",
        "current_available_capabilities",
        "current_context_refs",
        "evidence",
    }
)
SENSITIVE_INFORMATION_ROUTES = {
    "PUBLIC": "CLOUD_POLICY_ELIGIBLE",
    "DEIDENTIFIED_TECHNICAL": "CLOUD_POLICY_ELIGIBLE",
    "LOCAL_INTERNAL": "LOCAL_ONLY_DEFAULT",
    "BUSINESS_SECRET": "CLOUD_PLAINTEXT_FORBIDDEN",
    "PERSONAL_DATA": "CLOUD_PLAINTEXT_FORBIDDEN",
    "CREDENTIAL_SECRET": "MODEL_CONTEXT_FORBIDDEN",
    "PROTECTED_ADI_REFERENCE": "REFERENCE_ONLY",
    "UNKNOWN": "FAIL_CLOSED_LOCAL_ONLY",
}
TASK_CLASSES = frozenset(
    {
        "REASONING_TASK",
        "CAPABILITY_TASK",
        "DATA_ACCESS_TASK",
        "OPERATION_TASK",
        "MIXED_TASK",
    }
)
MAX_CAPABILITY_PACKET_TTL_SECONDS = 3600


def _require_sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"HASH_INVALID:{path}")
    return value


def _parse_packet_time(value: Any, path: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"DATETIME_REQUIRED:{path}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"DATETIME_INVALID:{path}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"DATETIME_TIMEZONE_REQUIRED:{path}")
    return parsed.astimezone(timezone.utc)


def normalize_capability_missing_report(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an exact Local-LLM gap; never select a provider or expose data."""
    if set(value) != CAPABILITY_MISSING_FIELDS:
        raise ValueError("CAPABILITY_MISSING_REPORT_SHAPE_MISMATCH")
    for field in CAPABILITY_MISSING_FIELDS - {
        "current_available_capabilities",
        "current_context_refs",
        "evidence",
    }:
        if not isinstance(value.get(field), str) or not str(value[field]).strip():
            raise ValueError(f"CAPABILITY_MISSING_REPORT_FIELD_INVALID:{field}")
    for field in ("current_available_capabilities", "current_context_refs", "evidence"):
        items = value.get(field)
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise ValueError(f"CAPABILITY_MISSING_REPORT_FIELD_INVALID:{field}")
    report = {
        "schema_id": "W7TP_CAPABILITY_MISSING_REPORT_V1",
        **deepcopy(dict(value)),
        "provider_selected": None,
        "authority": False,
        "candidate_only": True,
        "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
    }
    return _finalize_packet(report)


def classify_total_field_task(
    *,
    reasoning: bool = False,
    capability_gap: bool = False,
    data_access: bool = False,
    operation: bool = False,
) -> str:
    enabled = sum(bool(item) for item in (reasoning, capability_gap, data_access, operation))
    if enabled > 1:
        return "MIXED_TASK"
    if operation:
        return "OPERATION_TASK"
    if data_access:
        return "DATA_ACCESS_TASK"
    if capability_gap:
        return "CAPABILITY_TASK"
    return "REASONING_TASK"


def route_sensitive_information(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Route from exact governed metadata; model confidence is ignored."""
    data_class = str(metadata.get("data_class") or "UNKNOWN").upper()
    if data_class not in SENSITIVE_INFORMATION_ROUTES:
        data_class = "UNKNOWN"
    route = SENSITIVE_INFORMATION_ROUTES[data_class]
    return {
        "state": "TOTAL_FIELD_SENSITIVE_ROUTE_DECIDED",
        "data_class": data_class,
        "route": route,
        "cloud_plaintext_allowed": data_class in {"PUBLIC", "DEIDENTIFIED_TECHNICAL"},
        "model_context_allowed": data_class != "CREDENTIAL_SECRET",
        "reference_only": data_class == "PROTECTED_ADI_REFERENCE",
        "decision_inputs": {
            key: metadata.get(key)
            for key in (
                "object_class",
                "data_class",
                "namespace",
                "owner",
                "coordinate",
                "policy_ref",
                "d7_ref",
                "d8_ref",
                "evidence_ref",
            )
        },
        "model_confidence_used": False,
        "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
    }


def build_total_field_capability_requirement_packet(
    report: Mapping[str, Any],
    *,
    target_base_state: Mapping[str, Any],
    reusable_capability_refs: Collection[str],
    created_at: str,
    ttl_seconds: int = 900,
) -> dict[str, Any]:
    if report.get("schema_id") != "W7TP_CAPABILITY_MISSING_REPORT_V1":
        raise ValueError("CAPABILITY_MISSING_REPORT_REQUIRED")
    if report.get("authority") is not False or report.get("candidate_only") is not True:
        raise ValueError("CAPABILITY_REPORT_AUTHORITY_INVALID")
    if not 1 <= ttl_seconds <= MAX_CAPABILITY_PACKET_TTL_SECONDS:
        raise ValueError("CAPABILITY_REQUIREMENT_TTL_INVALID")
    created = _parse_packet_time(created_at, "created_at")
    expires = created + timedelta(seconds=ttl_seconds)
    packet = {
        "schema_id": "W7TP_TOTAL_FIELD_CAPABILITY_REQUIREMENT_PACKET_V1",
        "D1_INTENT": {
            "intent_ref": report["current_intent_ref"],
            "required_capability_id": report["missing_capability_id"],
        },
        "D2_STATE": {
            "receiver_id": report["receiver_id"],
            "receiver_version": report["receiver_version"],
            "target_base_state": deepcopy(dict(target_base_state)),
            "current_available_capabilities": list(report["current_available_capabilities"]),
        },
        "D3_COORDINATE": {
            "task_id": report["task_id"],
            "required_object_id": report["missing_capability_id"],
            "namespace": "W7TP.CAPABILITY",
            "version": report["missing_schema_version"],
            "receiver_id": report["receiver_id"],
        },
        "D4_EVIDENCE": {
            "gap_report_sha256": report["packet_sha256"],
            "evidence_refs": list(report["evidence"]),
            "reusable_capability_refs": sorted(set(reusable_capability_refs)),
        },
        "D5_EXECUTION_POLICY": {
            "allowed_provider_actions": ["ANALYZE", "GENERATE", "COMPLETE", "REPAIR", "TRANSFORM", "PROPOSE"],
            "forbidden_provider_actions": ["ACCEPT_SELF", "PROMOTE_SELF", "EXECUTE", "MODIFY_CANONICAL", "ISSUE_OPERATION_PACKET"],
        },
        "D6_GENERATIVE_COMPLETION": {
            "target_base_state": deepcopy(dict(target_base_state)),
            "minimum_capability_delta": [report["missing_capability_id"]],
            "references": sorted(set(reusable_capability_refs)),
            "coordinates": [report["missing_lookup_resource"]],
            "reconstruction_rules": ["REUSE_TARGET_NATIVE_FIRST", "GENERATE_ONLY_MISSING_CAPABILITY"],
            "verification_rules": [report["missing_verification_capability"]],
        },
        "D7_RISK_QUARANTINE": {
            "sensitive_data_route": "TOTAL_FIELD_REQUIRED",
            "forbidden_effects": ["LIVE_WRITE", "DB_WRITE", "CANONICAL_MUTATION", "POINTER_MUTATION", "OPERATION_COMMAND"],
            "stop_conditions": ["HASH_MISMATCH", "COORDINATE_MISMATCH", "PROTECTED_DATA_BOUNDARY", "NO_STATE_PROGRESS"],
        },
        "D8_ENVELOPE_AUTHORITY": {
            "request_identity": f"CAPABILITY_REQ:{report['task_id']}:{report['packet_sha256']}",
            "candidate_only": True,
            "provider_authority": False,
            "created_at": created.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "ttl_seconds": ttl_seconds,
            "verification_contract": report["missing_verification_capability"],
            "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
        },
    }
    return _finalize_packet(packet)


def _candidate_failures(
    candidate: Mapping[str, Any], requirement: Mapping[str, Any], *, now: datetime | None
) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    expected_request_hash = str(requirement.get("packet_sha256"))
    checks = (
        (candidate.get("schema_id") == "W7TP_COMPLETION_CANDIDATE_PACKET_V1", "SCHEMA_VALID", "$.schema_id"),
        (candidate.get("request_packet_sha256") == expected_request_hash, "REQUEST_HASH_EXACT", "$.request_packet_sha256"),
        (candidate.get("candidate_only") is True, "CANDIDATE_ONLY", "$.candidate_only"),
        (candidate.get("provider_authority") is False, "PROVIDER_AUTHORITY_FALSE", "$.provider_authority"),
        (candidate.get("operation_authority") in (None, False), "OPERATION_AUTHORITY_FALSE", "$.operation_authority"),
        (candidate.get("promoted") in (None, False), "SELF_PROMOTION_FORBIDDEN", "$.promoted"),
        (candidate.get("canonical") in (None, False), "SELF_CANONICALIZATION_FORBIDDEN", "$.canonical"),
        (candidate.get("unresolved_required_effects") == [], "UNRESOLVED_EFFECT_SET_EMPTY", "$.unresolved_required_effects"),
        (candidate.get("forbidden_effects") == [], "FORBIDDEN_EFFECTS_ABSENT", "$.forbidden_effects"),
        ("operation_command" not in candidate, "OPERATION_COMMAND_ABSENT", "$.operation_command"),
    )
    for passed, predicate, path in checks:
        if not passed:
            failures.append({"predicate": predicate, "path": path})
    envelope = requirement.get("D8_ENVELOPE_AUTHORITY")
    if not isinstance(envelope, Mapping):
        failures.append({"predicate": "REQUIREMENT_D8_VALID", "path": "$.D8_ENVELOPE_AUTHORITY"})
    else:
        try:
            created = _parse_packet_time(envelope.get("created_at"), "requirement.created_at")
            expires = _parse_packet_time(envelope.get("expires_at"), "requirement.expires_at")
            ttl = envelope.get("ttl_seconds")
            check_time = (now or created).astimezone(timezone.utc)
            if (
                isinstance(ttl, bool)
                or not isinstance(ttl, int)
                or not 1 <= ttl <= MAX_CAPABILITY_PACKET_TTL_SECONDS
                or expires - created != timedelta(seconds=ttl)
                or check_time < created
                or check_time >= expires
            ):
                failures.append({"predicate": "REQUIREMENT_TTL_ACTIVE", "path": "$.D8_ENVELOPE_AUTHORITY"})
        except (ValueError, AttributeError):
            failures.append({"predicate": "REQUIREMENT_D8_VALID", "path": "$.D8_ENVELOPE_AUTHORITY"})
    output_hashes = candidate.get("output_hashes")
    if not isinstance(output_hashes, Mapping) or not output_hashes:
        failures.append({"predicate": "OUTPUT_HASHES_PRESENT", "path": "$.output_hashes"})
    else:
        for coordinate, digest in output_hashes.items():
            try:
                _require_sha256(digest, f"$.output_hashes.{coordinate}")
            except ValueError:
                failures.append({"predicate": "OUTPUT_HASH_EXACT", "path": f"$.output_hashes.{coordinate}"})
    supplied_hash = candidate.get("candidate_sha256")
    unsigned = dict(candidate)
    unsigned.pop("candidate_sha256", None)
    if supplied_hash != canonical_sha256(unsigned):
        failures.append({"predicate": "CANDIDATE_SELF_HASH_EXACT", "path": "$.candidate_sha256"})
    expected_capability = requirement.get("D1_INTENT", {}).get("required_capability_id")
    if candidate.get("capability_id") != expected_capability:
        failures.append({"predicate": "CAPABILITY_ID_EXACT", "path": "$.capability_id"})
    return failures


def verify_completion_candidate(
    candidate: Mapping[str, Any], requirement: Mapping[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    failures = _candidate_failures(candidate, requirement, now=now)
    if failures:
        rejection = {
            "schema_id": "W7TP_TOTAL_FIELD_REJECTION_DELTA_PACKET_V1",
            "request_packet_sha256": requirement.get("packet_sha256"),
            "accepted_effects": [],
            "rejected_effects": [requirement.get("D1_INTENT", {}).get("required_capability_id")],
            "missing_effects": [requirement.get("D1_INTENT", {}).get("required_capability_id")],
            "invalid_objects": sorted({item["path"] for item in failures}),
            "exact_failure_predicates": failures,
            "required_corrections": sorted({item["predicate"] for item in failures}),
            "preserved_accepted_objects": list(candidate.get("reused_objects") or []),
            "next_minimum_delta": [requirement.get("D1_INTENT", {}).get("required_capability_id")],
            "candidate_only": True,
            "provider_authority": False,
        }
        return {
            "state": "REJECTED",
            "decision": "REJECT_AND_REQUEST_NEXT_DELTA",
            "failures": failures,
            "rejection_delta": _finalize_packet(rejection),
            "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
        }
    qualified = {
        "schema_id": "W7TP_QUALIFIED_CAPABILITY_PACKET_V1",
        "request_packet_sha256": requirement["packet_sha256"],
        "completion_candidate_sha256": candidate["candidate_sha256"],
        "capability_id": candidate["capability_id"],
        "object_refs": deepcopy(list(candidate.get("object_refs") or [])),
        "output_hashes": deepcopy(dict(candidate["output_hashes"])),
        "receiver_requirements": [requirement["D2_STATE"]["receiver_id"]],
        "lineage": {
            "parent": requirement["packet_sha256"],
            "relation": "TOTAL_FIELD_VERIFIED_COMPLETION",
        },
        "qualified": True,
        "provider_authority": False,
        "operation_authority": False,
        "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
    }
    return {
        "state": "QUALIFIED",
        "decision": "ACCEPT_QUALIFIED_CANDIDATE",
        "qualified_capability_packet": _finalize_packet(qualified),
        "failures": [],
    }


def run_total_field_capability_completion(
    report: Mapping[str, Any],
    *,
    target_native_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    local_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    cloud_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    target_base_state: Mapping[str, Any],
    reusable_capability_refs: Collection[str],
    created_at: str,
    verification_time: datetime | None = None,
    max_cloud_rounds: int = 3,
) -> dict[str, Any]:
    """Use target native, then Local LLM, then minimal Cloud deltas."""
    normalized = normalize_capability_missing_report(report)
    provider_trace: list[str] = []
    if target_native_provider is not None:
        target_result = target_native_provider(deepcopy(normalized))
        provider_trace.append("TARGET_NATIVE_CAPABILITY")
        if target_result.get("state") == "CAPABILITY_AVAILABLE":
            return {"state": "QUALIFIED_LOCAL", "provider_trace": provider_trace, "cloud_calls": 0, "result": deepcopy(dict(target_result))}
    local_result = local_provider(deepcopy(normalized))
    provider_trace.append("LOCAL_LLM")
    if local_result.get("state") == "CAPABILITY_AVAILABLE":
        return {"state": "QUALIFIED_LOCAL", "provider_trace": provider_trace, "cloud_calls": 0, "result": deepcopy(dict(local_result))}
    requirement = build_total_field_capability_requirement_packet(
        normalized,
        target_base_state=target_base_state,
        reusable_capability_refs=reusable_capability_refs,
        created_at=created_at,
    )
    request: Mapping[str, Any] = requirement
    rejection_deltas: list[dict[str, Any]] = []
    seen_delta_hashes: set[str] = set()
    for _round in range(1, max_cloud_rounds + 1):
        candidate = dict(cloud_provider(deepcopy(dict(request))))
        provider_trace.append("CLOUD_PROVIDER")
        decision = verify_completion_candidate(
            candidate,
            requirement,
            now=verification_time or _parse_packet_time(created_at, "verification_time"),
        )
        if decision["state"] == "QUALIFIED":
            return {
                "state": "QUALIFIED",
                "provider_trace": provider_trace,
                "cloud_calls": provider_trace.count("CLOUD_PROVIDER"),
                "requirement_packet": requirement,
                "rejection_deltas": rejection_deltas,
                "qualified_capability_packet": decision["qualified_capability_packet"],
            }
        delta = decision["rejection_delta"]
        if delta["packet_sha256"] in seen_delta_hashes:
            return {"state": "STOPPED_NON_CONVERGENCE", "provider_trace": provider_trace, "cloud_calls": provider_trace.count("CLOUD_PROVIDER"), "rejection_deltas": rejection_deltas + [delta], "unresolved_required_effects": delta["next_minimum_delta"]}
        seen_delta_hashes.add(delta["packet_sha256"])
        rejection_deltas.append(delta)
        request = delta
    return {"state": "STOPPED_NON_CONVERGENCE", "provider_trace": provider_trace, "cloud_calls": provider_trace.count("CLOUD_PROVIDER"), "rejection_deltas": rejection_deltas, "unresolved_required_effects": requirement["D6_GENERATIVE_COMPLETION"]["minimum_capability_delta"]}


def select_smallest_sufficient_memory_set(
    *,
    intent_ref: str,
    qualified_capability_packet: Mapping[str, Any],
    current_task_state: Mapping[str, Any],
    adi_objects: Collection[Mapping[str, Any]],
    receiver_id: str,
) -> dict[str, Any]:
    """Resolve an exact dependency closure; no semantic or float ranking."""
    if qualified_capability_packet.get("qualified") is not True:
        raise ValueError("QUALIFIED_CAPABILITY_PACKET_REQUIRED")
    index: dict[str, Mapping[str, Any]] = {}
    for item in adi_objects:
        object_id = item.get("object_id")
        coordinate = item.get("coordinate")
        if not isinstance(object_id, str) or not object_id or not isinstance(coordinate, str):
            raise ValueError("ADI_OBJECT_COORDINATE_INVALID")
        if coordinate.startswith("/") or ".." in Path(coordinate).parts or "\\" in coordinate:
            raise ValueError("ADI_OBJECT_COORDINATE_INVALID")
        _require_sha256(item.get("sha256"), f"ADI:{object_id}:sha256")
        if not isinstance(item.get("lineage_ref"), str) or not item["lineage_ref"]:
            raise ValueError(f"ADI_LINEAGE_REF_REQUIRED:{object_id}")
        if not isinstance(item.get("evidence_ref"), str) or not item["evidence_ref"]:
            raise ValueError(f"ADI_EVIDENCE_REF_REQUIRED:{object_id}")
        if object_id in index:
            raise ValueError("ADI_OBJECT_ID_COLLISION")
        index[object_id] = item
    required = set(current_task_state.get("required_object_ids") or [])
    required.update(qualified_capability_packet.get("object_refs") or [])
    selected: dict[str, Mapping[str, Any]] = {}
    pending = sorted(required)
    while pending:
        object_id = pending.pop(0)
        if object_id in selected:
            continue
        if object_id not in index:
            raise ValueError(f"ADI_REQUIRED_OBJECT_NOT_FOUND:{object_id}")
        item = index[object_id]
        consumers = item.get("consumers") or []
        if consumers and receiver_id not in consumers:
            raise ValueError(f"ADI_RECEIVER_INCOMPATIBLE:{object_id}")
        selected[object_id] = item
        for dependency in item.get("dependencies") or []:
            if dependency not in selected:
                pending.append(str(dependency))
        pending.sort()
    memory_set = {
        "schema_id": "W7TP_ADI_SMALLEST_SUFFICIENT_MEMORY_SET_V1",
        "intent_ref": intent_ref,
        "receiver_id": receiver_id,
        "selection_predicates": ["OBJECT_ID_EXACT", "COORDINATE_EXACT", "STATE_BOUND", "LINEAGE_BOUND", "DEPENDENCY_CLOSURE", "EVIDENCE_BOUND", "RECEIVER_COMPATIBLE"],
        "selected_objects": [
            {
                "object_id": object_id,
                "coordinate": selected[object_id]["coordinate"],
                "sha256": selected[object_id]["sha256"],
                "state": selected[object_id].get("state"),
                "lineage_ref": selected[object_id].get("lineage_ref"),
                "evidence_ref": selected[object_id].get("evidence_ref"),
                "capability_ref": selected[object_id].get("capability_ref"),
                "reconstruction_rule": selected[object_id].get("reconstruction_rule"),
                "verification_rule": selected[object_id].get("verification_rule"),
            }
            for object_id in sorted(selected)
        ],
        "excluded_object_count": len(index) - len(selected),
        "semantic_similarity_used": False,
        "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
    }
    return _finalize_packet(memory_set)


def build_local_llm_working_memory_projection(
    *,
    intent_ref: str,
    current_state_ref: str,
    required_capability_id: str,
    qualified_capability_packet: Mapping[str, Any],
    smallest_memory_set: Mapping[str, Any],
    receiver_id: str,
    receiver_capability_boundary: Collection[str],
    allowed_actions: Collection[str],
    forbidden_actions: Collection[str],
    verification_procedure: Collection[str],
    stop_conditions: Collection[str],
    context_ttl_seconds: int,
) -> dict[str, Any]:
    if not 1 <= context_ttl_seconds <= MAX_CAPABILITY_PACKET_TTL_SECONDS:
        raise ValueError("WORKING_MEMORY_TTL_INVALID")
    original_hash = canonical_sha256(qualified_capability_packet)
    selected = smallest_memory_set.get("selected_objects")
    if not isinstance(selected, list):
        raise ValueError("SMALLEST_MEMORY_SET_REQUIRED")
    projection = {
        "schema_id": "W7TP_LOCAL_LLM_WORKING_MEMORY_PROJECTION_V1",
        "intent": intent_ref,
        "current_state": current_state_ref,
        "required_capability": required_capability_id,
        "qualified_capability_ref": qualified_capability_packet.get("packet_sha256"),
        "object_refs": [item["object_id"] for item in selected],
        "schema_refs": [item["coordinate"] for item in selected if str(item["coordinate"]).startswith("schemas/")],
        "lineage_refs": [item["lineage_ref"] for item in selected if item.get("lineage_ref")],
        "evidence_refs": [item["evidence_ref"] for item in selected if item.get("evidence_ref")],
        "allowed_actions": sorted(set(allowed_actions)),
        "forbidden_actions": sorted(set(forbidden_actions)),
        "verification_procedure": list(verification_procedure),
        "stop_conditions": list(stop_conditions),
        "context_ttl_seconds": context_ttl_seconds,
        "receiver_id": receiver_id,
        "receiver_capability_boundary": sorted(set(receiver_capability_boundary)),
        "physical_memory_mapping": False,
        "candidate_only": True,
    }
    if canonical_sha256(qualified_capability_packet) != original_hash:
        raise AssertionError("QUALIFIED_CAPABILITY_PACKET_MUTATED")
    return _finalize_packet(projection)


def normalize_local_llm_result(result: Mapping[str, Any]) -> dict[str, Any]:
    proposed_actions = result.get("proposed_actions") or []
    if not isinstance(proposed_actions, list):
        raise ValueError("LOCAL_LLM_PROPOSED_ACTIONS_INVALID")
    return _finalize_packet(
        {
            "schema_id": "W7TP_LOCAL_LLM_RESULT_V1",
            "result_ref": result.get("result_ref"),
            "result_sha256": _require_sha256(result.get("result_sha256"), "result_sha256"),
            "reasoning_result": result.get("reasoning_result"),
            "operation_proposal": (
                {
                    "schema_id": "W7TP_OPERATION_PROPOSAL_V1",
                    "proposed_actions": deepcopy(proposed_actions),
                    "candidate_only": True,
                    "operation_authority": False,
                }
                if proposed_actions
                else None
            ),
            "operation_command": None,
            "operation_authority": False,
            "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
        }
    )


class TotalFieldContextMcpServer:
    """Small dependency-free MCP stdio server exposing one read-only tool."""

    def __init__(self, root: str | Path = ROOT) -> None:
        self.root = Path(root).resolve()

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        method = str(request.get("method", ""))
        request_id = request.get("id")
        if request_id is None:
            return None
        try:
            if method == "initialize":
                params = request.get("params") or {}
                result = {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {"name": "w7tp-total-field-dynamic-context", "version": "1.0.0"},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": "get_total_field_dynamic_context",
                            "description": (
                                "Read current allowlisted Total Field evidence and return relative paths, sizes, "
                                "SHA256 bindings, trust, freshness, and safe excerpts. Call before factual claims "
                                "about the workspace or product state. The result has no decision authority."
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "minLength": 1, "maxLength": 20000},
                                    "max_items": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                                    "identity_class": {
                                        "type": "string",
                                        "enum": ["founder", "general_member", "unknown"],
                                        "default": "unknown",
                                    },
                                },
                                "required": ["query"],
                                "additionalProperties": False,
                            },
                            "outputSchema": {
                                "type": "object",
                                "required": ["state", "authority", "policy", "packet_sha256"],
                                "properties": {
                                    "state": {"type": "string"},
                                    "authority": {
                                        "const": "READ_ONLY_CONTEXT_EVIDENCE_NO_DECISION_AUTHORITY"
                                    },
                                    "capability_route": {"type": ["object", "null"]},
                                    "context_items": {"type": "array"},
                                    "policy": {"type": "object"},
                                    "packet_sha256": {
                                        "type": "string",
                                        "pattern": "^[0-9a-f]{64}$",
                                    },
                                },
                                "additionalProperties": True,
                            },
                        }
                    ]
                }
            elif method == "tools/call":
                params = request.get("params") or {}
                if params.get("name") != "get_total_field_dynamic_context":
                    return self._error(request_id, -32602, "unknown tool")
                arguments = params.get("arguments") or {}
                if not isinstance(arguments, dict):
                    return self._error(request_id, -32602, "arguments must be an object")
                if set(arguments) - {"query", "max_items", "identity_class"}:
                    return self._error(request_id, -32602, "unknown tool argument")
                query = arguments.get("query")
                if not isinstance(query, str) or not query.strip():
                    return self._error(request_id, -32602, "query must be a non-empty string")
                max_items = arguments.get("max_items", 8)
                if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= 20:
                    return self._error(request_id, -32602, "max_items must be an integer from 1 to 20")
                identity_class = arguments.get("identity_class", "unknown")
                if identity_class not in {"founder", "general_member", "unknown"}:
                    return self._error(request_id, -32602, "identity_class is invalid")
                packet = build_dynamic_context(
                    query,
                    root=self.root,
                    max_items=max_items,
                    identity_class=identity_class,
                )
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(packet, ensure_ascii=False, sort_keys=True),
                        }
                    ],
                    "isError": str(packet.get("state", "")).startswith("HOLD"),
                }
            elif method == "resources/list":
                result = {
                    "resources": [
                        {
                            "uri": "w7tp://total-field/dynamic-context",
                            "name": "W7TP Total Field Dynamic Context",
                            "description": "Read-only baseline context packet; use the tool for query-specific retrieval.",
                            "mimeType": "application/json",
                        }
                    ]
                }
            elif method == "resources/read":
                params = request.get("params") or {}
                if params.get("uri") != "w7tp://total-field/dynamic-context":
                    return self._error(request_id, -32602, "unknown resource")
                packet = build_dynamic_context("current total field governed workspace context", root=self.root)
                result = {
                    "contents": [
                        {
                            "uri": "w7tp://total-field/dynamic-context",
                            "mimeType": "application/json",
                            "text": json.dumps(packet, ensure_ascii=False, sort_keys=True),
                        }
                    ]
                }
            elif method in {"prompts/list", "resources/templates/list"}:
                result = {"prompts": []} if method == "prompts/list" else {"resourceTemplates": []}
            else:
                return self._error(request_id, -32601, f"method not found: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:  # pragma: no cover - final protocol guard
            return self._error(request_id, -32603, f"internal error: {type(exc).__name__}:{exc}")

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def serve_stdio(root: str | Path = ROOT) -> int:
    server = TotalFieldContextMcpServer(root)
    for raw_line in sys.stdin.buffer:
        if not raw_line.strip():
            continue
        try:
            request = json.loads(raw_line)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            response = server.handle(request)
        except Exception as exc:
            response = TotalFieldContextMcpServer._error(None, -32700, f"parse error: {type(exc).__name__}:{exc}")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--query")
    parser.add_argument("--max-items", type=int, default=8)
    parser.add_argument("--stdio", action="store_true")
    args = parser.parse_args()
    if args.stdio or args.query is None:
        return serve_stdio(args.root)
    packet = build_dynamic_context(args.query, root=args.root, max_items=args.max_items)
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 1 if str(packet.get("state", "")).startswith("HOLD") else 0


if __name__ == "__main__":
    raise SystemExit(main())
