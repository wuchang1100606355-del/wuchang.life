#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
STATE="runtime/state/security_state_field.json"
LEDGER="runtime/ledger/security_state_events.jsonl"
REPORT="runtime/reports/security_state_field_${STAMP}.txt"

python3 - <<'PY'
from pathlib import Path
import json, datetime, socket, subprocess, hashlib

ROOT = Path.home() / "Taiji_Hub"
session_file = ROOT / "runtime/state/current_member_session.json"
state_file = ROOT / "runtime/state/security_state_field.json"
ledger = ROOT / "runtime/ledger/security_state_events.jsonl"
dead_dir = ROOT / "runtime/dead_letter"

state_file.parent.mkdir(parents=True, exist_ok=True)
ledger.parent.mkdir(parents=True, exist_ok=True)

def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

def load_json(p):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except Exception:
        return False

session = load_json(session_file)

ports = {
    "odoo_8069": port_open(8069),
    "openwebui_8080": port_open(8080),
    "gateway_8081": port_open(8081),
    "bridge_8098": port_open(8098),
    "line_8103": port_open(8103),
    "google_8104": port_open(8104),
    "ollama_11434": port_open(11434),
    "claw_9004": port_open(9004),
}

dead_letters = {}
if dead_dir.exists():
    for p in dead_dir.glob("*.jsonl"):
        try:
            dead_letters[p.name] = sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
        except Exception:
            dead_letters[p.name] = "unreadable"

public_ports = []
try:
    r = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=3)
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local_addr = parts[3]
            # only judge the Local Address:Port column, not the Peer column
            if local_addr.startswith("0.0.0.0:") or local_addr.startswith("[::]:") or local_addr.startswith(":::"):
                public_ports.append(line.strip())
except Exception:
    pass

risk = []

if session.get("session_state") != "logged_in":
    risk.append("member_not_logged_in")
if not session.get("mobile_verified", False):
    risk.append("mobile_not_verified")
if not ports["gateway_8081"]:
    risk.append("gateway_down")
if not ports["odoo_8069"]:
    risk.append("odoo_down")
if not ports["line_8103"]:
    risk.append("line_bridge_down")
if not ports["google_8104"]:
    risk.append("google_bridge_down")
if public_ports:
    risk.append("public_listening_ports_need_review")

if not risk:
    level = "GREEN"
elif "gateway_down" in risk or "odoo_down" in risk or "member_not_logged_in" in risk:
    level = "RED"
else:
    level = "YELLOW"

obj = {
    "id": "wuchang_security_state_field",
    "created_at": now(),
    "level": level,
    "risk_flags": risk,
    "member": {
        "member_id": session.get("member_id"),
        "member_hash": session.get("member_hash"),
        "member_email": session.get("member_email"),
        "login_assurance": session.get("login_assurance"),
        "mobile_verified": session.get("mobile_verified", False),
    },
    "ports": ports,
    "identity_bridges": {
        "line_status": session.get("line_login_status", "unknown"),
        "google_status": session.get("google_login_status", "unknown"),
        "odoo_sync_status": session.get("odoo_sync_status", "unknown"),
        "odoo_password_still_required": True,
    },
    "dead_letter": dead_letters,
    "public_ports_review": public_ports,
    "hard_denies": [
        "store_password",
        "store_token",
        "store_private_key",
        "bypass_odoo_password",
        "auto_replay_dead_letter",
        "external_upload_without_review"
    ],
    "secret_policy": {
        "store_passwords": False,
        "store_tokens": False,
        "store_private_keys": False,
        "secrets_location": "~/.secrets",
        "no_secret_to_memory_model": True
    }
}

canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True)
obj["security_state_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

state_file.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

with ledger.open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "ts": now(),
        "event": "security_state_field_updated",
        "level": level,
        "risk_flags": risk,
        "state": "runtime/state/security_state_field.json",
        "hash": obj["security_state_hash"]
    }, ensure_ascii=False) + "\n")

print(json.dumps(obj, ensure_ascii=False, indent=2))
PY

{
  echo "=== SECURITY STATE FIELD $STAMP ==="
  cat "$STATE"
  echo
  echo "=== ports ==="
  ss -ltnp | grep -E ':8069|:8080|:8081|:8098|:8103|:8104|:11434|:9004|:2222' || true
  echo
  echo "=== latest ledger ==="
  tail -n 10 "$LEDGER" 2>/dev/null || true
} | tee "$REPORT"

sha256sum "$STATE" "$REPORT" | tee "$REPORT.sha256"

echo
echo "STATE=$STATE"
echo "REPORT=$REPORT"
