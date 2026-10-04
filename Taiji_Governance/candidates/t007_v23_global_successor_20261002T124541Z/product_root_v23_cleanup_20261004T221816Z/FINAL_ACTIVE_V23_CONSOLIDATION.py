from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/taiji_admin/Taiji_Hub").resolve()
RUN_ID = "V23_ACTIVE_SEMANTIC_CONSOLIDATION_20261004T223116Z"
OUT = ROOT / "runtime/total_field" / RUN_ID
GOV = ROOT / "Taiji_Governance/candidates/t007_v23_global_successor_20261002T124541Z/product_root_v23_cleanup_20261004T221816Z"

ACTIVE_W7TP = ROOT / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
ACTIVE_PRODUCT = ROOT / "runtime/total_field/master_index/ACTIVE_PRODUCT_SYSTEM_ROOT_POINTER.json"
ACTIVE_AUTHORITY = ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"

ACTIVE_ALLNODE = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json"
ACTIVE_ALLNODE_PTR = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_POINTER.txt"
ACTIVE_ALLNODE_ROUTER = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
ACTIVE_ALLNODE_ROUTER_PTR = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt"
ACTIVE_ROUTER_BOUNDARY = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_BOUNDARY_CANONICAL.json"
ACTIVE_ROUTER_BOUNDARY_PTR = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_BOUNDARY_POINTER.txt"
ACTIVE_ROUTER_MERGE = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_ALLNODE_MERGE.json"
ACTIVE_ROUTER_MERGE_PTR = ROOT / "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_ALLNODE_MERGE_POINTER.txt"
ACTIVE_TFCT = ROOT / "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
ACTIVE_TFCT_PTR = ROOT / "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"

REPORT = GOV / "FINAL_ACTIVE_V23_CONSOLIDATION_REPORT.json"

DIMENSIONS = {
    "D1": "Intent",
    "D2": "State",
    "D3": "Coordinate",
    "D4": "Evidence",
    "D5": "Execution/Policy",
    "D6": "Generative State Transmission",
    "D7": "Risk/Isolation",
    "D8": "Envelope/Authority",
}

TARGETS = [
    ACTIVE_PRODUCT,
    ACTIVE_ALLNODE_PTR,
    ACTIVE_ALLNODE_ROUTER_PTR,
    ACTIVE_ROUTER_BOUNDARY,
    ACTIVE_ROUTER_BOUNDARY_PTR,
    ACTIVE_ROUTER_MERGE,
    ACTIVE_ROUTER_MERGE_PTR,
    ACTIVE_TFCT,
    ACTIVE_TFCT_PTR,
]

def utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def atomic(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def write_json(path: Path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")

def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def pointer_target(pointer: Path) -> Path:
    raw = pointer.read_text(encoding="utf-8").strip()
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p

def canonical_dims_list():
    return [{"id": k, "field_en": v, "field_zh": {
        "D1":"意圖","D2":"狀態","D3":"座標","D4":"證據",
        "D5":"執行／政策","D6":"生成式狀態傳輸","D7":"風險／隔離","D8":"封套／權威"
    }[k]} for k,v in DIMENSIONS.items()]

def scan_active_v21():
    findings = []
    allowed = []
    for base in (ROOT / "runtime/total_field/master_index", ROOT / "runtime/total_field/active"):
        for p in sorted(base.glob("ACTIVE*.json")):
            try:
                doc = read_json(p)
            except Exception:
                continue
            def walk(v, path="$"):
                if isinstance(v, dict):
                    for k, x in v.items():
                        walk(x, path + "." + k)
                elif isinstance(v, list):
                    for i, x in enumerate(v):
                        walk(x, path + f"[{i}]")
                elif isinstance(v, str):
                    low = v.lower()
                    hit = (
                        v == "2.1"
                        or "canonical_v2_1" in low
                        or "w7tp_v2_1" in low
                        or "w7tp-v2-1" in low
                    )
                    if not hit:
                        return
                    record = {"source": rel(p), "path": path, "value": v}
                    if (
                        p == ACTIVE_W7TP
                        and path.startswith("$.parent.")
                        and doc.get("parent", {}).get("status") == "SUPERSEDED_BY_V2_3"
                    ):
                        allowed.append(record)
                    else:
                        findings.append(record)
            walk(doc)
    return findings, allowed

def main():
    if socket.gethostname() != "taiji01":
        raise RuntimeError("TARGET_MISMATCH")
    if REPORT.exists() or OUT.exists():
        raise RuntimeError("RUN_ALREADY_EXISTS")

    w7tp = read_json(ACTIVE_W7TP)
    product = read_json(ACTIVE_PRODUCT)
    allnode = read_json(ACTIVE_ALLNODE)
    allnode_router = read_json(ACTIVE_ALLNODE_ROUTER)
    authority_sha = sha(ACTIVE_AUTHORITY)

    if w7tp.get("version") != "2.3" or w7tp.get("canonical_id") != "W7TP_8D_ADI_V2_3":
        raise RuntimeError("W7TP_NOT_V23")
    if product.get("w7tp_canonical", {}).get("version") != "2.3":
        raise RuntimeError("PRODUCT_ROOT_NOT_V23")
    if allnode.get("version") != "2.3" or allnode_router.get("version") != "2.3":
        raise RuntimeError("CURRENT_FIELD_NOT_V23")

    preimages = {rel(p): p.read_bytes() for p in TARGETS}
    prehash = {k: hashlib.sha256(v).hexdigest() for k,v in preimages.items()}
    OUT.mkdir(parents=True, exist_ok=False)
    rollback = OUT / "rollback_preimages"
    rollback.mkdir()
    for p in TARGETS:
        dest = rollback / (p.name + "." + sha(p) + ".preimage")
        atomic(dest, p.read_bytes())

    immutable_allnode = OUT / "TRUE8D_ALLNODE_CANONICAL_V23.json"
    immutable_allnode_router = OUT / "TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL_V23.json"
    write_json(immutable_allnode, allnode)
    write_json(immutable_allnode_router, allnode_router)

    old_boundary = read_json(ACTIVE_ROUTER_BOUNDARY)
    boundary = copy.deepcopy(old_boundary)
    boundary["canonical_id"] = "W7TP_8D_ADI_V2_3"
    boundary["version"] = "2.3"
    boundary["semantics"] = "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
    boundary["dimensions"] = canonical_dims_list()
    boundary["canonical_binding"] = {
        "ref": rel(ACTIVE_W7TP),
        "sha256": sha(ACTIVE_W7TP),
        "version": "2.3",
    }
    boundary.pop("true8d_mapping", None)
    boundary["router_projection"] = {
        "D3": "router/network/hardware boundary is coordinate context",
        "D4": "SSH/hostname/kernel/receipt material is evidence",
        "D5": "network configuration or routing action belongs to Execution/Policy and requires authority",
        "D6": "carrier or router transport is not D6 by itself; D6 is Generative State Transmission",
        "D7": "network detour, unsafe change and isolation/quarantine belong to Risk/Isolation",
        "D8": "router has no independent authority; authorization remains Envelope/Authority",
    }
    boundary["legacy_semantic_mapping"] = "SUPERSEDED_READ_ONLY"
    immutable_boundary = OUT / "TRUE8D_ROUTER_BOUNDARY_CANONICAL_V23.json"
    write_json(immutable_boundary, boundary)

    old_merge = read_json(ACTIVE_ROUTER_MERGE)
    merge = copy.deepcopy(old_merge)
    merge["canonical_id"] = "W7TP_8D_ADI_V2_3"
    merge["version"] = "2.3"
    merge["semantics"] = "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
    merge["dimensions"] = canonical_dims_list()
    merge.pop("true8d_mapping", None)
    merge["router_projection"] = boundary["router_projection"]
    merge["source_pointers"] = {
        "router_pointer": rel(ACTIVE_ROUTER_BOUNDARY_PTR),
        "router_canonical": rel(immutable_boundary),
        "allnode_pointer": rel(ACTIVE_ALLNODE_ROUTER_PTR),
        "allnode_canonical": rel(immutable_allnode_router),
    }
    merge["legacy_semantic_mapping"] = "SUPERSEDED_READ_ONLY"
    immutable_merge = OUT / "TRUE8D_ROUTER_ALLNODE_MERGE_V23.json"
    write_json(immutable_merge, merge)

    old_tfct = read_json(ACTIVE_TFCT)
    tfct = copy.deepcopy(old_tfct)
    tfct["canonical_id"] = "W7TP_8D_ADI_V2_3"
    tfct["canonical_version"] = "v2.3"
    tfct["semantics"] = "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD"
    tfct["w7tp_canonical_binding"] = {
        "ref": rel(ACTIVE_W7TP),
        "sha256": sha(ACTIVE_W7TP),
        "version": "2.3",
    }
    tfct["semantic_locks"] = {
        **DIMENSIONS,
        "commit_rule": old_tfct.get("semantic_locks", {}).get("commit_rule", "ALLOW_ONLY"),
        "consensus_mode": old_tfct.get("semantic_locks", {}).get("consensus_mode", "LOCAL_EQUIVALENCE_ONLY"),
    }
    tfct["legacy_candidate_engine"] = {
        "authority": "NONE",
        "mode": "COMPATIBILITY_ONLY",
        "note": "Internal evaluator labels in policy are legacy implementation identifiers and do not define W7TP dimension semantics.",
    }
    immutable_tfct = OUT / "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V23.json"
    write_json(immutable_tfct, tfct)

    product2 = copy.deepcopy(product)
    legacy_rule = product2.get("d7", {}).get("rule_ref")
    product2["d6"] = {
        "semantic": "Generative State Transmission",
        "legacy_reference_only_rule_ref": legacy_rule,
        "legacy_rule_authority": "NONE",
        "legacy_rule_mode": "READ_ONLY_COMPATIBILITY",
    }
    product2["d7"] = {
        "semantic": "Risk/Isolation",
        "reference_only": False,
        "legacy_reference_only_rule_ref": legacy_rule,
        "legacy_rule_authority": "NONE",
    }
    product2["d8"] = {
        "semantic": "Envelope/Authority",
        "authority_ref": rel(ACTIVE_AUTHORITY),
        "authority_sha256": authority_sha,
    }
    product2["w7tp_semantics"] = {
        "canonical_id": "W7TP_8D_ADI_V2_3",
        "version": "2.3",
        "semantics": "8_IN_1_SINGLE_DYNAMIC_STATE_FIELD",
        "dimensions": DIMENSIONS,
        "active_pointer_ref": rel(ACTIVE_W7TP),
        "active_pointer_sha256": sha(ACTIVE_W7TP),
    }

    try:
        atomic(ACTIVE_ALLNODE_PTR, (rel(immutable_allnode) + "\n").encode())
        atomic(ACTIVE_ALLNODE_ROUTER_PTR, (rel(immutable_allnode_router) + "\n").encode())
        write_json(ACTIVE_ROUTER_BOUNDARY, boundary)
        atomic(ACTIVE_ROUTER_BOUNDARY_PTR, (rel(immutable_boundary) + "\n").encode())
        write_json(ACTIVE_ROUTER_MERGE, merge)
        atomic(ACTIVE_ROUTER_MERGE_PTR, (rel(immutable_merge) + "\n").encode())
        write_json(ACTIVE_TFCT, tfct)
        atomic(ACTIVE_TFCT_PTR, (rel(immutable_tfct) + "\n").encode())
        write_json(ACTIVE_PRODUCT, product2)

        pointer_checks = {}
        for ptr in (
            ACTIVE_ALLNODE_PTR,
            ACTIVE_ALLNODE_ROUTER_PTR,
            ACTIVE_ROUTER_BOUNDARY_PTR,
            ACTIVE_ROUTER_MERGE_PTR,
            ACTIVE_TFCT_PTR,
        ):
            target = pointer_target(ptr)
            pointer_checks[rel(ptr)] = {
                "target": rel(target),
                "exists": target.is_file(),
                "sha256": sha(target) if target.is_file() else None,
            }
            if not target.is_file():
                raise RuntimeError("POINTER_TARGET_MISSING:" + rel(ptr))

        after_product = read_json(ACTIVE_PRODUCT)
        after_tfct = read_json(ACTIVE_TFCT)
        after_boundary = read_json(ACTIVE_ROUTER_BOUNDARY)
        after_merge = read_json(ACTIVE_ROUTER_MERGE)

        checks = {
            "w7tp_pointer_v23": read_json(ACTIVE_W7TP).get("version") == "2.3",
            "product_root_v23": after_product.get("w7tp_canonical", {}).get("version") == "2.3",
            "product_semantics_v23": after_product.get("w7tp_semantics", {}).get("dimensions") == DIMENSIONS,
            "current_field_v23": read_json(ACTIVE_ALLNODE).get("version") == "2.3",
            "current_field_router_v23": read_json(ACTIVE_ALLNODE_ROUTER).get("version") == "2.3",
            "router_boundary_v23": after_boundary.get("version") == "2.3" and after_boundary.get("dimensions") == canonical_dims_list(),
            "router_merge_v23": after_merge.get("version") == "2.3" and after_merge.get("dimensions") == canonical_dims_list(),
            "tfct_semantic_locks_v23": all(after_tfct.get("semantic_locks", {}).get(k) == v for k,v in DIMENSIONS.items()),
            "tfct_legacy_engine_no_authority": after_tfct.get("legacy_candidate_engine", {}).get("authority") == "NONE",
            "authority_unchanged": sha(ACTIVE_AUTHORITY) == authority_sha,
            "pointer_targets_exist": all(x["exists"] for x in pointer_checks.values()),
        }
        if not all(checks.values()):
            raise RuntimeError("POST_VALIDATION_FAIL:" + json.dumps(checks, sort_keys=True))

        forbidden_phrases = (
            "Sovereign Privacy Field",
            "Generative Transmission & Resource Routing Field",
            "Red-Team Detour Alert & Quarantine Field",
            "D7_Generative_Transmission_Resource_Routing_Field",
            "D8_RedTeam_Detour_Alert_Quarantine_Field",
        )
        active_semantic_findings = []
        for p in sorted((ROOT / "runtime/total_field/active").glob("ACTIVE*.json")):
            text = p.read_text(encoding="utf-8")
            for phrase in forbidden_phrases:
                if phrase in text:
                    active_semantic_findings.append({"source": rel(p), "phrase": phrase})

        v21_findings, allowed_history = scan_active_v21()
        if active_semantic_findings:
            raise RuntimeError("OLD_ACTIVE_SEMANTICS_REMAIN:" + json.dumps(active_semantic_findings, ensure_ascii=False))
        if v21_findings:
            raise RuntimeError("ACTIVE_V21_REMAINS:" + json.dumps(v21_findings, ensure_ascii=False))

        report = {
            "schema_id": "W7TP_T007_V23_FINAL_ACTIVE_CONSOLIDATION_REPORT_V1",
            "state": "PASS_GLOBAL_V23_ACTIVE_V21_HISTORICAL_ONLY",
            "run_id": RUN_ID,
            "observed_at": utc(),
            "founder_intent": "收乾淨不要留問題",
            "context_rule": "LATEST_EXPLICIT_FOUNDER_INTENT_OVERRIDES_STALE_CHECKPOINT",
            "w7tp_pointer_sha256": sha(ACTIVE_W7TP),
            "product_root_pointer_sha256": sha(ACTIVE_PRODUCT),
            "authority_sha256": sha(ACTIVE_AUTHORITY),
            "checks": checks,
            "pointer_checks": pointer_checks,
            "active_v21_findings": v21_findings,
            "allowed_v21_history_only": allowed_history,
            "active_old_semantic_findings": active_semantic_findings,
            "preimage_sha256": prehash,
            "historical_policy": "PRESERVE_APPEND_ONLY_HISTORY_AND_EXPLICIT_NON_AUTHORITATIVE_COMPATIBILITY_ONLY",
        }
        write_json(REPORT, report)
        print(json.dumps({
            "state": report["state"],
            "run_id": RUN_ID,
            "active_v21_count": len(v21_findings),
            "active_old_semantic_count": len(active_semantic_findings),
            "allowed_v21_history_count": len(allowed_history),
            "report": rel(REPORT),
        }, ensure_ascii=False, sort_keys=True))
    except Exception:
        for p in reversed(TARGETS):
            atomic(p, preimages[rel(p)])
        raise

if __name__ == "__main__":
    main()
