#!/usr/bin/env bash
set -u

TS="$(date +%Y%m%d_%H%M%S)"
BASE="$(pwd)"
OUT="reports/file_convergence_$TS.md"
JSON="reports/file_convergence_$TS.json"
DUP_HASH="reports/duplicate_hashes_$TS.txt"
DUP_NAME="reports/duplicate_basenames_$TS.txt"
SCORE="reports/subsystem_score_$TS.tsv"

EXCLUDE_DIRS=(
  "./.git"
  "./Taiji_Odoo/postgres_data"
  "./open_webui_data"
  "./node_modules"
  "./__pycache__"
  "./.venv"
  "./venv"
  "./keys"
  "./security"
  "./taiji_env"
)

PRUNE_EXPR=""
for d in "${EXCLUDE_DIRS[@]}"; do
  PRUNE_EXPR="$PRUNE_EXPR -path '$d' -o"
done

safe_find_files() {
  eval "find . \( ${PRUNE_EXPR% -o} \) -prune -o -type f -print" 2>/dev/null
}

safe_find_dirs() {
  eval "find . \( ${PRUNE_EXPR% -o} \) -prune -o -type d -print" 2>/dev/null
}

echo -e "subsystem\tfile_count\tpy\tjs\tsh\tdocker\tcompose\todoo_manifest\tpackage_json\trequirements\tgit_dir\tlast_modified" > "$SCORE"

for d in */ ; do
  d="${d%/}"
  [ "$d" = "keys" ] && continue
  [ "$d" = "security" ] && continue
  [ "$d" = "taiji_env" ] && continue

  count=$(find "$d" -maxdepth 5 -type f 2>/dev/null | wc -l | tr -d ' ')
  py=$(find "$d" -maxdepth 5 -type f -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
  js=$(find "$d" -maxdepth 5 -type f \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \) 2>/dev/null | wc -l | tr -d ' ')
  shc=$(find "$d" -maxdepth 5 -type f -name "*.sh" 2>/dev/null | wc -l | tr -d ' ')
  docker=$(find "$d" -maxdepth 5 -type f -name "Dockerfile" 2>/dev/null | wc -l | tr -d ' ')
  compose=$(find "$d" -maxdepth 5 -type f \( -name "docker-compose.yml" -o -name "docker-compose.yaml" -o -name "compose.yml" -o -name "compose.yaml" \) 2>/dev/null | wc -l | tr -d ' ')
  manifest=$(find "$d" -maxdepth 6 -type f -name "__manifest__.py" 2>/dev/null | wc -l | tr -d ' ')
  pkg=$(find "$d" -maxdepth 5 -type f -name "package.json" 2>/dev/null | wc -l | tr -d ' ')
  req=$(find "$d" -maxdepth 5 -type f -name "requirements.txt" 2>/dev/null | wc -l | tr -d ' ')
  gitd=$(find "$d" -maxdepth 2 -type d -name ".git" 2>/dev/null | wc -l | tr -d ' ')
  mod=$(find "$d" -maxdepth 5 -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f1)
  [ -z "$mod" ] && mod="0"

  echo -e "$d\t$count\t$py\t$js\t$shc\t$docker\t$compose\t$manifest\t$pkg\t$req\t$gitd\t$mod" >> "$SCORE"
done

safe_find_files \
  | grep -Ev '/(postgres_data|open_webui_data|node_modules|__pycache__|\.venv|venv)/' \
  | xargs -r sha256sum 2>/dev/null \
  | sort \
  | awk '
    {
      h=$1
      $1=""
      sub(/^ /,"")
      a[h]=a[h] "\n" $0
      c[h]++
    }
    END {
      for (h in c) {
        if (c[h] > 1) {
          print "HASH " h " COUNT " c[h]
          print a[h]
          print ""
        }
      }
    }
  ' > "$DUP_HASH"

safe_find_files \
  | awk -F/ '{print $NF "\t" $0}' \
  | sort \
  | awk -F'\t' '
    {
      n=$1
      p=$2
      a[n]=a[n] "\n" p
      c[n]++
    }
    END {
      for (n in c) {
        if (c[n] > 1) {
          print "NAME " n " COUNT " c[n]
          print a[n]
          print ""
        }
      }
    }
  ' > "$DUP_NAME"

{
echo "# Taiji File Convergence Probe"
echo
echo "timestamp: $TS"
echo "base: $BASE"
echo

echo "## 1. Top Level Inventory"
find . -maxdepth 1 -mindepth 1 -printf '%M %10s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort
echo

echo "## 2. Subsystem Score TSV"
cat "$SCORE"
echo

echo "## 3. Candidate Core Subsystems"
for d in core Wuchang_Unified_Core Wuchang_Odoo_Core Taiji_Odoo Taiji_Claw_Container edge CloudRun_Auto_Target jules_cloud_deployment cloud_proxy_update services scripts contexts prompts docs reports; do
  echo
  echo "### $d"
  if [ -d "$d" ]; then
    echo "exists=true"
    echo "files=$(find "$d" -maxdepth 5 -type f 2>/dev/null | wc -l | tr -d ' ')"
    echo "dirs=$(find "$d" -maxdepth 5 -type d 2>/dev/null | wc -l | tr -d ' ')"
    echo "recent_files:"
    find "$d" -maxdepth 5 -type f -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort -r | head -n 15
  else
    echo "exists=false"
  fi
done
echo

echo "## 4. Compose / Dockerfiles"
find . -maxdepth 6 -type f \( -name "Dockerfile" -o -name "docker-compose.yml" -o -name "docker-compose.yaml" -o -name "compose.yml" -o -name "compose.yaml" \) 2>/dev/null | sort
echo

echo "## 5. Python Entry Candidates"
find . -maxdepth 6 -type f \( -name "main.py" -o -name "app.py" -o -name "server.py" -o -name "*api*.py" -o -name "*worker*.py" -o -name "*core*.py" \) 2>/dev/null | grep -Ev '/(postgres_data|open_webui_data|node_modules|__pycache__|\.venv|venv)/' | sort
echo

echo "## 6. Node Entry Candidates"
find . -maxdepth 6 -type f \( -name "package.json" -o -name "index.js" -o -name "server.js" -o -name "app.js" -o -name "*worker*.js" \) 2>/dev/null | grep -Ev '/(postgres_data|open_webui_data|node_modules|__pycache__|\.venv|venv)/' | sort
echo

echo "## 7. Odoo Candidates"
find . -maxdepth 8 -type f \( -name "__manifest__.py" -o -name "__openerp__.py" -o -path "*/models/*.py" -o -path "*/security/ir.model.access.csv" \) 2>/dev/null | grep -Ev '/postgres_data/' | sort | head -n 300
echo

echo "## 8. Requirements / Lock Files"
find . -maxdepth 6 -type f \( -name "requirements.txt" -o -name "pyproject.toml" -o -name "package-lock.json" -o -name "yarn.lock" -o -name "pnpm-lock.yaml" \) 2>/dev/null | grep -Ev '/(node_modules|\.venv|venv|postgres_data|open_webui_data)/' | sort
echo

echo "## 9. Largest Files"
safe_find_files | grep -Ev '/(postgres_data|open_webui_data|node_modules|__pycache__|\.venv|venv)/' | xargs -r du -h 2>/dev/null | sort -hr | head -n 80
echo

echo "## 10. Largest Directories"
du -h --max-depth=2 . 2>/dev/null | sort -hr | head -n 80
echo

echo "## 11. Duplicate Hash Groups"
head -n 300 "$DUP_HASH"
echo

echo "## 12. Duplicate Basename Groups"
head -n 300 "$DUP_NAME"
echo

echo "## 13. Sensitive Filename Index Only"
find keys security config taiji_env admin -maxdepth 4 -type f 2>/dev/null | sed 's#^\./##' | sort
echo

echo "## 14. Runtime Ports"
ss -lntp 2>/dev/null | grep -E ':3000|:6379|:8080|:11434|:8000|:9004|:9090|:50051|:8069|:5432' || true
echo

echo "## 15. Git Repositories"
find . -maxdepth 5 -type d -name ".git" 2>/dev/null | sort
echo

echo "## 16. Preliminary Convergence Recommendation"
echo "KEEP_MAIN_AI_LAYER=open-webui + ollama + contexts/ai_metric"
echo "EVALUATE_ODOO_LAYER=Wuchang_Odoo_Core vs Taiji_Odoo"
echo "EVALUATE_CORE_LAYER=Wuchang_Unified_Core vs core"
echo "QUARANTINE_UNTIL_REVIEW=Taiji_Claw_Container when /host_root mount is present"
echo "DEFER_CLOUD_LAYER=CloudRun_Auto_Target + jules_cloud_deployment until local MVP stable"
echo "DO_NOT_EXPORT=keys security config taiji_env admin .env secrets credentials"
} > "$OUT" 2>&1

cat > "$JSON" <<EOFJSON
{
  "timestamp": "$TS",
  "report": "$OUT",
  "duplicate_hashes": "$DUP_HASH",
  "duplicate_basenames": "$DUP_NAME",
  "subsystem_score": "$SCORE",
  "mode": "read_only_metadata_and_safe_text",
  "secret_policy": "do_not_read_secret_values"
}
EOFJSON

echo "$OUT"
echo "$JSON"
echo "$DUP_HASH"
echo "$DUP_NAME"
echo "$SCORE"
