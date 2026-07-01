#!/usr/bin/env python3
import json, os, re, datetime
evidence_dir = "evidence"
os.makedirs(evidence_dir, exist_ok=True)
imports_file = os.path.join(evidence_dir, "taiji_imports.txt")
pip_freeze_file = os.path.join(evidence_dir, "pip_freeze_full.txt")
mods = set()
if os.path.exists(imports_file):
    with open(imports_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.findall(r'from\s+([A-Za-z0-9_.]+)|import\s+([A-Za-z0-9_.]+)', line)
            for a,b in m:
                name = (a or b).split('.')[0]
                if name:
                    mods.add(name)
installed = set()
if os.path.exists(pip_freeze_file):
    with open(pip_freeze_file, "r", encoding="utf-8", errors="ignore") as f:
        for l in f:
            if '==' in l:
                installed.add(l.split('==')[0].lower())
plan = {"generated_at": datetime.datetime.utcnow().isoformat()+"Z", "candidates": []}
for m in sorted(mods):
    pkg_guess = m.replace('_','-').lower()
    present = (m.lower() in installed) or (pkg_guess in installed)
    plan["candidates"].append({
        "module": m,
        "pip_name_guess": pkg_guess,
        "present_in_env": present,
        "recommended_action": "verify_and_pin" if not present else "none",
        "source": None,
        "version_pin": None,
        "sha256": None,
        "risk_notes": "supply-chain check required before install"
    })
with open(os.path.join(evidence_dir, "INSTALL_PLAN.json"), "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)
print("INSTALL_PLAN_WRITTEN: evidence/INSTALL_PLAN.json")
