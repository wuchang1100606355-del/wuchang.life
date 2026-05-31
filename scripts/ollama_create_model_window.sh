#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/ollama_create_model_window.sh <base_model> <new_model_name> [window_id]

Examples:
  scripts/ollama_create_model_window.sh qwen2.5:3b xiaoj-persona-qwen25-3b AIW-persona-light
  scripts/ollama_create_model_window.sh llama3.1:8b xiaoj-engineering-llama31-8b AIW-engineering-reasoning

This script:
  1. ollama pull <base_model>
  2. creates a temporary governed Modelfile
  3. ollama create <new_model_name> -f <temp Modelfile>

It does not read secrets and does not mutate Taiji/Odoo/Google production systems.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 2 ]; then
  usage
  exit 0
fi

BASE_MODEL="$1"
NEW_MODEL="$2"
WINDOW_ID="${3:-AIW-engineering-reasoning}"

case "$BASE_MODEL" in
  *[!A-Za-z0-9._:/+-]*|'')
    echo "invalid base_model: $BASE_MODEL" >&2
    exit 2
    ;;
esac

case "$NEW_MODEL" in
  *[!A-Za-z0-9._-]*|'')
    echo "invalid new_model_name: $NEW_MODEL" >&2
    exit 2
    ;;
esac

case "$WINDOW_ID" in
  AIW-persona-light|AIW-engineering-reasoning|AIW-gateway-policy|AIW-audit-replay)
    ;;
  *)
    echo "invalid window_id: $WINDOW_ID" >&2
    exit 2
    ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/models/ollama/Modelfile.xiaoj_model_window.template"
PREFIX="$ROOT/prompts/XIAOJ_MODEL_WINDOW_GOVERNED_PREFIX.md"

if [ ! -f "$TEMPLATE" ]; then
  echo "missing template: $TEMPLATE" >&2
  exit 3
fi

if [ ! -f "$PREFIX" ]; then
  echo "missing prefix: $PREFIX" >&2
  exit 3
fi

command -v ollama >/dev/null 2>&1 || {
  echo "ollama command not found" >&2
  exit 4
}

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

sed "s|__BASE_MODEL__|$BASE_MODEL|g" "$TEMPLATE" > "$TMP"

echo "window_id=$WINDOW_ID"
echo "base_model=$BASE_MODEL"
echo "new_model=$NEW_MODEL"
echo "prefix=$PREFIX"
echo "pulling base model..."
ollama pull "$BASE_MODEL"
echo "creating governed XiaoJ model window..."
ollama create "$NEW_MODEL" -f "$TMP"
echo "done: $NEW_MODEL"
