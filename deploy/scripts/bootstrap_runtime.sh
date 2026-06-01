#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${TAIJI_ENV_FILE:-$ROOT_DIR/deploy/env/runtime.env.example}"

"$ROOT_DIR/deploy/scripts/preflight_check.sh"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

mkdir -p "${TAIJI_RUNTIME_STATE_DIR:?}" "${TAIJI_REPLAY_DIR:?}" "${TAIJI_DEADBOX_DIR:?}" "${TAIJI_CACHE_DIR:?}" "$(dirname "${TAIJI_AUDIT_PATH:?}")"

printf '%s\n' "bootstrap ok"
