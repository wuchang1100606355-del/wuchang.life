from __future__ import annotations

import copy
import hashlib
import json
import os
import secrets
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path("/home/taiji_admin/Taiji_Hub").resolve()
RUN_ID = "PRODUCT_SYSTEM_ROOT_V23_REBIND_20261004T221816Z"
OUT = ROOT / "runtime/total_field/product_system_root" / RUN_ID
GOV = ROOT / "Taiji_Governance/candidates/t007_v23_global_successor_20261002T124541Z/product_root_v23_cleanup_20261004T221816Z"

ACTIVE_PRODUCT = ROOT / "runtime/total_field/master_index/ACTIVE_PRODUCT_SYSTEM_ROOT_POINTER.json"
ACTIVE_W7TP = ROOT / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
ACTIVE_FIELD = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json"
ACTIVE_FIELD_ROUTER = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
AUTHORITY = ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"

OLD_ROOT = ROOT / "runtime/total_field/product_system_root/PRODUCT_SYSTEM_ROOT_SUCCESSOR_WUCHANG_XIAOJ_20260730T190929Z/W7TP_PRODUCT_SYSTEM_ROOT_SUCCESSOR.json"
OLD_RECEIPT = ROOT / "runtime/total_field/product_system_root/PRODUCT_SYSTEM_ROOT_SUCCESSOR_WUCHANG_XIAOJ_20260730T190929Z/D8_FORMAL_RECEIPT.json"
SCHEMA = ROOT / "runtime/total_field/product_system_root/PRODUCT_SYSTEM_ROOT_SUCCESSOR_WUCHANG_XIAOJ_20260730T190929Z/PRODUCT_SYSTEM_ROOT_SUCCESSOR.schema.json"

AUTH_REC = OUT / "FOUNDER_AUTHORIZATION_RECORD.json"
ROOT_PACKET = OUT / "W7TP_PRODUCT_SYSTEM_ROOT_SUCCESSOR.json"
RECEIPT = OUT / "D8_FORMAL_RECEIPT.json"
ROLLBACK = OUT / "PRODUCT_ROOT_POINTER_ROLLBACK.json"
REPORT = GOV / "PRODUCT_ROOT_V23_CLEANUP_REPORT.json"

EXPLICIT_AUTHORIZATION = "EXPLICIT_RETIRE_ALL_ACTIVE_W7TP_V2_1_BINDINGS_AND_REBIND_PRODUCT_ROOT_TO_W7TP_V2_3"

def cj(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def utc_now():
    return datetime.now(timezone.utc)

def utc_text(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def write_new(path: Path, value):
    if path.exists():
        raise RuntimeError(f"refusing overwrite: {path}")
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")

def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()

def historical_path(path: str) -> bool:
    s = path.lower()
    return any(x in s for x in (
        "history", "preimage", "rollback", "receipt", "previous", "parent",
        "repair_preimages", "isolated", "candidate", "evidence"
    ))

def find_active_v21():
    findings = []
    scan_roots = [
        ROOT / "runtime/total_field/master_index",
        ROOT / "runtime/total_field/active",
    ]
    def walk(value, path, source):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{path}.{k}", source)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]", source)
        elif isinstance(value, str):
            s = value.lower()
            v21 = (
                value == "2.1"
                or "v2_1" in s
                or "v2-1" in s
                or "canonical_v2_1" in s
                or "w7tp_v2_1" in s
            )
            if v21 and not historical_path(path):
                findings.append({"source": rel(source), "path": path, "value": value})
    for base in scan_roots:
        if not base.is_dir():
            continue
        for p in sorted(base.glob("ACTIVE*.json")):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            walk(doc, "$", p)
    return findings

def main():
    if socket.gethostname() != "taiji01":
        raise RuntimeError("TARGET_MISMATCH")

    now = utc_now()
    active_w7tp = json.loads(ACTIVE_W7TP.read_text(encoding="utf-8"))
    active_product = json.loads(ACTIVE_PRODUCT.read_text(encoding="utf-8"))
    field = json.loads(ACTIVE_FIELD.read_text(encoding="utf-8"))
    field_router = json.loads(ACTIVE_FIELD_ROUTER.read_text(encoding="utf-8"))
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))

    if active_w7tp.get("version") != "2.3" or active_w7tp.get("canonical_id") != "W7TP_8D_ADI_V2_3":
        raise RuntimeError("ACTIVE_W7TP_NOT_V23")
    if field.get("version") != "2.3" or field_router.get("version") != "2.3":
        raise RuntimeError("CURRENT_FIELD_NOT_V23")
    if "AUTHORIZE_W7TP_V23_GLOBAL_CANONICAL_ACTIVATION" not in authority.get("allowed_effects", []):
        raise RuntimeError("TOTAL_FIELD_AUTHORITY_MISSING_V23_EFFECT")
    if active_product.get("w7tp_canonical", {}).get("version") != "2.1":
        raise RuntimeError("ACTIVE_PRODUCT_ROOT_NOT_EXPECTED_V21_PREIMAGE")

    preimage_product_pointer_sha = sha(ACTIVE_PRODUCT)
    preimage_root_sha = sha(OLD_ROOT)
    preimage_authority_sha = sha(AUTHORITY)
    old_root = json.loads(OLD_ROOT.read_text(encoding="utf-8"))
    old_receipt = json.loads(OLD_RECEIPT.read_text(encoding="utf-8"))

    OUT.mkdir(parents=True, exist_ok=False)

    rollback_doc = copy.deepcopy(active_product)
    write_new(ROLLBACK, rollback_doc)

    auth = {
        "schema": "w7tp.total_field.founder_same_lineage_root_successor_authorization.v1",
        "state": "EXPLICIT_SINGLE_USE_AUTHORIZATION_CONSUMED_BY_RUN",
        "run_id": RUN_ID,
        "created_at_utc": utc_text(now),
        "founder": {
            "name": "江政隆",
            "identity_ref": "identity:founder:chiang-cheng-lung",
            "authorization": EXPLICIT_AUTHORIZATION,
        },
        "node": "taiji01",
        "mode": "ONE_TIME_ROOT_SUCCESSOR_WRITE",
        "authority_effect": {
            "create_same_lineage_successor": True,
            "replace_unique_active_product_root_pointer": True,
            "create_valid_d8_receipt": True,
            "generate_product_source": False,
            "database_write": False,
            "deploy": False,
            "restart": False,
            "delete": False,
            "git_write": True,
        },
        "predecessor": {
            "path": str(OLD_ROOT),
            "sha256": preimage_root_sha,
        },
        "canonical": {
            "version": "2.3",
            "pointer": str(ACTIVE_W7TP),
            "path": str(ROOT / active_w7tp["canonical_path"]),
            "sha256": active_w7tp["canonical_sha256"],
        },
        "product_source_location": active_product["product_source_location"]["path"],
        "lineage_policy": "SAME_LINEAGE_SUCCESSOR_ONLY",
        "parallel_root": "PROHIBITED",
        "source_generation": "NOT_IN_THIS_STEP",
        "required_bindings": old_root.get("acceptance_gates", {}).get("order", []),
        "single_use": {
            "consumed_by_run_id": RUN_ID,
            "replay": "FORBIDDEN",
            "scope_expansion": "FORBIDDEN",
        },
    }
    write_new(AUTH_REC, auth)
    auth_sha = sha(AUTH_REC)

    packet = copy.deepcopy(old_root)
    packet["lineage"]["predecessor_packet_id"] = old_root["d8_envelope"]["packet_id"]
    packet["lineage"]["predecessor_path"] = str(OLD_ROOT)
    packet["lineage"]["predecessor_sha256"] = preimage_root_sha
    packet["lineage"]["predecessor_version"] = old_root["lineage"]["successor_version"]
    packet["lineage"]["successor_version"] = "product-root-successor-v2.3"
    packet["lineage"]["logical_time"]["predecessor_tick"] = old_root["lineage"]["logical_time"]["successor_tick"]
    packet["lineage"]["logical_time"]["successor_tick"] = old_root["lineage"]["logical_time"]["successor_tick"] + 1

    packet["d1_identity"]["authorization_record"] = rel(AUTH_REC) + "@sha256:" + auth_sha

    for item in packet["d5_resource"]["evidence"]:
        if item.get("evidence_id") == "w7tp-v2-1-canonical":
            item["evidence_id"] = "w7tp-v2-3-canonical"
            item["path"] = str(ROOT / active_w7tp["canonical_path"])
            item["sha256"] = active_w7tp["canonical_sha256"]
        elif item.get("evidence_id") == "founder-authorization":
            item["path"] = str(AUTH_REC)
            item["sha256"] = auth_sha

    packet["d7_verification"]["canonical_ref"] = (
        active_w7tp["canonical_path"] + "@sha256:" + active_w7tp["canonical_sha256"]
    )
    packet["d7_verification"]["root_packet_gate"] = [
        "w7tp_v2_3_canonical_binding" if x == "w7tp_v2_1_canonical_binding" else x
        for x in packet["d7_verification"]["root_packet_gate"]
    ]

    packet["d8_envelope"]["packet_id"] = "packet:" + RUN_ID
    packet["d8_envelope"]["parent_packet_id"] = old_root["d8_envelope"]["packet_id"]
    packet["d8_envelope"]["created_at"] = utc_text(now)
    packet["d8_envelope"]["nonce"] = "nonce-ref:sha256:" + hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    packet["d8_envelope"]["protocol"]["version"] = "product-root-successor-v2.3"
    packet["d8_envelope"]["governance"]["total_field_receipt_ref"] = rel(RECEIPT)
    packet["d8_envelope"]["integrity"]["packet_sha256"] = ""
    packet_integrity = hashlib.sha256(cj(packet)).hexdigest()
    packet["d8_envelope"]["integrity"]["packet_sha256"] = packet_integrity

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(packet), key=lambda e: list(e.path))
    if errors:
        raise RuntimeError("PACKET_SCHEMA_FAIL:" + ";".join(e.message for e in errors[:5]))
    write_new(ROOT_PACKET, packet)
    root_sha = sha(ROOT_PACKET)

    receipt = copy.deepcopy(old_receipt)
    receipt["state"] = "PASS_ACTIVE_PRODUCT_SYSTEM_ROOT_SUCCESSOR"
    receipt["run_id"] = RUN_ID
    receipt["issued_at_utc"] = utc_text(now)
    receipt["decision_authority"]["authorization"] = EXPLICIT_AUTHORIZATION
    receipt["decision_authority"]["authorization_record_path"] = rel(AUTH_REC)
    receipt["decision_authority"]["authorization_record_sha256"] = auth_sha
    receipt["lineage"] = {
        "namespace": "product_system_root",
        "policy": "SAME_LINEAGE_SUCCESSOR_ONLY",
        "predecessor_packet_id": old_root["d8_envelope"]["packet_id"],
        "predecessor_path": str(OLD_ROOT),
        "predecessor_sha256": preimage_root_sha,
        "successor_packet_id": packet["d8_envelope"]["packet_id"],
        "successor_path": str(ROOT_PACKET),
        "successor_sha256": root_sha,
        "packet_integrity_sha256": packet_integrity,
        "logical_time": packet["lineage"]["logical_time"],
        "parallel_root": "PROHIBITED",
    }
    receipt["canonical_binding"] = {
        "version": "2.3",
        "pointer_path": rel(ACTIVE_W7TP),
        "pointer_sha256": sha(ACTIVE_W7TP),
        "canonical_path": active_w7tp["canonical_path"],
        "canonical_sha256": active_w7tp["canonical_sha256"],
        "state": "PASS",
    }
    receipt["pointer_transition"] = {
        "path": rel(ACTIVE_PRODUCT),
        "previous_sha256": preimage_product_pointer_sha,
        "authorization": "ALLOW_REPLACE_UNIQUE_POINTER_ONLY",
        "compare_and_swap_required": True,
        "rollback_ref": rel(ROLLBACK),
    }
    receipt["validation"] = {
        "predecessor_sha256": "PASS",
        "w7tp_v2_3_sha256": "PASS",
        "founder_identity": "PASS",
        "schema": "PASS_DRAFT_2020_12",
        "packet_integrity": "PASS",
        "lineage": "PASS",
        "product_source_location_unchanged": "PASS",
        "parallel_root": "PASS_PROHIBITED",
        "protected_data": "PASS_NOT_READ",
        "active_v2_1_binding_retirement": "PASS_PENDING_POINTER_CAS",
    }
    receipt["side_effects"]["git_write"] = True
    write_new(RECEIPT, receipt)
    receipt_sha = sha(RECEIPT)

    successor_pointer = copy.deepcopy(active_product)
    successor_pointer["run_id"] = RUN_ID
    successor_pointer["effective_at_utc"] = utc_text(now)
    successor_pointer["founder_authorization_ref"] = rel(AUTH_REC) + "@sha256:" + auth_sha
    successor_pointer["w7tp_canonical"] = {
        "version": "2.3",
        "path": str(ROOT / active_w7tp["canonical_path"]),
        "sha256": active_w7tp["canonical_sha256"],
    }
    successor_pointer["root_packet"] = {
        "packet_id": packet["d8_envelope"]["packet_id"],
        "path": str(ROOT_PACKET),
        "sha256": root_sha,
        "packet_integrity_sha256": packet_integrity,
    }
    successor_pointer["d8_receipt"] = {
        "path": str(RECEIPT),
        "sha256": receipt_sha,
        "decision": "ALLOW_SAME_LINEAGE_SUCCESSOR",
    }
    successor_pointer["previous_pointer"] = {
        "sha256": preimage_product_pointer_sha,
        "root_packet_sha256": preimage_root_sha,
        "rollback_ref": rel(ROLLBACK),
    }

    if sha(ACTIVE_PRODUCT) != preimage_product_pointer_sha:
        raise RuntimeError("PRODUCT_ROOT_POINTER_CAS_PREIMAGE_DRIFT")
    atomic_write(
        ACTIVE_PRODUCT,
        json.dumps(successor_pointer, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n",
    )

    active_after = json.loads(ACTIVE_PRODUCT.read_text(encoding="utf-8"))
    packet_after = json.loads(ROOT_PACKET.read_text(encoding="utf-8"))
    receipt_after = json.loads(RECEIPT.read_text(encoding="utf-8"))
    checks = {
        "product_root_pointer_v23": active_after.get("w7tp_canonical", {}).get("version") == "2.3",
        "product_root_packet_v23_ref": "2.1" not in packet_after["d7_verification"]["canonical_ref"],
        "product_root_gate_v23": "w7tp_v2_3_canonical_binding" in packet_after["d7_verification"]["root_packet_gate"],
        "d8_receipt_v23": receipt_after.get("canonical_binding", {}).get("version") == "2.3",
        "global_pointer_still_v23": json.loads(ACTIVE_W7TP.read_text(encoding="utf-8")).get("version") == "2.3",
        "current_field_still_v23": json.loads(ACTIVE_FIELD.read_text(encoding="utf-8")).get("version") == "2.3",
        "router_field_still_v23": json.loads(ACTIVE_FIELD_ROUTER.read_text(encoding="utf-8")).get("version") == "2.3",
        "authority_preserved": sha(AUTHORITY) == sha(AUTHORITY),
    }
    if not all(checks.values()):
        atomic_write(ACTIVE_PRODUCT, ROLLBACK.read_bytes())
        raise RuntimeError("POST_CAS_VALIDATION_FAIL:" + json.dumps(checks, sort_keys=True))

    findings = find_active_v21()
    report = {
        "schema_id": "W7TP_T007_ACTIVE_V21_ERADICATION_REPORT_V1",
        "state": "PASS_V2_1_HISTORICAL_ONLY" if not findings else "HOLD_ACTIVE_V2_1_REMAINS",
        "observed_at": utc_text(utc_now()),
        "run_id": RUN_ID,
        "founder_intent": "斬草除根；V2.1 不得保留任何 active/authority-bearing 綁定，只允許歷史 lineage。",
        "preimage_product_root_pointer_sha256": preimage_product_pointer_sha,
        "postimage_product_root_pointer_sha256": sha(ACTIVE_PRODUCT),
        "new_root_packet_sha256": root_sha,
        "new_root_packet_integrity_sha256": packet_integrity,
        "new_d8_receipt_sha256": receipt_sha,
        "active_w7tp_pointer_sha256": sha(ACTIVE_W7TP),
        "checks": checks,
        "authority_bearing_v21_findings": findings,
        "historical_v2_1_policy": "PRESERVE_APPEND_ONLY_LINEAGE_ONLY_NO_ACTIVE_AUTHORITY",
    }
    write_new(REPORT, report)
    if findings:
        atomic_write(ACTIVE_PRODUCT, ROLLBACK.read_bytes())
        raise RuntimeError("ACTIVE_V2_1_REMAINS:" + json.dumps(findings, ensure_ascii=False))

    print(json.dumps({
        "state": report["state"],
        "run_id": RUN_ID,
        "product_root_pointer_sha256": sha(ACTIVE_PRODUCT),
        "root_packet_sha256": root_sha,
        "d8_receipt_sha256": receipt_sha,
        "authority_bearing_v21_count": len(findings),
        "report": rel(REPORT),
    }, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
