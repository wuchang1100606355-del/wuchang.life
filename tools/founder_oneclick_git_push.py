#!/usr/bin/env python3
"""Founder-requested direct Git fast-forward delivery for one pinned branch.

This is an operational Git helper, NOT a D8 authority issuer or a replacement
for platform confirmations. It does not rewrite the index or working tree.

Usage: python3 tools/founder_oneclick_git_push.py --check
       python3 tools/founder_oneclick_git_push.py --execute
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/taiji_admin/Taiji_Hub")
NODE = os.uname().nodename
# Exact, node-bound founder delivery lanes. No arbitrary branch/remote input.
NODE_TARGETS = {
    "taiji01": (
        "codex/current-live-state-consolidation-20260915",
        "https://github.com/wuchang1100606355-del/wuchang.life.git",
    ),
    "MSI": (
        "agent/moving-v-v2-taiji8d-local-canary",
        "git@github.com:wuchang1100606355-del/wuchang.life.git",
    ),
}
if NODE not in NODE_TARGETS:
    raise RuntimeError("UNRECOGNIZED_DELIVERY_NODE")
BRANCH, ENDPOINT = NODE_TARGETS[NODE]
REF = "refs/heads/" + BRANCH
REMOTE = "origin"
HEX_OID = re.compile(r"^[0-9a-f]{40}$")


def git(*args: str, require=True):
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    p = subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=env, timeout=90, check=False)
    if require and p.returncode:
        raise RuntimeError(f"GIT_COMMAND_FAILED ({' '.join(args[:2])}, exit={p.returncode})")
    return p


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fingerprint() -> str:
    # Includes dirty changes only as a fingerprint; never stages or pushes them.
    p = subprocess.run(["git", "-C", str(ROOT), "--no-optional-locks",
                        "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if p.returncode:
        raise RuntimeError("WORKTREE_FINGERPRINT_UNAVAILABLE")
    return sha(p.stdout)


def remote_oid() -> str:
    result = git("ls-remote", "--heads", REMOTE, REF).stdout.strip()
    parts = result.split()
    if len(parts) != 2 or parts[1] != REF or not HEX_OID.fullmatch(parts[0]):
        raise RuntimeError("REMOTE_REF_NOT_EXACTLY_OBSERVED")
    return parts[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Read-only preflight")
    group.add_argument("--execute", action="store_true", help="Push after explicit Founder instruction")
    args = ap.parse_args()
    if ROOT.is_symlink() or not ROOT.is_dir() or git("rev-parse", "--show-toplevel").stdout.strip() != str(ROOT):
        raise RuntimeError("REPOSITORY_COORDINATE_MISMATCH")
    if git("symbolic-ref", "HEAD").stdout.strip() != REF:
        raise RuntimeError("WRONG_BRANCH")
    if git("remote", "get-url", REMOTE).stdout.strip() != ENDPOINT:
        raise RuntimeError("REMOTE_ENDPOINT_MISMATCH")
    if git("remote", "get-url", "--push", REMOTE).stdout.strip() != ENDPOINT:
        raise RuntimeError("PUSH_ENDPOINT_MISMATCH")
    source = git("rev-parse", "HEAD").stdout.strip()
    if not HEX_OID.fullmatch(source) or git("cat-file", "-t", source).stdout.strip() != "commit":
        raise RuntimeError("SOURCE_COMMIT_INVALID")

    before_fp = fingerprint()
    before = remote_oid()
    ff = git("merge-base", "--is-ancestor", before, source, require=False)
    if ff.returncode != 0:
        raise RuntimeError("NON_FAST_FORWARD_OR_MISSING_LOCAL_REMOTE_BASE")
    if args.execute and before != source:
        hook = Path(git("rev-parse", "--git-path", "hooks/pre-push").stdout.strip())
        if not hook.is_absolute():
            hook = ROOT / hook
        push_scope: tuple[str, ...] = ()
        if hook.exists() and os.access(hook, os.X_OK):
            # MSI's pinned legacy D8 hook is audit-only for this exact founder
            # branch+endpoint+fast-forward lane; do not change global Git config.
            known_msi_d8_hook_sha256 = "df435784373c5dd5b58a450e8e15bed31a914620818e5141ab692c3b0f7f1afb"
            if NODE != "MSI" or sha(hook.read_bytes()) != known_msi_d8_hook_sha256:
                raise RuntimeError("UNKNOWN_EXECUTABLE_PRE_PUSH_HOOK")
            push_scope = ("-c", "core.hooksPath=/dev/null")
        # An ordinary push is always non-force. It can never rewrite history.
        git(*push_scope, "push", "--porcelain", "--no-follow-tags", "--recurse-submodules=no",
            REMOTE, f"{source}:{REF}")

    after = remote_oid()
    after_fp = fingerprint()
    receipt = {
        "schema": "W7TP_FOUNDER_DIRECT_GIT_FAST_FORWARD_RECEIPT_V1",
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "EXECUTE" if args.execute else "CHECK_ONLY",
        "node": NODE,
        "branch": BRANCH,
        "expected_remote_before": before,
        "local_head": source,
        "remote_readback": after,
        "remote_exact_match": after == source,
        "worktree_fingerprint_unchanged": before_fp == after_fp,
        "msi_local_hook_policy": (
            "PINNED_LEGACY_D8_HOOK_SKIP_FOR_FOUNDER_FAST_FORWARD"
            if NODE == "MSI" else "NO_MSI_HOOK_OVERRIDE"
        ),
        "d8": "AUDIT_ONLY_NO_INDEPENDENT_GIT_VETO_IN_THIS_HELPER",
        "authority_note": "This receipt does not amend or authenticate ACTIVE_TOTAL_FIELD_AUTHORITY.json",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    if not receipt["worktree_fingerprint_unchanged"]:
        raise RuntimeError("PROTECTED_WORKTREE_STATUS_DRIFT")
    if args.execute and not receipt["remote_exact_match"]:
        raise RuntimeError("REMOTE_READBACK_NOT_TARGET")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("HOLD: " + str(exc), file=sys.stderr)
        sys.exit(2)
