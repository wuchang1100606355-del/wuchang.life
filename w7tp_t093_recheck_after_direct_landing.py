from pathlib import Path
from datetime import datetime, timezone
import hashlib

ROOT = Path.home() / "Taiji_Hub"
TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

master = ROOT / "W7TP_FIELD_ATLAS/02_governed_hive_master_index.yaml"
blocker_dir = ROOT / "W7TP_FIELD_ATLAS/xiaoj_total_field"
report_dir = ROOT / "runtime/reports/direct_landing" / TS
report_dir.mkdir(parents=True, exist_ok=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"

txt = master.read_text(encoding="utf-8") if master.exists() else ""
blocker_files = sorted(blocker_dir.glob("XIAOJ_TOTAL_FIELD_V2_PRE_LANDING_BLOCKER_*.yaml")) if blocker_dir.exists() else []

checks = {
    "master_index_exists": master.exists(),
    "candidate_resolution_registered": "xiaoj_total_field_candidate_resolution" in txt,
    "sync_executors_registered": "sync_executors" in txt,
    "sync_reports_registered": "sync_reports" in txt,
    "docs_specs_registered": "docs_specs" in txt,
    "docs_w7tp_algorithms_registered": "docs_w7tp_algorithms" in txt,
    "task_board_policies_merged": "task_board_policies" in txt and "MERGE" in txt,
    "docs_runtime_aliased": "docs_runtime" in txt and "ALIAS" in txt,
    "blocker_file_exists": len(blocker_files) > 0,
}

clear_ready = all(checks.values())

out = report_dir / "T093_RECHECK_BLOCKER_AFTER_DIRECT_LANDING.yaml"
out.write_text(f"""id: T093_RECHECK_BLOCKER_AFTER_DIRECT_LANDING
timestamp: {TS}
mode: REVIEW_ONLY
master_index: {master}
master_index_sha256: {sha(master)}
blocker_files:
{chr(10).join('  - ' + str(p) for p in blocker_files) if blocker_files else '  - NONE'}

checks:
{chr(10).join(f'  {k}: {str(v).lower()}' for k, v in checks.items())}

decision:
  blocker_clear_ready: {str(clear_ready).lower()}
  blocker_removed: false
  canonical_v2_landed: false

xiaoj_review_opinion:
  recommendation: {'READY_FOR_BLOCKER_CLEAR_AUTHORIZATION' if clear_ready else 'KEEP_BLOCKER_ACTIVE'}
  reason: {'T091/T092 direct landing evidence is present.' if clear_ready else 'Required direct landing evidence is incomplete.'}
  safe_option: {'authorize blocker clear as next explicit step' if clear_ready else 'keep blocker active and repair missing evidence'}
  risk_if_approved: low
  risk_if_rejected: V2 landing remains blocked
  required_human_action: review T093 recheck result and authorize T094 blocker clear / V2 landing sequence
""", encoding="utf-8")

print(out)
print(f"blocker_clear_ready={clear_ready}")