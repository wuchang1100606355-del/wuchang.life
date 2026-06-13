#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail() {
  echo "STATE=HOLD_VERIFY"
  echo "reason=$1"
  exit 1
}

[ -f AGENTS.md ] || fail "AGENTS.md missing"

required_terms=(
  "Direct Shortest Path Rule"
  "Generative Transfer Priority Gate"
  "Main Chain Rule"
  "Redteam Rule"
  "No Detour Rule"
  "W3_GENERATIVE_TRANSFER_DEPLOY"
  "STATE=HOLD_MAIN_CHAIN_DEVIATION"
)

for term in "${required_terms[@]}"; do
  grep -Fq "$term" AGENTS.md || fail "missing required term: $term"
done

if grep -Eq 'sk-[A-Za-z0-9_-]{10,}|AIza[A-Za-z0-9_-]{10,}|[Bb]earer[[:space:]]+[A-Za-z0-9._~+/=-]{10,}|BEGIN PRIVATE KEY' AGENTS.md; then
  fail "raw key pattern found in AGENTS.md"
fi

if grep -Eq '身分證|身份證|電話|地址|生日|電子信箱|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' AGENTS.md; then
  fail "member PII marker found in AGENTS.md"
fi

echo "STATE=PASS_VERIFY"
