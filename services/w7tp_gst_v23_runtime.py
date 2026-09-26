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

# Origin Cell semantic purity is stricter than generic transport safety.
# Historical differential evidence may be referenced, but active packet semantics
# must remain source-generated rule-body reconstruction from a clean receiver.
_FORBIDDEN_SEMANTIC_KEYS = frozenset({
    "blob", "blobs", "base64", "literal_bytes", "file_fragment",
    "changed_bytes", "chunk_payload", "chunks", "diff", "delta",
    "patch", "patch_cells", "payload", "source_target", "target_artifact",
    "target_data", "target_bytes", "previous_state", "prior_state",
    "base_payload", "compressed_payload", "compressed_blob",
})
_FORBIDDEN_KEY_MARKERS = (
    "compress", "gzip", "zlib", "bz2", "lzma", "archive",
    "xdelta", "bsdiff", "rsync", "delta", "patch",
)
_ALLOWED_RULE_FIELDS = {
    "CREATE_DIRECTORY": frozenset({"id", "primitive", "path"}),
    "WRITE_PRNG_BYTES": frozenset({"id", "primitive", "path", "size", "seed"}),
    "WRITE_DETERMINISTIC_BYTES_AT_OFFSETS": frozenset(
        {"id", "primitive", "path", "size", "writes"}
    ),
    "JSONL_WRITE": frozenset(
        {"id", "primitive", "path", "row_count", "default_state", "changed_rows", "namespace"}
    ),
    "SQLITE_BUILD": frozenset(
        {"id", "primitive", "path", "base_rows", "update_rows", "insert_rows", "namespace"}
    ),
    "WRITE_DETERMINISTIC_FILE_SERIES": frozenset({
        "id", "primitive", "directory", "base_count", "file_size",
        "replace_count", "delete_start", "delete_end", "rename_start",
        "rename_end", "new_count", "namespace",
    }),
}
_ALLOWED_STATE_CELL_FIELDS = {
    "SOURCE_MANIFEST": frozenset({"cell", "manifest_sha256", "bytes", "files"}),
    "DATASET_COORDINATE": frozenset({"cell", "dataset_mib"}),
    "CONSTRUCTION_GRAPH": frozenset({"cell", "rule_ids"}),
}


class GstRuntimeHold(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _normalized_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _reject_polluting_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = _normalized_key(key)
            if normalized == "differential_input_allowed":
                pass
            elif (
                normalized in _FORBIDDEN_SEMANTIC_KEYS
                or any(marker in normalized for marker in _FORBIDDEN_KEY_MARKERS)
            ):
                raise GstRuntimeHold(
                    f"HOLD_GST_RUNTIME_SEMANTIC_PURITY_KEY:{path}.{key}"
                )
            _reject_polluting_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_polluting_keys(nested, f"{path}[{index}]")


def _validate_rule_body_purity(packet: dict[str, Any]) -> None:
    rules = packet.get("reconstruction_rules")
    if not isinstance(rules, list) or not rules:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_RULE_BODY_REQUIRED")
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise GstRuntimeHold("HOLD_GST_RUNTIME_RULE_OBJECT_REQUIRED")
        primitive = rule.get("primitive")
        allowed = _ALLOWED_RULE_FIELDS.get(str(primitive))
        if allowed is None:
            raise GstRuntimeHold("HOLD_GST_RUNTIME_RULE_PRIMITIVE_NOT_PURE")
        if frozenset(rule) != allowed:
            raise GstRuntimeHold(
                f"HOLD_GST_RUNTIME_RULE_FIELDS_NOT_PURE:{index}"
            )
        for key, value in rule.items():
            if isinstance(value, str) and len(value.encode("utf-8")) > 1024:
                raise GstRuntimeHold(
                    f"HOLD_GST_RUNTIME_RULE_STRING_TOO_LARGE:{index}:{key}"
                )
        if primitive == "WRITE_DETERMINISTIC_BYTES_AT_OFFSETS":
            writes = rule.get("writes")
            if not isinstance(writes, list):
                raise GstRuntimeHold("HOLD_GST_RUNTIME_RULE_WRITES_INVALID")
            for write_index, write in enumerate(writes):
                if not isinstance(write, dict) or frozenset(write) != frozenset({"offset", "seed"}):
                    raise GstRuntimeHold(
                        f"HOLD_GST_RUNTIME_RULE_WRITE_FIELDS_NOT_PURE:{index}:{write_index}"
                    )
                seed = write.get("seed")
                if not isinstance(seed, str) or len(seed.encode("utf-8")) > 256:
                    raise GstRuntimeHold(
                        f"HOLD_GST_RUNTIME_RULE_SEED_INVALID:{index}:{write_index}"
                    )


def _validate_state_cell_purity(packet: dict[str, Any]) -> None:
    cells = packet.get("source_state_cells")
    if not isinstance(cells, list) or not cells:
        raise GstRuntimeHold("HOLD_GST_RUNTIME_STATE_CELLS_REQUIRED")
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            raise GstRuntimeHold("HOLD_GST_RUNTIME_STATE_CELL_INVALID")
        allowed = _ALLOWED_STATE_CELL_FIELDS.get(str(cell.get("cell")))
        if allowed is None or frozenset(cell) != allowed:
            raise GstRuntimeHold(
                f"HOLD_GST_RUNTIME_STATE_CELL_FIELDS_NOT_PURE:{index}"
            )


def verify_origin_cell_semantic_purity(packet: dict[str, Any]) -> None:
    if not isinstance(packet, dict):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_PACKET_OBJECT_REQUIRED")
    if packet.get("packet_type") != "ORIGIN_CELL_GENERATIVE_RULE_PACKET":
        raise GstRuntimeHold("HOLD_GST_RUNTIME_ORIGIN_CELL_PACKET_REQUIRED")

    _reject_polluting_keys(packet)

    field = packet.get("joint_state_field")
    if not isinstance(field, dict):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_JOINT_FIELD_REQUIRED")
    d6 = field.get("D6")
    if not isinstance(d6, dict):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D6_REQUIRED")
    if (
        d6.get("mode") != "SOURCE_GENERATED_RULE_BODY"
        or d6.get("generator_base_required") is not False
        or d6.get("transmitted_target_bytes") != 0
    ):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_D6_PURITY_CONTRACT")

    conditions = packet.get("construction_conditions")
    if not isinstance(conditions, dict):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_CONSTRUCTION_CONDITIONS_REQUIRED")
    required_conditions = {
        "receiver_root": "EMPTY_CLEAN_ROOM",
        "executor": "GENERIC_PRIMITIVES_ONLY",
        "previous_state_allowed": False,
        "differential_input_allowed": False,
    }
    if any(conditions.get(key) != expected for key, expected in required_conditions.items()):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_CONSTRUCTION_PURITY_CONTRACT")
    if frozenset(conditions) != frozenset(required_conditions):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_CONSTRUCTION_FIELDS_NOT_PURE")

    minimum = packet.get("minimum_new_information")
    if not isinstance(minimum, dict) or frozenset(minimum) != frozenset({"dataset_mib"}):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_MINIMUM_INFORMATION_NOT_PURE")

    _validate_state_cell_purity(packet)
    _validate_rule_body_purity(packet)

    relations = packet.get("relations")
    if not isinstance(relations, list):
        raise GstRuntimeHold("HOLD_GST_RUNTIME_RELATIONS_REQUIRED")
    for index, relation in enumerate(relations):
        if not isinstance(relation, dict) or frozenset(relation) != frozenset(
            {"from", "to", "relation"}
        ):
            raise GstRuntimeHold(
                f"HOLD_GST_RUNTIME_RELATION_FIELDS_NOT_PURE:{index}"
            )


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
        "semantic_purity_guard": "ACTIVE_NO_DIFF_NO_COMPRESSION_NO_PATCH",
        "origin_cell_semantics": "SOURCE_GENERATED_RULE_BODY_CLEAN_RECEIVER",
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
    verify_origin_cell_semantic_purity(packet)
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
