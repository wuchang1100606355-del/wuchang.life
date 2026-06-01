#!/usr/bin/env bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
BASE="$(pwd)"
IDX="indexes"
ARC="archive_converged"
PEND="_pending_delete/nonessential_$TS"
REP="reports"

mkdir -p "$IDX" "$ARC" "$PEND" "$REP"

HUMAN_INDEX="$IDX/HUMAN_FILE_INDEX_$TS.md"
AI_INDEX="$IDX/AI_FILE_TENSOR_INDEX_$TS.json"
MANIFEST="$IDX/ARCHIVE_MANIFEST_$TS.tsv"
ARCHIVE="$ARC/taiji_nonessential_context_$TS.tar.gz"
SHA="$ARCHIVE.sha256"
REPORT="$REP/archive_stage_delete_report_$TS.md"

CANDIDATES=(
  "_archive_bak"
  "_snapshots"
  "_evidence"
  "evidence_snapshots"
  "archive"
  "_trash_miscreated"
  "wuchang_cognition_archive"
  "Taiji_Hub.tar.gz"
  "wuchang_cognition_archive_20260505_003744.tar.gz"
  "wuchang_cognition_archive_20260505_003744.tar.gz.sha256"
  ".venv-browser"
)

PROTECTED=(
  "keys"
  "security"
  "config"
  "taiji_env"
  "admin"
  "admin.pub"
  "open_webui_data"
  "Taiji_Odoo/postgres_data"
  ".env"
)

is_protected() {
  local x="$1"
  for p in "${PROTECTED[@]}"; do
    [[ "$x" == "$p" || "$x" == "$p/"* ]] && return 0
  done
  return 1
}

echo -e "path\ttype\tsize_bytes\tsha256\tmtime_epoch\tdecision" > "$MANIFEST"

{
echo "# Taiji Human File Index"
echo
echo "timestamp: $TS"
echo "base: $BASE"
echo
echo "## Protected"
for p in "${PROTECTED[@]}"; do
  [ -e "$p" ] && echo "- PROTECTED: $p"
done
echo
echo "## Archive Candidates"
for c in "${CANDIDATES[@]}"; do
  [ -e "$c" ] && echo "- ARCHIVE_AND_STAGE: $c"
done
echo
echo "## Root Inventory"
find . -maxdepth 1 -mindepth 1 -printf '%M %12s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort
} > "$HUMAN_INDEX"

for x in "${CANDIDATES[@]}"; do
  [ -e "$x" ] || continue
  is_protected "$x" && continue

  if [ -f "$x" ]; then
    size="$(stat -c '%s' "$x" 2>/dev/null || echo 0)"
    hash="$(sha256sum "$x" 2>/dev/null | awk '{print $1}')"
    mt="$(stat -c '%Y' "$x" 2>/dev/null || echo 0)"
    echo -e "$x\tfile\t$size\t$hash\t$mt\tarchive_and_stage" >> "$MANIFEST"
  elif [ -d "$x" ]; then
    find "$x" -type f 2>/dev/null | while read -r f; do
      is_protected "$f" && continue
      size="$(stat -c '%s' "$f" 2>/dev/null || echo 0)"
      hash="$(sha256sum "$f" 2>/dev/null | awk '{print $1}')"
      mt="$(stat -c '%Y' "$f" 2>/dev/null || echo 0)"
      echo -e "$f\tfile\t$size\t$hash\t$mt\tarchive_and_stage" >> "$MANIFEST"
    done
  fi
done

tar_items=()
for x in "${CANDIDATES[@]}"; do
  [ -e "$x" ] || continue
  is_protected "$x" && continue
  tar_items+=("$x")
done

if [ "${#tar_items[@]}" -gt 0 ]; then
  tar --warning=no-file-changed \
    --exclude='*/.git/*' \
    --exclude='*/node_modules/*' \
    --exclude='*/__pycache__/*' \
    -czf "$ARCHIVE" "${tar_items[@]}" 2>"$REP/archive_tar_warnings_$TS.log" || true

  sha256sum "$ARCHIVE" > "$SHA"

  echo "=== VERIFY ARCHIVE ===" > "$REP/archive_verify_$TS.txt"
  tar -tzf "$ARCHIVE" >/dev/null 2>>"$REP/archive_verify_$TS.txt"
  VERIFY_CODE=$?

  if [ "$VERIFY_CODE" -eq 0 ]; then
    for x in "${tar_items[@]}"; do
      [ -e "$x" ] || continue
      parent="$(dirname "$PEND/$x")"
      mkdir -p "$parent"
      mv "$x" "$PEND/$x"
    done
    STAGE_STATUS="moved_to_pending_delete"
  else
    STAGE_STATUS="archive_verify_failed_no_move"
  fi
else
  echo "NO_ARCHIVE_ITEMS" > "$SHA"
  STAGE_STATUS="no_items"
fi

python3 - <<PY
import json, pathlib
manifest = pathlib.Path("$MANIFEST")
rows = []
if manifest.exists():
    lines = manifest.read_text(encoding="utf-8", errors="ignore").splitlines()
    if lines:
        header = lines[0].split("\\t")
        for line in lines[1:]:
            parts = line.split("\\t")
            if len(parts) == len(header):
                rows.append(dict(zip(header, parts)))
data = {
  "index_type": "TAIJI_AI_FILE_TENSOR_INDEX_V1",
  "timestamp": "$TS",
  "base": "$BASE",
  "human_index": "$HUMAN_INDEX",
  "manifest": "$MANIFEST",
  "archive": "$ARCHIVE",
  "sha256": "$SHA",
  "pending_delete_dir": "$PEND",
  "stage_status": "$STAGE_STATUS",
  "policy": {
    "direct_delete": False,
    "archive_before_stage": True,
    "protected": [
      "keys", "security", "config", "taiji_env", "admin", "admin.pub",
      "open_webui_data", "Taiji_Odoo/postgres_data", ".env"
    ]
  },
  "archive_manifest": rows
}
pathlib.Path("$AI_INDEX").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
PY

{
echo "# Taiji Archive + Stage Delete Report"
echo
echo "timestamp: $TS"
echo "status: $STAGE_STATUS"
echo "archive: $ARCHIVE"
echo "sha256: $SHA"
echo "pending_delete_dir: $PEND"
echo "human_index: $HUMAN_INDEX"
echo "ai_index: $AI_INDEX"
echo "manifest: $MANIFEST"
echo
echo "## Staged Items"
find "$PEND" -maxdepth 3 -mindepth 1 -print 2>/dev/null | sort
echo
echo "## Remaining Root"
find . -maxdepth 1 -mindepth 1 -printf '%M %12s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort
} > "$REPORT"

echo "$REPORT"
echo "$HUMAN_INDEX"
echo "$AI_INDEX"
echo "$MANIFEST"
echo "$ARCHIVE"
echo "$SHA"
echo "$PEND"
