from __future__ import annotations
import json
import hashlib
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("runtime/total_field/active/ACTIVE_6_ENGINE_CAPABILITY_REGISTRY.json")
LIVE_CTX_REL = Path("runtime/total_field/CURRENT_LIVE_DYNAMIC_CONTEXT.json")

def load_six_engine_registry(repo_root: str | Path = "/home/taiji_admin/Taiji_Hub") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    reg_path = root / REGISTRY_REL
    if not reg_path.is_file():
        raise FileNotFoundError(f"6-engine capability registry missing: {reg_path}")
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    expected = data.get("registry_sha256")
    unsigned = dict(data)
    unsigned.pop("registry_sha256", None)
    actual = hashlib.sha256(
        json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if expected != actual:
        raise ValueError("BLOCK_SIX_ENGINE_REGISTRY_HASH_MISMATCH")
    return data

def get_derivative_context_binding(repo_root: str | Path = "/home/taiji_admin/Taiji_Hub") -> dict[str, Any]:
    reg = load_six_engine_registry(repo_root)
    return {
        "capability_state": reg["state"],
        "registry_ref": REGISTRY_REL.as_posix(),
        "registry_sha256": reg["registry_sha256"],
        "active_families": list(reg["engines"].keys()),
        "zero_engine_modification_verified": reg["zero_engine_modification_verified"],
        "generic_rle_fallback_used": reg["generic_rle_fallback_used"],
    }
