#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 40
SCRIPT_REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)" || {
    printf '%s\n' 'STATE=HOLD' 'REASON=D8_WORKTREE_ROOT_UNRESOLVED'
    exit 20
}
CURRENT_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    printf '%s\n' 'STATE=HOLD' 'REASON=D8_CURRENT_WORKTREE_UNRESOLVED'
    exit 20
}
SCRIPT_REPO_ROOT="$(realpath -e -- "$SCRIPT_REPO_ROOT")" || exit 40
CURRENT_REPO_ROOT="$(realpath -e -- "$CURRENT_REPO_ROOT")" || exit 40
COMMON_GIT_DIR="$(git -C "$CURRENT_REPO_ROOT" rev-parse --git-common-dir 2>/dev/null)" || exit 40
if [[ "$COMMON_GIT_DIR" != /* ]]; then
    COMMON_GIT_DIR="$CURRENT_REPO_ROOT/$COMMON_GIT_DIR"
fi
COMMON_GIT_DIR="$(realpath -e -- "$COMMON_GIT_DIR")" || exit 40
SOURCE_REPO_ROOT="$(dirname -- "$COMMON_GIT_DIR")"

if [[ "$SCRIPT_REPO_ROOT" != "$CURRENT_REPO_ROOT" ]]; then
    printf '%s\n' 'STATE=HOLD' 'REASON=D8_WORKTREE_ROOT_MISMATCH'
    exit 20
fi
if [[ "$CURRENT_REPO_ROOT" == "$SOURCE_REPO_ROOT" || "$CURRENT_REPO_ROOT" == "$SOURCE_REPO_ROOT"/* ]]; then
    printf '%s\n' 'STATE=HOLD' 'REASON=D8_SOURCE_REPO_OUTPUT_FORBIDDEN'
    exit 20
fi

cd "$CURRENT_REPO_ROOT" || exit 40
python3 tools/d8_codex_mandatory_workflow.py "$@"
exit $?
