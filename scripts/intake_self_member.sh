#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT" || exit 1

mkdir -p data/internal_members runtime/ledger runtime/dead_letter runtime/reports ~/.secrets scripts
chmod 700 ~/.secrets

ENV_FILE="$HOME/.secrets/taiji_member_intake.env"

if [ ! -f "$ENV_FILE" ]; then
  TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
  cat > "$ENV_FILE" <<ENV
TAIJI_MEMBER_TOKEN=$TOKEN
GOOGLE_WEBHOOK_TOKEN=CHANGE_ME_GOOGLE_TOKEN
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
ODOO_URL=http://127.0.0.1:8069
ODOO_DB=odoo
ODOO_USERNAME=
ODOO_PASSWORD=
ENV
  chmod 600 "$ENV_FILE"
fi

source "$ENV_FILE"

if [ -z "${TAIJI_MEMBER_TOKEN:-}" ] || [ "${TAIJI_MEMBER_TOKEN:-}" = "CHANGE_ME_LOCAL_TOKEN" ]; then
  TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
  python3 - <<PY
from pathlib import Path
p = Path("$ENV_FILE")
s = p.read_text(encoding="utf-8") if p.exists() else ""
lines=[]
done=False
for line in s.splitlines():
    if line.startswith("TAIJI_MEMBER_TOKEN="):
        lines.append("TAIJI_MEMBER_TOKEN=$TOKEN")
        done=True
    else:
        lines.append(line)
if not done:
    lines.insert(0, "TAIJI_MEMBER_TOKEN=$TOKEN")
p.write_text("\\n".join(lines)+"\\n", encoding="utf-8")
PY
  source "$ENV_FILE"
fi

systemctl --user restart taiji-member-intake.service 2>/dev/null || true
sleep 3

STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="runtime/reports/self_member_intake_${STAMP}.txt"

{
  echo "=== SELF MEMBER INTAKE $STAMP ==="
  echo

  echo "=== health ==="
  curl -fsS http://127.0.0.1:8102/health | python3 -m json.tool

  echo
  echo "=== intake self ==="

  RESP="$(curl -fsS -X POST http://127.0.0.1:8102/members/intake \
    -H "Content-Type: application/json" \
    -H "X-Taiji-Token: ${TAIJI_MEMBER_TOKEN}" \
    -d '{
      "name":"江政隆 CHIANG CHENG LUNG",
      "phone":"",
      "email":"admin@wuchang.life",
      "member_type":"founder_internal",
      "source":"self_oneclick_internal_intake",
      "consent":true,
      "note":"本人一鍵收件；五常智慧雲/社區內部會員主體；待人工確認後同步 Odoo。"
    }')"

  echo "$RESP" | python3 -m json.tool

  echo
  echo "=== latest pending ==="
  tail -n 5 data/internal_members/pending_members.jsonl

  echo
  echo "=== latest ledger ==="
  tail -n 10 runtime/ledger/member_intake_events.jsonl

  echo
  echo "=== optional odoo sync ==="
  if [ -n "${ODOO_USERNAME:-}" ] && [ -n "${ODOO_PASSWORD:-}" ] && [ -n "${ODOO_DB:-}" ]; then
    curl -fsS -X POST http://127.0.0.1:8102/odoo/sync \
      -H "X-Taiji-Token: ${TAIJI_MEMBER_TOKEN}" | python3 -m json.tool || true
  else
    echo "Odoo credentials not configured; self member is stored in pending only."
  fi

} | tee "$REPORT"

sha256sum "$REPORT" | tee "$REPORT.sha256"

printf '{"ts":"%s","event":"self_member_intake_done","report":"%s"}\n' \
  "$(date -Is)" "$REPORT" >> runtime/ledger/member_intake_events.jsonl

echo
echo "REPORT=$REPORT"
echo "HASH=$REPORT.sha256"
