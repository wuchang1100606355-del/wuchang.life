#!/usr/bin/env python3
"""Gemini Dedicated 8D-ADI Dynamic Context & Express Skill."""
import sys, os, json, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_FILE = ROOT / "LIVE_DYNAMIC_CONTEXT.json"

def sha256_file(p: Path) -> str:
    if not p.is_file(): return "MISSING"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

def git_short_status():
    res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    return {"total_changed": len(lines), "head_items": lines[:12]}

def build_viewport_packet(target_rel: str = None):
    # 1. Inspect Broker & Transport readiness
    broker_methods = []
    try:
        import tools.total_field_dynamic_context_pull as pull_mod
        broker_methods = [m for m in dir(pull_mod.TotalFieldDynamicContextPullBroker) if not m.startswith("_")]
    except Exception as e:
        broker_methods = [f"ERR: {e}"]

    packet = {
        "skill": "GEMINI_8D_ADI_VIEWPORT_BRIDGE_V1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        "broker_ready": broker_methods,
        "core_engines": {
            "dynamic_pull": sha256_file(ROOT / "tools/total_field_dynamic_context_pull.py"),
            "w7tp_transport": sha256_file(ROOT / "tools/w7tp_bridge_dynamic_context_transport_v1.py"),
            "effect_gate": sha256_file(ROOT / "capabilities/w7tp-deterministic-effect-gate/scripts/effect_gate.py"),
            "validate_flow": sha256_file(ROOT / "capabilities/w7tp-8d-adi-change-to-closure/scripts/validate_flow.py"),
            "d8_authority": sha256_file(ROOT / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"),
        },
        "git_state": git_short_status(),
    }

    # 2. If a target file is specified, extract compact AST/signature cell for Gemini viewport
    if target_rel:
        tp = ROOT / target_rel
        if tp.is_file():
            text = tp.read_text(errors="replace").splitlines()
            sigs = [f"L{i+1}: {line.strip()}" for i, line in enumerate(text)
                    if line.lstrip().startswith(("def ", "class ", "async def ", "return ", "raise "))][:25]
            packet["active_cell"] = {
                "path": target_rel,
                "sha256_16": sha256_file(tp),
                "lines": len(text),
                "signatures": sigs,
                "tail_preview": text[-15:]
            }
        else:
            packet["active_cell"] = {"error": f"Not found: {target_rel}"}

    OUT_FILE.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Gemini Context synced -> {OUT_FILE.name} ({OUT_FILE.stat().st_size} bytes)")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "tools/w7tp_bridge_dynamic_context_transport_v1.py"
    build_viewport_packet(target)
