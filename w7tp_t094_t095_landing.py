from pathlib import Path
from datetime import datetime, timezone
import hashlib, shutil

ROOT = Path.home() / "Taiji_Hub"
TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

src_candidates = [
    ROOT / "runtime/sandbox/xiaoj_total_field_registry_v2/XIAOJ_TOTAL_FIELD_REGISTRY_V2.yaml",
    ROOT / "runtime/sandbox/xiaoj_total_field_registry_v2/XIAOJ_TOTAL_FIELD_REGISTRY_V2.yml",
]

src = next((p for p in src_candidates if p.exists()), None)

canonical_dir = ROOT / "W7TP_FIELD_ATLAS/xiaoj_total_field"
canonical_dir.mkdir(parents=True, exist_ok=True)
dst = canonical_dir / "XIAOJ_TOTAL_FIELD_REGISTRY_V2.yaml"

blocker_files = sorted(canonical_dir.glob("XIAOJ_TOTAL_FIELD_V2_PRE_LANDING_BLOCKER_*.yaml"))

backup_dir = ROOT / "runtime/backups/t094_t095_landing" / TS
report_dir = ROOT / "runtime/reports/t094_t095_landing" / TS
backup_dir.mkdir(parents=True, exist_ok=True)
report_dir.mkdir(parents=True, exist_ok=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"

if dst.exists():
    shutil.copy2(dst, backup_dir / dst.name)

for b in blocker_files:
    shutil.copy2(b, backup_dir / b.name)

if not src:
    report = report_dir / "T094_T095_LANDING_FAILED.yaml"
    report.write_text(f"""id: T094_T095_LANDING_FAILED
timestamp: {TS}
reason: source_registry_missing
searched:
  - runtime/sandbox/xiaoj_total_field_registry_v2/XIAOJ_TOTAL_FIELD_REGISTRY_V2.yaml
  - runtime/sandbox/xiaoj_total_field_registry_v2/XIAOJ_TOTAL_FIELD_REGISTRY_V2.yml
blocker_cleared: false
canonical_v2_landed: false
xiaoj_review_opinion:
  recommendation: HOLD
  reason: source registry file missing
  safe_option: locate sandbox V2 registry before landing
  risk_if_approved: impossible_without_source
  risk_if_rejected: landing delayed
  required_human_action: provide registry source path
""", encoding="utf-8")
    print(report)
    raise SystemExit(2)

before_dst_sha = sha(dst)
src_sha = sha(src)

shutil.copy2(src, dst)
after_dst_sha = sha(dst)

cleared = []
for b in blocker_files:
    cleared_name = canonical_dir / (b.name + ".CLEARED_" + TS)
    b.rename(cleared_name)
    cleared.append(str(cleared_name))

report = report_dir / "T094_T095_BLOCKER_CLEAR_AND_V2_LANDING_RESULT.yaml"
report.write_text(f"""id: T094_T095_BLOCKER_CLEAR_AND_V2_LANDING_RESULT
timestamp: {TS}
source_registry: {src}
canonical_registry: {dst}
backup_dir: {backup_dir}
source_sha256: {src_sha}
canonical_sha256_before: {before_dst_sha}
canonical_sha256_after: {after_dst_sha}
blocker_files_found: {len(blocker_files)}
blocker_files_cleared:
{chr(10).join('  - ' + x for x in cleared) if cleared else '  - NONE'}
blocker_cleared: true
canonical_v2_landed: true
forbidden_actions_respected:
  db_write: false
  service_restart: false
  docker_action: false
  secret_read: false
xiaoj_review_opinion:
  recommendation: PROCEED_TO_FINAL_VERIFY
  reason: blocker cleared by rename and V2 registry landed into canonical xiaoj_total_field path.
  safe_option: run final grep/hash verification and git status review.
  risk_if_approved: low
  risk_if_rejected: canonical state remains unverified
  required_human_action: review final verification output
""", encoding="utf-8")

print(report)
print(f"src_sha={src_sha}")
print(f"dst_before={before_dst_sha}")
print(f"dst_after={after_dst_sha}")
print(f"cleared_blockers={len(cleared)}")