#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="data/internal_members/7d_codes"
LEDGER="runtime/ledger/seven_d_code_events.jsonl"
mkdir -p "$OUTDIR" runtime/ledger runtime/reports

JSON_OUT="$OUTDIR/seven_d_code_${STAMP}.json"
TXT_OUT="$OUTDIR/seven_d_code_${STAMP}.txt"
HTML_OUT="$OUTDIR/seven_d_code_${STAMP}.html"

python3 - <<PY
from pathlib import Path
import json, hashlib, datetime

ROOT = Path.home() / "Taiji_Hub"

session_file = ROOT / "runtime/state/current_member_session.json"
approved_file = ROOT / "data/internal_members/approved_members.jsonl"
map_manifest = ROOT / "topology/community_3d_map/manifest.json"

json_out = ROOT / "$JSON_OUT"
txt_out = ROOT / "$TXT_OUT"
html_out = ROOT / "$HTML_OUT"
ledger = ROOT / "$LEDGER"

def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

def load_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

session = load_json(session_file)

approved = {}
if approved_file.exists():
    for line in approved_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if obj.get("email") == "admin@wuchang.life":
                approved = obj
        except Exception:
            pass

map_state = load_json(map_manifest)

member_id = session.get("member_id") or approved.get("member_id")
member_hash = session.get("member_hash") or approved.get("member_hash")
member_email = session.get("member_email") or approved.get("email") or "admin@wuchang.life"

payload = {
    "type": "WUCHANG_SEVEN_D_CODE",
    "issued_at": now(),
    "issuer": "CHIANG_CHENG_LUNG_LOCAL_ROOT",
    "domain": "wuchang.life",
    "subject": {
        "member_id": member_id,
        "member_hash": member_hash,
        "member_email": member_email,
        "member_name": session.get("member_name") or approved.get("name"),
    },
    "dimensions": {
        "D1_member_identity": {
            "status": session.get("status") or approved.get("status"),
            "member_type": approved.get("member_type", "founder_internal"),
        },
        "D2_authority_role": {
            "authority_role": session.get("authority_role") or approved.get("authority_role"),
            "approval_source": approved.get("approval_source", "local_root_self_approval"),
        },
        "D3_phone_presence": {
            "mobile_verified": session.get("mobile_verified", False),
            "mobile_verify_method": session.get("mobile_verify_method", ""),
            "mobile_verify_status": session.get("mobile_verify_status", ""),
            "login_assurance": session.get("login_assurance", ""),
        },
        "D4_line_binding": {
            "line_login_status": session.get("line_login_status", "pending_channel_config"),
            "line_login_method": session.get("line_login_method", "line_login_oauth"),
        },
        "D5_google_workspace": {
            "google_login_status": session.get("google_login_status", "pending_client_config"),
            "business_email": "admin@wuchang.life",
            "workspace_domain": "wuchang.life",
            "nonprofit_identity": True,
        },
        "D6_odoo_erp": {
            "odoo_url": "http://127.0.0.1:8069",
            "odoo_sync_status": session.get("odoo_sync_status", approved.get("odoo_sync_status", "pending_odoo_credentials")),
            "odoo_password_still_required": True,
        },
        "D7_topology_ledger": {
            "community_3d_map_state": map_state.get("fusion_state", "unknown"),
            "community_3d_map_level": map_state.get("fusion_level", "unknown"),
            "ledger": "runtime/ledger/member_login_events.jsonl",
            "seven_d_ledger": "runtime/ledger/seven_d_code_events.jsonl",
        },
    },
    "security": {
        "contains_password": False,
        "contains_token": False,
        "contains_private_key": False,
        "public_share_level": "hash_and_status_only",
        "high_risk_actions_require_gateway": True,
    }
}

canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
code_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
payload["seven_d_code_hash"] = code_hash
payload["seven_d_code_short"] = "7D-" + code_hash[:16].upper()

json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

txt_out.write_text(
    "五常七維碼\\n"
    f"Code: {payload['seven_d_code_short']}\\n"
    f"Hash: {code_hash}\\n"
    f"Member: {member_email}\\n"
    f"Role: {payload['dimensions']['D2_authority_role']['authority_role']}\\n"
    f"Phone: {payload['dimensions']['D3_phone_presence']['mobile_verify_status']}\\n"
    f"LINE: {payload['dimensions']['D4_line_binding']['line_login_status']}\\n"
    f"Google: {payload['dimensions']['D5_google_workspace']['google_login_status']}\\n"
    f"Odoo: {payload['dimensions']['D6_odoo_erp']['odoo_sync_status']}\\n"
    f"Map: {payload['dimensions']['D7_topology_ledger']['community_3d_map_state']} level {payload['dimensions']['D7_topology_ledger']['community_3d_map_level']}\\n",
    encoding="utf-8"
)

html_out.write_text(f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>五常七維碼 {payload['seven_d_code_short']}</title>
<style>
body {{ font-family: sans-serif; padding: 24px; line-height: 1.6; }}
.card {{ max-width: 720px; border: 1px solid #ddd; border-radius: 16px; padding: 20px; box-shadow: 0 6px 18px rgba(0,0,0,.08); }}
.code {{ font-size: 28px; font-weight: 800; }}
.small {{ color: #666; font-size: 13px; word-break: break-all; }}
pre {{ background: #f7f7f7; padding: 12px; border-radius: 10px; overflow: auto; }}
</style>
</head>
<body>
<div class="card">
  <h1>五常七維碼</h1>
  <div class="code">{payload['seven_d_code_short']}</div>
  <div class="small">{code_hash}</div>
  <h2>主體</h2>
  <p>{member_email}<br>{session.get('member_name') or approved.get('name')}</p>
  <h2>七維狀態</h2>
  <pre>{json.dumps(payload["dimensions"], ensure_ascii=False, indent=2)}</pre>
  <h2>安全</h2>
  <p>不含密碼、不含 token、不含私鑰。僅作內部會員身分與拓樸狀態驗證。</p>
</div>
</body>
</html>
""", encoding="utf-8")

event = {
    "ts": now(),
    "event": "seven_d_code_issued",
    "member_id": member_id,
    "member_email": member_email,
    "seven_d_code": payload["seven_d_code_short"],
    "seven_d_code_hash": code_hash,
    "json": str(json_out.relative_to(ROOT)),
    "txt": str(txt_out.relative_to(ROOT)),
    "html": str(html_out.relative_to(ROOT)),
}

with ledger.open("a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\\n")

print(json.dumps({
    "ok": True,
    "seven_d_code": payload["seven_d_code_short"],
    "hash": code_hash,
    "json": str(json_out),
    "txt": str(txt_out),
    "html": str(html_out)
}, ensure_ascii=False, indent=2))
PY

sha256sum "$JSON_OUT" "$TXT_OUT" "$HTML_OUT" | tee "runtime/reports/seven_d_code_${STAMP}.sha256"

echo
echo "=== 七維碼文字版 ==="
cat "$TXT_OUT"

echo
echo "=== 七維碼檔案 ==="
echo "$JSON_OUT"
echo "$TXT_OUT"
echo "$HTML_OUT"

echo
echo "=== ledger latest ==="
tail -n 5 "$LEDGER"
