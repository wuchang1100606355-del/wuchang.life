from pathlib import Path
from datetime import datetime, timezone
import hashlib, shutil

ROOT = Path.home() / "Taiji_Hub"
TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

master = ROOT / "W7TP_FIELD_ATLAS/02_governed_hive_master_index.yaml"
backup_dir = ROOT / "runtime/backups/direct_landing" / TS
report_dir = ROOT / "runtime/reports/direct_landing" / TS
backup_dir.mkdir(parents=True, exist_ok=True)
report_dir.mkdir(parents=True, exist_ok=True)

def sha(p):
    if not p.exists():
        return "MISSING"
    return hashlib.sha256(p.read_bytes()).hexdigest()

before = sha(master)
if master.exists():
    shutil.copy2(master, backup_dir / master.name)

block = f"""

# T091_T092_DIRECT_LANDING_{TS}
xiaoj_total_field_candidate_resolution:
  source: T085_T092_direct_landing
  mode: canonical_index_patch
  added:
    sync_executors:
      classification: KEEP
      authority: candidate_sub_universe
      target: W7TP_FIELD_ATLAS/sync_executors
    sync_reports:
      classification: KEEP
      authority: candidate_sub_universe
      target: W7TP_FIELD_ATLAS/sync_reports
    docs_specs:
      classification: KEEP
      authority: specification_candidate
      target: docs/specs
    docs_w7tp_algorithms:
      classification: KEEP
      authority: algorithm_candidate
      target: docs/w7tp_algorithms
  merged:
    task_board_policies:
      classification: MERGE
      target: W7TP_FIELD_ATLAS/task_boards
  aliases:
    docs_runtime:
      classification: ALIAS
      alias_to: runtime_evidence
      authority: evidence_only
  governance:
    no_db_write: true
    no_service_restart: true
    no_secret_read: true
    blocker_remains_active: true
"""

if master.exists():
    txt = master.read_text(encoding="utf-8")
    if "xiaoj_total_field_candidate_resolution:" not in txt:
        master.write_text(txt.rstrip() + "\n" + block + "\n", encoding="utf-8")
        changed = True
    else:
        changed = False
else:
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_text(block.strip() + "\n", encoding="utf-8")
    changed = True

after = sha(master)

result = report_dir / "T091_T092_DIRECT_LANDING_RESULT.yaml"
result.write_text(f"""id: T091_T092_DIRECT_LANDING_RESULT
timestamp: {TS}
master_index: {master}
backup_dir: {backup_dir}
changed: {changed}
sha256_before: {before}
sha256_after: {after}
blocker_status: ACTIVE
canonical_v2_landed: false
next_required:
  - T093_RECHECK_BLOCKER_AFTER_DIRECT_LANDING
  - T094_V2_LANDING_AUTHORIZATION
xiaoj_review_opinion:
  recommendation: PROCEED_TO_T093_RECHECK
  reason: T091/T092 direct landing completed or already present.
  safe_option: verify master index before clearing blocker.
  risk_if_approved: low
  risk_if_rejected: V2 landing remains blocked.
  required_human_action: review direct landing result
""", encoding="utf-8")

print(result)
print(f"before={before}")
print(f"after={after}")
print(f"changed={changed}")