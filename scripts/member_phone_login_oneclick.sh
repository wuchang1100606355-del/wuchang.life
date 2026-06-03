#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT" || exit 1

mkdir -p \
  data/internal_members \
  runtime/state \
  runtime/ledger \
  runtime/reports \
  configs \
  scripts

# 確保會員登入 session 存在
if [ -x scripts/member_login_oneclick.sh ]; then
  scripts/member_login_oneclick.sh >/dev/null 2>&1 || true
fi

python3 - <<'PY'
from pathlib import Path
import json, datetime, hashlib, subprocess

ROOT = Path.home() / "Taiji_Hub"

session_file = ROOT / "runtime/state/current_member_session.json"
mobile_bindings = ROOT / "data/internal_members/mobile_bindings.jsonl"
ledger = ROOT / "runtime/ledger/member_login_events.jsonl"
policy = ROOT / "configs/member_mobile_verify_policy.yaml"
report_dir = ROOT / "runtime/reports"

for p in [mobile_bindings.parent, ledger.parent, policy.parent, report_dir]:
    p.mkdir(parents=True, exist_ok=True)

APPROVED_PHONE_NODES = [
    "iphone-11",
    "v3-mix-edla-gl",
    "drallion"
]

def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

def append_jsonl(path, obj):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

if session_file.exists():
    session = json.loads(session_file.read_text(encoding="utf-8"))
else:
    session = {
        "session_state": "logged_in",
        "login_method": "local_oneclick",
        "member_email": "admin@wuchang.life",
        "member_name": "江政隆 CHIANG CHENG LUNG",
        "status": "approved_internal_founder",
        "authority_role": "founder_internal_member"
    }

tailscale_lines = []
try:
    r = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=5)
    tailscale_lines = r.stdout.splitlines()
except Exception:
    tailscale_lines = []

observed = []
for line in tailscale_lines:
    for name in APPROVED_PHONE_NODES:
        if name in line:
            online = "offline" not in line.lower()
            parts = line.split()
            ip = parts[0] if parts and parts[0].startswith("100.") else ""
            observed.append({
                "name": name,
                "ip": ip,
                "online": online,
                "raw": line
            })

online_phones = [x for x in observed if x["online"]]

verified = bool(online_phones)

binding = {
    "ts": now(),
    "member_email": session.get("member_email", "admin@wuchang.life"),
    "member_id": session.get("member_id", ""),
    "member_hash": session.get("member_hash", ""),
    "method": "tailscale_phone_presence",
    "approved_phone_nodes": APPROVED_PHONE_NODES,
    "observed_phone_nodes": observed,
    "verified": verified,
    "verify_status": "mobile_verified" if verified else "waiting_phone_online",
    "security": {
        "store_sms_code": False,
        "store_phone_token": False,
        "store_password": False,
        "store_private_key": False,
        "no_secret_to_memory_model": True
    }
}
binding["binding_hash"] = sha({
    "member_email": binding["member_email"],
    "method": binding["method"],
    "approved_phone_nodes": APPROVED_PHONE_NODES
})

append_jsonl(mobile_bindings, binding)

session["mobile_verified"] = verified
session["mobile_verify_method"] = "tailscale_phone_presence"
session["mobile_verify_status"] = binding["verify_status"]
session["mobile_verified_at"] = now() if verified else ""
session["mobile_nodes_observed"] = observed
session["mobile_nodes_online"] = online_phones
session["login_assurance"] = "member_plus_phone_presence" if verified else "member_only_phone_pending"

session_file.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

event = {
    "ts": now(),
    "event": "member_phone_login_oneclick_done",
    "member_email": session.get("member_email"),
    "member_id": session.get("member_id"),
    "mobile_verified": verified,
    "method": "tailscale_phone_presence",
    "online_phone_nodes": online_phones,
    "binding_hash": binding["binding_hash"]
}
append_jsonl(ledger, event)

policy.write_text("""member_mobile_verify_policy:
  purpose: one-click phone presence verification for internal member login
  method: tailscale_phone_presence
  approved_phone_nodes:
    - iphone-11
    - v3-mix-edla-gl
    - drallion
  rules:
    no_sms_code_storage: true
    no_password_storage: true
    no_token_storage: true
    no_secret_to_memory_model: true
    odoo_password_still_required: true
    phone_presence_is_second_factor: true
  files:
    session: runtime/state/current_member_session.json
    bindings: data/internal_members/mobile_bindings.jsonl
    ledger: runtime/ledger/member_login_events.jsonl
""", encoding="utf-8")

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
report = report_dir / f"member_phone_login_oneclick_{stamp}.txt"
report.write_text(
    "=== MEMBER PHONE LOGIN ONECLICK ===\n\n"
    + json.dumps(event, ensure_ascii=False, indent=2)
    + "\n\n=== session ===\n"
    + json.dumps(session, ensure_ascii=False, indent=2)
    + "\n\n=== binding ===\n"
    + json.dumps(binding, ensure_ascii=False, indent=2)
    + "\n",
    encoding="utf-8"
)
report_sha = hashlib.sha256(report.read_bytes()).hexdigest()
(report.with_suffix(report.suffix + ".sha256")).write_text(f"{report_sha}  {report}\n", encoding="utf-8")

print(json.dumps({
    "ok": True,
    "mobile_verified": verified,
    "verify_status": binding["verify_status"],
    "online_phone_nodes": online_phones,
    "session": str(session_file),
    "bindings": str(mobile_bindings),
    "ledger": str(ledger),
    "report": str(report),
    "sha256": report_sha
}, ensure_ascii=False, indent=2))
PY

# 補 Odoo addon 顯示手機驗證狀態
ADDON="Taiji_Odoo/addons/taiji_member_login/controllers/main.py"

if [ -f "$ADDON" ]; then
python3 - <<'PY'
from pathlib import Path

p = Path("Taiji_Odoo/addons/taiji_member_login/controllers/main.py")
s = p.read_text(encoding="utf-8")

old = '"secret_policy": "no_password_no_token_no_private_key",'
new = '''"mobile_verified": session.get("mobile_verified", False),
            "mobile_verify_method": session.get("mobile_verify_method", ""),
            "mobile_verify_status": session.get("mobile_verify_status", ""),
            "login_assurance": session.get("login_assurance", ""),
            "secret_policy": "no_password_no_token_no_private_key",'''

if old in s and "mobile_verify_status" not in s:
    s = s.replace(old, new)

p.write_text(s, encoding="utf-8")
PY
fi

VIEW="Taiji_Odoo/addons/taiji_member_login/views/login_panel.xml"
if [ -f "$VIEW" ]; then
python3 - <<'PY'
from pathlib import Path

p = Path("Taiji_Odoo/addons/taiji_member_login/views/login_panel.xml")
s = p.read_text(encoding="utf-8")

s = s.replace(
    "本頁已接入 Taiji 內部會員狀態。Odoo 登入仍使用 Odoo 帳密；會員身分、Gateway、ledger 與 dead letter 由本機系統管理。",
    "本頁已接入 Taiji 內部會員狀態與手機存在驗證。Odoo 登入仍使用 Odoo 帳密；會員身分、手機節點、Gateway、ledger 與 dead letter 由本機系統管理。"
)

if "手機驗證" not in s:
    s = s.replace(
        '<div class="taiji_member_rule">',
        '<div class="taiji_member_rule">手機驗證：使用 Tailscale 手機節點在線狀態，不儲存 SMS、不儲存 token。</div>\n        <div class="taiji_member_rule">'
    )

p.write_text(s, encoding="utf-8")
PY
fi

# 重啟 Odoo / 03 UI
if [ -d Taiji_Odoo ]; then
  (
    cd Taiji_Odoo
    docker compose restart 2>/dev/null || docker-compose restart 2>/dev/null || true
  )
fi

systemctl --user restart taiji-03-ui.service 2>/dev/null || true
sleep 3

echo
echo "=== current member session ==="
cat runtime/state/current_member_session.json

echo
echo "=== latest login ledger ==="
tail -n 10 runtime/ledger/member_login_events.jsonl

echo
echo "=== ports ==="
ss -ltnp | grep -E ':8069|:8080|:8081|:8098|:8102|:11434|:9004' || true
