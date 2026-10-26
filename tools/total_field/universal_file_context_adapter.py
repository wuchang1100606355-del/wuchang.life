from __future__ import annotations
import sys
from pathlib import Path as _Path
_REPO_ROOT = str(_Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import hashlib
import json
import datetime
from pathlib import Path
from typing import Any
from tools.total_field.six_engine_capability_hub import load_six_engine_registry
from core.adi_native.evidence_ledger import VerifiableSpacetimeSystem
import tools.total_field.d4_adi_v2_record_wiring as d4_wiring

HISTORICAL_BLOCKED_PREFIXES = (
    "/mnt/taiji_cloud_drive",
    "/mnt/taiji_cloud_drive/時空/EXPORT_DATA",
    "/mnt/taiji_cloud_drive/時空/SECURED_ARCHIVE",
)

EXT_TO_FAMILY = {
    ".wav": "F1_AUDIO_PCM", ".pcm": "F1_AUDIO_PCM", ".mp3": "F1_AUDIO_PCM", ".flac": "F1_AUDIO_PCM",
    ".mp4": "F2_VISUAL_TEMPORAL", ".avi": "F2_VISUAL_TEMPORAL", ".mov": "F2_VISUAL_TEMPORAL", ".npy": "F2_VISUAL_TEMPORAL",
    ".bvh": "F3_BONE_COORDINATE", ".fbx": "F3_BONE_COORDINATE", ".c3d": "F3_BONE_COORDINATE",
    ".json": "F4_STRUCTURED_RECORD", ".jsonl": "F4_STRUCTURED_RECORD", ".csv": "F4_STRUCTURED_RECORD", ".sqlite3": "F4_STRUCTURED_RECORD",
    ".md": "F5_DOCUMENT_CONTAINER", ".txt": "F5_DOCUMENT_CONTAINER", ".docx": "F5_DOCUMENT_CONTAINER", ".pdf": "F5_DOCUMENT_CONTAINER", ".py": "F5_DOCUMENT_CONTAINER",
    ".zip": "F6_BINARY_ARCHIVE", ".tar": "F6_BINARY_ARCHIVE", ".gz": "F6_BINARY_ARCHIVE", ".bin": "F6_BINARY_ARCHIVE",
}

def bind_file_to_dynamic_context(
    file_path: str | Path,
    *,
    repo_root: str | Path = "/home/taiji_admin/Taiji_Hub",
    actor_ref: str = "founder:taiji01",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    target = Path(file_path).resolve()
    target_str = str(target)

    if any(target_str.startswith(prefix) for prefix in HISTORICAL_BLOCKED_PREFIXES) or not target.is_relative_to(root):
        return {
            "state": "BLOCK_HISTORICAL_OR_OUTSIDE_CANONICAL_ROOT",
            "reason": f"Rejected non-current or historical archive path outside {root}: {target_str}",
        }

    if not target.is_file():
        raise FileNotFoundError(f"target file not found: {target}")

    reg = load_six_engine_registry(root)
    ext = target.suffix.lower()
    family_key = EXT_TO_FAMILY.get(ext, "F6_BINARY_ARCHIVE")
    engine_spec = reg["engines"][family_key]

    raw_bytes = target.read_bytes()
    file_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    rel_path = target.relative_to(root).as_posix()
    now_compact = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    descriptor = {
        "item_id": f"ctx_item:{family_key.lower()}:{file_sha256[:16]}",
        "path": rel_path,
        "size_bytes": len(raw_bytes),
        "file_sha256": file_sha256,
        "routed_engine_family": family_key,
        "routed_capability": engine_spec["capability"],
        "engine_verified_anchor_sha256": engine_spec.get("verified_sha256") or engine_spec.get("verified_docx_sha256"),
        "bound_at_utc": now_compact,
    }

    ctx_path = root / "runtime/total_field/CURRENT_LIVE_DYNAMIC_CONTEXT.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    ctx.pop("packet_sha256", None)
    ctx["historical_archive_isolation_enforced"] = True
    ctx.setdefault("universal_file_context_items", [])
    ctx["universal_file_context_items"] = [
        item for item in ctx["universal_file_context_items"] if item.get("path") != rel_path
    ] + [descriptor]
    ctx["context_id"] = f"ctx:universal-6engine-bound:{now_compact}"

    canonical_bytes = json.dumps(ctx, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ctx["packet_sha256"] = hashlib.sha256(canonical_bytes).hexdigest()

    formatted = json.dumps(ctx, indent=2, ensure_ascii=False)
    ctx_path.write_text(formatted, encoding="utf-8")
    (root / "LIVE_DYNAMIC_CONTEXT.json").write_text(formatted, encoding="utf-8")

    ledger_path = root / "runtime/total_field/d4_six_engine_capability_ledger.jsonl"
    ledger = VerifiableSpacetimeSystem(
        ledger_path,
        legacy_file_sha256=hashlib.sha256((root / "runtime/total_field/active/ACTIVE_6_ENGINE_CAPABILITY_REGISTRY.json").read_bytes()).hexdigest(),
        legacy_chain_head=reg["registry_sha256"],
    )
    d4_wiring.append_fact(
        ledger,
        fact_id=f"fact:file_bound:{file_sha256[:12]}:{now_compact}",
        fact_type="UNIVERSAL_FILE_BOUND_VIA_SIX_ENGINE_HUB",
        payload_sha256=ctx["packet_sha256"],
        source_ref=rel_path,
        actor_ref=actor_ref,
        accountable_person_ref="founder:natural_person_root",
    )
    return {
        "state": "PASS_FILE_BOUND_TO_DYNAMIC_CONTEXT",
        "routed_engine_family": family_key,
        "file_sha256": file_sha256,
        "context_packet_sha256": ctx["packet_sha256"],
        "ledger_verify": d4_wiring.verify(ledger),
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="W7TP 8D ADI V2.3 — 6-Engine Universal File Dynamic Context Adapter")
    parser.add_argument("files", nargs="+", help="One or more file paths to route through the 6 engines into Dynamic Context")
    parser.add_argument("--repo-root", default="/home/taiji_admin/Taiji_Hub")
    args = parser.parse_args()
    results = [bind_file_to_dynamic_context(f, repo_root=args.repo_root) for f in args.files]
    print(json.dumps({"state": "PASS_BATCH_PROCESSED", "count": len(results), "results": results}, indent=2, ensure_ascii=False))
