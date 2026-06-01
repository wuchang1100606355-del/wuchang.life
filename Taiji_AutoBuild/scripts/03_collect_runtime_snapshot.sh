#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT_DIR/Taiji_Governance/baseline"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="$OUT_DIR/runtime_snapshot_$STAMP.txt"

mkdir -p "$OUT_DIR"

{
  printf 'Taiji runtime snapshot\n'
  printf 'created_at_utc=%s\n' "$STAMP"
  printf 'mode=read_only_no_secret_output\n'
  printf '\n[paths]\n'
  find "$ROOT_DIR" -maxdepth 3 -type d -printf '%P\n' | sort

  printf '\n[governance_files_sha256]\n'
  find "$ROOT_DIR/Taiji_Governance" "$ROOT_DIR/Taiji_AutoBuild" "$ROOT_DIR/Taiji_Vector_Runtime_Lite" \
    -maxdepth 6 -type f -print0 2>/dev/null | sort -z | xargs -0r sha256sum

  printf '\n[docker_ps]\n'
  if command -v docker >/dev/null 2>&1; then
    docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
  else
    printf 'docker=missing\n'
  fi

  printf '\n[listening_ports]\n'
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp || true
  else
    printf 'ss=missing\n'
  fi

  printf '\n[ip_route]\n'
  if command -v ip >/dev/null 2>&1; then
    ip route || true
  else
    printf 'ip=missing\n'
  fi

  printf '\n[tailscale]\n'
  if command -v tailscale >/dev/null 2>&1; then
    tailscale status || true
  else
    printf 'tailscale=missing\n'
  fi

  printf '\n[credential_file_names_only]\n'
  find "$ROOT_DIR" -maxdepth 5 -type f \
    \( -iname '*credential*' -o -iname '*service*account*.json' -o -iname '*oauth*' -o -iname '*client_secret*' -o -path '*/keys/*.json' \) \
    -printf '%P\n' | sort || true
} > "$OUT_FILE"

printf 'snapshot_written=%s\n' "$OUT_FILE"
printf 'secret_contents_printed=false\n'
