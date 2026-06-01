#!/usr/bin/env bash
set -euo pipefail

cd "${TAIJI_ROOT:-$HOME/Taiji_Hub}" || exit 1

python3 - <<'PY'
from pathlib import Path
import json, datetime, hashlib

ROOT = Path.home() / "Taiji_Hub"
approved = ROOT / "data/internal_members/approved_members.jsonl"
session_file = ROOT / "runtime/state/current_member_session.json"
ledger = ROOT / "runtime/ledger/member_login_events.jsonl"
report_dir = ROOT / "runtime/reports"

report_dir.mkdir(parents=True, exist_ok=True)
ledger.parent.mkdir(parents=True, exist_ok=True)

TARGET_EMAIL = "admin@wuchang.life"

def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

approved_member = None
for line in approved.read_text(encoding="utf-8", errors="ignore").splitlines():
    if not line.strip():
        continue
    obj = json.loads(line)
    if obj.get("email") == TARGET_EMAIL:
        approved_member = obj

if not approved_member:
    raise SystemExit("missing approved member")

session = {}
if session_file.exists():
    session = json.loads(session_file.read_text(encoding="utf-8"))

session.update({
    "session_state": "logged_in",
    "member_id": approved_member.get("member_id"),
    "member_hash": approved_member.get("member_hash"),
    "member_email": approved_member.get("email"),
    "member_name": approved_member.get("name"),
    "status": approved_member.get("status"),
    "authority_role": approved_member.get("authority_role", "founder_internal_member"),
    "odoo_sync_status": approved_member.get("odoo_sync_status", "pending_odoo_credentials"),
    "login_method": session.get("login_method", "local_oneclick"),
})

if session.get("mobile_verified"):
    session["login_assurance"] = "member_plus_phone_presence"
else:
    session["login_assurance"] = "member_only_phone_pending"

session_file.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

event = {
    "ts": now(),
    "event": "member_session_repaired_with_approved_member",
    "member_id": session.get("member_id"),
    "member_hash": session.get("member_hash"),
    "member_email": session.get("member_email"),
    "mobile_verified": session.get("mobile_verified", False),
    "login_assurance": session.get("login_assurance"),
}

with ledger.open("a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
report = report_dir / f"member_session_repair_{stamp}.txt"
report.write_text(json.dumps({
    "event": event,
    "session": session,
}, ensure_ascii=False, indent=2), encoding="utf-8")

sha = hashlib.sha256(report.read_bytes()).hexdigest()
(report.with_suffix(report.suffix + ".sha256")).write_text(f"{sha}  {report}\n", encoding="utf-8")

print(json.dumps({
    "ok": True,
    "member_id": session.get("member_id"),
    "member_email": session.get("member_email"),
    "mobile_verified": session.get("mobile_verified", False),
    "login_assurance": session.get("login_assurance"),
    "session": str(session_file),
    "report": str(report),
    "sha256": sha
}, ensure_ascii=False, indent=2))
PY

echo
echo "=== current member session ==="
cat runtime/state/current_member_session.json

echo
echo "=== latest login ledger ==="
tail -n 10 runtime/ledger/member_login_events.jsonl
