#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub

TS="$(date +%Y%m%d_%H%M%S)"
OUT="git_space/reports/git_central_status_${TS}.txt"

{
  echo "=== git status short ==="
  git status --short

  echo
  echo "=== staged files ==="
  git diff --cached --name-only

  echo
  echo "=== untracked top-level summary ==="
  git status --short | awk '{print $2}' | cut -d/ -f1 | sort | uniq -c | sort -nr | head -80

  echo
  echo "=== recent commits ==="
  git log --oneline -20 || true
} | tee "$OUT"

echo "REPORT=$OUT"
