from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_BINDING_PATH = ROOT / "runtime/total_field/gst_v23_runtime_consumer/ACTIVE_BINDING.json"
AUTHORITY_PATH = ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
D8_DECISION_PATH = ROOT / (
    "evidence/total_field/gst_v23_runtime_consumer_binding_candidate/"
    "GST_V23_D8_FORMAL_CLOSURE_20260924/D8_FORMAL_CLOSURE_DECISION.json"
)
DELIVERY_ROOT = ROOT / "runtime/total_field/gst_v23_runtime_consumer/deliveries"
REQUIRED_EFFECT = "AUTHORIZE_GST_V23_RUNTIME_CONSUMER_FORMAL_DELIVERY"
MAX_PACKET_BYTES = 16 * 1024 * 1024
_DELIVERY_LOCK = Lock()


class GstRuntimeHold(RuntimeError):
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_JSON_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_JSON_OBJECT_REQUIRED")
    return value


def resolve_repo_ref(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_REFERENCE_INVALID")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_REFERENCE_OUTSIDE_ROOT") from exc
    return candidate


def verify_active_binding(
    *,
    root: Path = ROOT,
    active_binding_path: Path = ACTIVE_BINDING_PATH,
    authority_path: Path = AUTHORITY_PATH,
    d8_decision_path: Path = D8_DECISION_PATH,
) -> dict[str, Any]:
    binding = load_json(active_binding_path)
    authority = load_json(authority_path)
    decision = load_json(d8_decision_path)

    if binding.get("state") != "ACTIVE_FOUNDER_AUTHORIZED_RUNTIME_BINDING":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_BINDING_NOT_ACTIVE")
    if binding.get("total_field_decision") != "PASS":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_BINDING_TOTAL_FIELD_NOT_PASS")
    if authority.get("state") != "ACTIVE_TOTAL_FIELD_AUTHORITY":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_AUTHORITY_NOT_ACTIVE")
    if authority.get("contract_state") != "ACTIVE_FORMAL":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_AUTHORITY_NOT_FORMAL")
    if authority.get("formal_decision_authority") is not True:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_FORMAL_DECISION_AUTHORITY_MISSING")
    if REQUIRED_EFFECT not in authority.get("allowed_effects", []):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_REQUIRED_EFFECT_NOT_ALLOWED")
    if decision.get("state") != "PASS_D8_FORMAL_CLOSURE":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_NOT_CLOSED")
    if decision.get("required_effect") != REQUIRED_EFFECT:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_EFFECT_MISMATCH")
    if decision.get("total_field_decision") != "PASS":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_TOTAL_FIELD_NOT_PASS")
    if decision.get("binding_id") != binding.get("binding_id"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_BINDING_ID_MISMATCH")

    if resolve_repo_ref(root, decision.get("active_binding_ref")) != active_binding_path.resolve():
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_REFERENCE_MISMATCH")
    if sha256_file(active_binding_path) != decision.get("active_binding_sha256"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_HASH_MISMATCH")
    if resolve_repo_ref(root, decision.get("authority_pointer_ref")) != authority_path.resolve():
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_REFERENCE_MISMATCH")
    historical_authority_hash = decision.get("authority_pointer_sha256")
    if not isinstance(historical_authority_hash, str) or len(historical_authority_hash) != 64:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D8_AUTHORITY_COORDINATE_INVALID")

    consumer_path = resolve_repo_ref(root, binding.get("consumer_path"))
    contract_path = resolve_repo_ref(root, binding.get("contract_path"))
    for observed_path, binding_hash, decision_hash in (
        (consumer_path, binding.get("consumer_sha256"), decision.get("consumer_sha256")),
        (contract_path, binding.get("contract_sha256"), decision.get("contract_sha256")),
    ):
        observed_hash = sha256_file(observed_path)
        if observed_hash != binding_hash or observed_hash != decision_hash:
            raise GstRuntimeHold("HOLD_GST_RUNTIME_IMPLEMENTATION_HASH_MISMATCH")

    activation_run = resolve_repo_ref(root, binding.get("activation_run"))
    activation_receipt = activation_run / "FOUNDER_RUNTIME_ACTIVATION.json"
    if sha256_file(activation_receipt) != binding.get("activation_record_sha256"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ACTIVATION_RECORD_HASH_MISMATCH")
    if binding.get("activation_record_sha256") != decision.get("activation_record_sha256"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ACTIVATION_RECORD_NOT_D8_BOUND")

    activation_result = activation_run / "receipts/ACTIVATION_RESULT.json"
    if resolve_repo_ref(root, decision.get("activation_result_ref")) != activation_result.resolve():
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ACTIVATION_RESULT_REFERENCE_MISMATCH")
    observed_result_hash = sha256_file(activation_result)
    if observed_result_hash != binding.get("activation_result_sha256"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ACTIVATION_RESULT_HASH_MISMATCH")
    if observed_result_hash != decision.get("activation_result_sha256"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ACTIVATION_RESULT_NOT_D8_BOUND")
    activation_result_value = load_json(activation_result)
    expected_manifest = binding.get("last_verified_target_manifest_sha256")
    if expected_manifest != decision.get("target_manifest_sha256"):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_TARGET_MANIFEST_BINDING_MISMATCH")
    if activation_result_value.get("target_manifest_sha256") != expected_manifest:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ACTIVATION_RESULT_MANIFEST_MISMATCH")

    return {
        "binding": binding,
        "authority": authority,
        "decision": decision,
        "consumer_path": consumer_path,
        "contract_path": contract_path,
        "activation_receipt": activation_receipt,
        "activation_result": activation_result,
    }


def runtime_status(**paths: Any) -> dict[str, Any]:
    context = verify_active_binding(**paths)
    binding = context["binding"]
    decision = context["decision"]
    return {
        "state": "ACTIVE_GST_V23_USER_DELIVERY",
        "founder_baseline": binding["founder_baseline"],
        "binding_id": binding["binding_id"],
        "runtime_activated": True,
        "formal_delivery": True,
        "total_field_decision": "PASS",
        "d8_closure": decision["d8_closure"],
        "service_ready": True,
    }


def _load_consumer(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("w7tp_gst_v23_active_runtime_consumer", path)
    if spec is None or spec.loader is None:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_CONSUMER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "activate_once", None)):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_CONSUMER_ENTRYPOINT_MISSING")
    return module


def deliver_packet(
    packet: dict[str, Any],
    *,
    root: Path = ROOT,
    active_binding_path: Path = ACTIVE_BINDING_PATH,
    authority_path: Path = AUTHORITY_PATH,
    d8_decision_path: Path = D8_DECISION_PATH,
    delivery_root: Path = DELIVERY_ROOT,
) -> dict[str, Any]:
    packet_bytes = canonical_json_bytes(packet)
    if len(packet_bytes) > MAX_PACKET_BYTES:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_PACKET_TOO_LARGE")

    try:
        delivery_root.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_DELIVERY_ROOT_OUTSIDE_REPOSITORY") from exc

    context = verify_active_binding(
        root=root,
        active_binding_path=active_binding_path,
        authority_path=authority_path,
        d8_decision_path=d8_decision_path,
    )
    if not _DELIVERY_LOCK.acquire(blocking=False):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_DELIVERY_BUSY")
    try:
        consumer = _load_consumer(context["consumer_path"])
        delivery_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:12]
        run_root = delivery_root / delivery_id
        run_root.mkdir(parents=True, exist_ok=False)
        packet_path = run_root / "RECEIVED_GST_PACKET.json"
        result_path = run_root / "DELIVERY_RESULT.json"
        packet_path.write_bytes(packet_bytes + b"\n")

        try:
            consumer_result = consumer.activate_once(
                packet_path,
                run_root / "workspace",
                context["activation_receipt"],
            )
        except Exception as exc:
            code = getattr(exc, "code", "HOLD_GST_RUNTIME_DELIVERY_FAILED")
            result_path.write_bytes(canonical_json_bytes({"state": code, "delivery_id": delivery_id}) + b"\n")
            if hasattr(exc, "code"):
                raise GstRuntimeHold(code) from exc
            raise GstRuntimeHold("HOLD_GST_RUNTIME_DELIVERY_FAILED") from exc

        result = {
            "state": "PASS_D8_AUTHORIZED_GST_V23_DELIVERY",
            "delivery_id": delivery_id,
            "binding_id": context["binding"]["binding_id"],
            "consumer_state": consumer_result["state"],
            "packet_sha256": consumer_result["packet_sha256"],
            "target_manifest_sha256": consumer_result["target_manifest_sha256"],
            "reconstructed_bytes": consumer_result["target_bytes"],
            "reconstructed_files": consumer_result["target_files"],
            "differential_bytes": consumer_result["differential_payload_bytes"],
            "target_bytes_transmitted": consumer_result["transmitted_target_bytes"],
            "runtime_activated": True,
            "formal_delivery": True,
            "total_field_decision": "PASS",
            "output_ref": str((run_root / "workspace/reconstructed").relative_to(root)),
        }
        result_path.write_bytes(canonical_json_bytes(result) + b"\n")
        return result
    finally:
        _DELIVERY_LOCK.release()
