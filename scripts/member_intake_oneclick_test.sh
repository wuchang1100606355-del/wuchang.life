#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
ENV_FILE="$HOME/.secrets/taiji_member_intake.env"
REPORT="runtime/reports/member_intake_oneclick_test_${STAMP}.txt"

mkdir -p runtime/reports runtime/ledger runtime/dead_letter data/internal_members ~/.secrets
chmod 700 ~/.secrets

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

# shellcheck disable=SC1090
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
s = p.read_text() if p.exists() else ""
lines = []
done = False
for line in s.splitlines():
    if line.startswith("TAIJI_MEMBER_TOKEN="):
        lines.append("TAIJI_MEMBER_TOKEN=$TOKEN")
        done = True
    else:
        lines.append(line)
if not done:
    lines.insert(0, "TAIJI_MEMBER_TOKEN=$TOKEN")
p.write_text("\\n".join(lines) + "\\n")
PY
  source "$ENV_FILE"
fi

{
  echo "=== MEMBER INTAKE ONECLICK TEST $STAMP ==="
  echo "root: $ROOT"
  echo

  echo "=== ensure service ==="
  systemctl --user daemon-reload || true

  if systemctl --user list-unit-files | grep -q '^taiji-member-intake.service'; then
    systemctl --user restart taiji-member-intake.service
  else
    echo "MISSING: taiji-member-intake.service"
    echo "請先建立 8102 member intake 服務。"
    exit 1
  fi

  sleep 3

  echo
  echo "=== health ==="
  curl -fsS http://127.0.0.1:8102/health | python3 -m json.tool

  echo
  echo "=== submit internal test member ==="

  NAME="內部測試會員_${STAMP}"
  PHONE="0900000000"
  EMAIL="internal-test-${STAMP}@example.local"

  RESP="$(curl -fsS -X POST http://127.0.0.1:8102/members/intake \
    -H "Content-Type: application/json" \
    -H "X-Taiji-Token: ${TAIJI_MEMBER_TOKEN}" \
    -d "{
      \"name\":\"${NAME}\",
      \"phone\":\"${PHONE}\",
      \"email\":\"${EMAIL}\",
      \"member_type\":\"internal\",
      \"source\":\"oneclick_internal_test\",
      \"consent\":true,
      \"note\":\"內部一鍵收件測試；不代表正式會員授權\"
    }")"

  echo "$RESP" | python3 -m json.tool

  echo
  echo "=== pending latest ==="
  tail -n 5 data/internal_members/pending_members.jsonl 2>/dev/null || true

  echo
  echo "=== ledger latest ==="
  tail -n 10 runtime/ledger/member_intake_events.jsonl 2>/dev/null || true

  echo
  echo "=== dead letter latest ==="
  tail -n 10 runtime/dead_letter/member_intake_rejected.jsonl 2>/dev/null || true

  echo
  echo "=== optional odoo sync check ==="
  if [ -n "${ODOO_USERNAME:-}" ] && [ -n "${ODOO_PASSWORD:-}" ] && [ -n "${ODOO_DB:-}" ]; then
    echo "Odoo env detected; trying sync..."
    curl -fsS -X POST http://127.0.0.1:8102/odoo/sync \
      -H "X-Taiji-Token: ${TAIJI_MEMBER_TOKEN}" | python3 -m json.tool || true
  else
    echo "Odoo credentials not configured; skipped sync."
    echo "目前只收進 pending_members.jsonl。"
  fi

  echo
  echo "=== ports ==="
  ss -ltnp | grep -E ':8102|:8069|:8081|:8080|:8098|:11434|:9004' || true

} | tee "$REPORT"

sha256sum "$REPORT" | tee "$REPORT.sha256"

printf '{"ts":"%s","event":"member_intake_oneclick_test_done","report":"%s"}\n' \
  "$(date -Is)" "$REPORT" >> runtime/ledger/member_intake_events.jsonl

echo
echo "REPORT=$REPORT"
echo "HASH=$REPORT.sha256"
