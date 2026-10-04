from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "capability_manifest.json"

FORBIDDEN_SERVICE_ENDPOINT = re.compile(
    r"(?:^|://)(?:localhost|127(?:\.\d+){3}|10(?:\.\d+){3}|192\.168(?:\.\d+){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d+){2}|100\.(?:6[4-9]|[789]\d|1[01]\d|12[0-7])(?:\.\d+){2})(?::\d+)?",
    re.IGNORECASE,
)

DESTRUCTIVE_RE = re.compile(
    r"(?:\b(?:shutdown|reboot|poweroff|halt|kill|pkill|killall|taskkill|mkfs|fdisk|parted)\b|\bformat(?!-)[A-Za-z0-9_.]*\b)",
    re.IGNORECASE,
)
MUTATING_RE = re.compile(
    r"(?:\b(?:rm|mv|cp|chmod|chown|mkdir|touch|truncate|install|apt|dnf|yum|pacman)\b|"
    r"\bsystemctl\s+(?:start|stop|restart|enable|disable|mask|unmask)\b|"
    r"\bdocker\s+(?:run|start|stop|restart|rm|exec|compose\s+up|compose\s+down)\b|"
    r"\b(?:Set|New|Remove|Start|Stop|Restart|Enable|Disable|Add|Clear|Move|Copy|Rename|Write)-[A-Za-z0-9]+\b|"
    r"\b(?:Out-File|Set-Content|Add-Content|Clear-Content)\b|>>?|\|\s*tee\b)",
    re.IGNORECASE,
)
SAFE_POSIX_HEADS = {
    "pwd", "whoami", "id", "uname", "ls", "cat", "head", "tail", "grep",
    "wc", "stat", "sha256sum", "ss", "ps", "env", "printenv", "date",
}
SAFE_GIT_SUBCOMMANDS = {"status", "diff", "log", "show", "rev-parse", "branch"}
SAFE_POWERSHELL_VERBS = {"Get", "Select", "Where", "Format", "Sort", "Measure"}

class RemoteDesktopOrganError(RuntimeError):
    pass


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def tool_contract(source_tool: str) -> dict[str, Any]:
    for item in load_manifest()["tool_contracts"]:
        if item["source_tool"] == source_tool:
            return dict(item)
    raise RemoteDesktopOrganError(f"UNKNOWN_SOURCE_TOOL:{source_tool}")


def _powershell_read_only(command: str) -> bool:
    if MUTATING_RE.search(command) or DESTRUCTIVE_RE.search(command):
        return False
    cmdlets = re.findall(r"\b([A-Za-z]+)-[A-Za-z0-9]+\b", command)
    if not cmdlets:
        return False
    return all(verb in SAFE_POWERSHELL_VERBS for verb in cmdlets)


def _posix_read_only(command: str) -> bool:
    if MUTATING_RE.search(command) or DESTRUCTIVE_RE.search(command):
        return False
    # Fail closed on command substitution or sequencing. A simple pipe is accepted
    # only when every segment starts with a known read-only command.
    if any(marker in command for marker in ("&&", "||", ";", "$(", "`")):
        return False
    segments = [segment.strip() for segment in command.split("|")]
    if not segments or any(not s for s in segments):
        return False
    for segment in segments:
        try:
            tokens = shlex.split(segment)
        except ValueError:
            return False
        if not tokens:
            return False
        head = Path(tokens[0]).name
        if head == "git":
            if len(tokens) < 2 or tokens[1] not in SAFE_GIT_SUBCOMMANDS:
                return False
            continue
        if head not in SAFE_POSIX_HEADS:
            return False
    return True


def classify_process_command(command: str) -> dict[str, Any]:
    text = str(command or "").strip()
    if not text:
        return {"effect_class": "DYNAMIC_EFFECT", "d8_required": True, "reason": "EMPTY_OR_UNKNOWN_COMMAND"}
    if DESTRUCTIVE_RE.search(text):
        return {"effect_class": "DESTRUCTIVE_CONTROL", "d8_required": True, "reason": "DESTRUCTIVE_MARKER"}
    if MUTATING_RE.search(text):
        return {"effect_class": "MUTATION", "d8_required": True, "reason": "MUTATING_MARKER"}
    if _powershell_read_only(text):
        return {"effect_class": "READ_ONLY", "d8_required": False, "reason": "PROVEN_READ_ONLY_POWERSHELL"}
    if _posix_read_only(text):
        return {"effect_class": "READ_ONLY", "d8_required": False, "reason": "PROVEN_READ_ONLY_POSIX"}
    return {"effect_class": "DYNAMIC_EFFECT", "d8_required": True, "reason": "UNPROVEN_COMMAND_FAIL_CLOSED"}


def resolve_effect(source_tool: str, input_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    contract = tool_contract(source_tool)
    payload = dict(input_payload or {})
    if contract["class"] == "DYNAMIC_EFFECT":
        candidate = payload.get("command") or payload.get("input") or payload.get("chars") or ""
        dynamic = classify_process_command(str(candidate))
        return {**contract, **dynamic}
    if contract["d8_required"] == "DYNAMIC_BY_EFFECT":
        return {**contract, "d8_required": True, "reason": "HELPER_EFFECT_MUST_BE_RECLASSIFIED"}
    return {**contract, "effect_class": contract["class"], "reason": "STATIC_TOOL_CONTRACT"}


def validate_service_ref(service_ref: str | None) -> None:
    if not service_ref:
        return
    value = str(service_ref)
    if FORBIDDEN_SERVICE_ENDPOINT.search(value):
        raise RemoteDesktopOrganError("DIRECT_IP_PORT_SERVICE_ID_FORBIDDEN")
    if not (value.startswith("service:") or value.startswith("domain:") or value.startswith("https://")):
        raise RemoteDesktopOrganError("SERVICE_REF_REQUIRED")


def _canonical_hash(value: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_effect_envelope(*, source_tool: str, task_ref: str, device_ref: str,
                          target_ref: str, input_payload: Mapping[str, Any],
                          authority_ref: str | None, idempotency_key: str,
                          return_coordinate: str, service_ref: str | None = None,
                          preimage_ref: str | None = None,
                          rollback_ref: str | None = None,
                          origin_cell_packet_ref: str | None = None) -> dict[str, Any]:
    validate_service_ref(service_ref)
    resolved = resolve_effect(source_tool, input_payload)
    if resolved["d8_required"] and not authority_ref:
        raise RemoteDesktopOrganError("D8_AUTHORITY_REF_REQUIRED")
    envelope = {
        "schema_version": "W7TP-RDC-EFFECT-ENVELOPE/1.0",
        "command_id": resolved["command_id"],
        "task_ref": task_ref,
        "device_ref": device_ref,
        "service_ref": service_ref,
        "effect_class": resolved["effect_class"],
        "target_ref": target_ref,
        "input": dict(input_payload),
        "preimage_ref": preimage_ref,
        "rollback_ref": rollback_ref,
        "authority_ref": authority_ref,
        "idempotency_key": idempotency_key,
        "origin_cell_packet_ref": origin_cell_packet_ref,
        "return_coordinate": return_coordinate,
    }
    envelope["envelope_sha256"] = _canonical_hash(envelope)
    return envelope


def build_origin_state_projection(*, task_ref: str, device_ref: str, command_id: str,
                                  state_refs: list[str], evidence_refs: list[str],
                                  version_ref: str) -> dict[str, Any]:
    return {
        "schema_version": "W7TP-RDC-ORIGIN-STATE-PROJECTION/1.0",
        "task_ref": task_ref,
        "device_ref": device_ref,
        "command_id": command_id,
        "state_refs": list(dict.fromkeys(state_refs)),
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
        "version_ref": version_ref,
        "plaintext_expansion": False,
        "authority_created": False,
        "semantic_class": "TASK_MINIMUM_ORIGIN_STATE_PROJECTION",
    }


def validate_cloud_completion(candidate: Mapping[str, Any]) -> dict[str, Any]:
    forbidden = {
        "d8_authority", "authority_granted", "execution_authorized", "canonical",
        "observed_fact", "member_plaintext", "credential", "password", "api_key",
    }
    for key in candidate:
        if str(key).strip().lower() in forbidden:
            raise RemoteDesktopOrganError(f"CLOUD_COMPLETION_FORBIDDEN_FIELD:{key}")
    result = dict(candidate)
    result["candidate_only"] = True
    result["authority_created"] = False
    return result


def build_dispatch_plan(envelope: Mapping[str, Any], *, mode: str,
                        executor_service_ref: str | None = None) -> dict[str, Any]:
    command_id = str(envelope.get("command_id") or "")
    source = next(
        (item for item in load_manifest()["tool_contracts"] if item["command_id"] == command_id),
        None,
    )
    if source is None:
        raise RemoteDesktopOrganError(f"UNKNOWN_COMMAND_ID:{command_id}")
    if mode == "compatibility_rdc":
        return {
            "schema_version": "W7TP-RDC-DISPATCH-PLAN/1.0",
            "mode": "COMPATIBILITY_RDC",
            "source_runtime_dependency": True,
            "source_tool": source["source_tool"],
            "device_ref": envelope["device_ref"],
            "input": dict(envelope["input"]),
            "effect_class": envelope["effect_class"],
            "authority_ref": envelope.get("authority_ref"),
            "envelope_sha256": envelope.get("envelope_sha256"),
            "return_coordinate": envelope["return_coordinate"],
        }
    if mode == "native_claw":
        validate_service_ref(executor_service_ref)
        if not executor_service_ref:
            raise RemoteDesktopOrganError("NATIVE_CLAW_SERVICE_REF_REQUIRED")
        return {
            "schema_version": "W7TP-RDC-DISPATCH-PLAN/1.0",
            "mode": "NATIVE_CLAW",
            "source_runtime_dependency": False,
            "executor_service_ref": executor_service_ref,
            "native_action_ref": source["native_target"],
            "device_ref": envelope["device_ref"],
            "target_ref": envelope["target_ref"],
            "input": dict(envelope["input"]),
            "effect_class": envelope["effect_class"],
            "authority_ref": envelope.get("authority_ref"),
            "idempotency_key": envelope["idempotency_key"],
            "origin_cell_packet_ref": envelope.get("origin_cell_packet_ref"),
            "envelope_sha256": envelope.get("envelope_sha256"),
            "return_coordinate": envelope["return_coordinate"],
        }
    raise RemoteDesktopOrganError(f"UNKNOWN_DISPATCH_MODE:{mode}")
