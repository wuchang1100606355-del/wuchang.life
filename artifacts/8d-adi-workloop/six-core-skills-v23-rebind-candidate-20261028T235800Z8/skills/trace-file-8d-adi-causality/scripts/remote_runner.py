#!/usr/bin/env python3
"""Run the frozen-source analyzer through one exact fixed-IP SSH coordinate."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


PROFILE_SCHEMA = "trace-file-8d-adi-fixed-ip-profile/1.0"
SAFE_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
SAFE_USER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,31}")
FORBIDDEN_KEYS = {
    "password", "passwd", "token", "secret", "private_key", "private_key_path",
    "identity_file", "command", "fallback", "hostname", "dns", "proxy", "tunnel",
}
REQUIRED_KEYS = {
    "schema_version", "node_ref", "host_ip", "ssh_user", "ssh_port",
    "remote_repo", "remote_output_dir", "connect_timeout_seconds",
}
OPTIONAL_KEYS = {
    "analysis_timeout_seconds",
}
REMOTE_BOOTSTRAP = (
    "import os,runpy,sys,tempfile;"
    "fd,p=tempfile.mkstemp(prefix='trace_8d_adi_',suffix='.py');"
    "os.write(fd,sys.stdin.buffer.read());os.close(fd);"
    "a=sys.argv[1:];sys.argv=[p]+a;"
    "x=None;"
    "\ntry:\n runpy.run_path(p,run_name='__main__')"
    "\nfinally:\n os.unlink(p)"
)


def public_result(state: str, node_ref: str, **extra: Any) -> dict[str, Any]:
    return {
        "STATE": state,
        "NODE_REF": node_ref,
        "CONNECTION_MODE": "FIXED_IP_SSH_PRIVATE_PROFILE",
        "RAW_NETWORK_COORDINATE_DISCLOSED": False,
        "FALLBACK_ATTEMPTED": False,
        "ORIGINAL_FILES_MODIFIED": False,
        "GIT_INDEX_MODIFIED": False,
        "CANONICAL_PROMOTION": False,
        "TOTAL_FIELD_DECISION": "NOT_RUN",
        **extra,
    }


def absolute_posix(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        raise ValueError(f"{field} must be an absolute POSIX path")
    pure = PurePosixPath(value)
    if ".." in pure.parts:
        raise ValueError(f"{field} must not contain parent traversal")
    return str(pure)


def validate_profile(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if resolved.stat().st_mode & 0o077:
        raise ValueError("profile permissions must not grant group or other access")
    profile = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("profile must be a JSON object")
    keys = set(profile)
    if keys & FORBIDDEN_KEYS:
        raise ValueError("profile contains a forbidden credential, command, or fallback field")
    if not REQUIRED_KEYS.issubset(keys):
        raise ValueError("profile is missing required fields")
    if keys - REQUIRED_KEYS - OPTIONAL_KEYS:
        raise ValueError("profile contains undeclared fields")
    if profile["schema_version"] != PROFILE_SCHEMA:
        raise ValueError("unsupported profile schema")
    try:
        ipaddress.ip_address(profile["host_ip"])
    except (ValueError, TypeError):
        raise ValueError("host_ip must be an IP literal") from None
    if not isinstance(profile["ssh_user"], str) or not SAFE_USER_RE.fullmatch(profile["ssh_user"]):
        raise ValueError("ssh_user is invalid")
    if not isinstance(profile["node_ref"], str) or not SAFE_REF_RE.fullmatch(profile["node_ref"]):
        raise ValueError("node_ref must be opaque and use safe characters")
    if not isinstance(profile["ssh_port"], int) or not 1 <= profile["ssh_port"] <= 65535:
        raise ValueError("ssh_port is invalid")
    if not isinstance(profile["connect_timeout_seconds"], int) or not 1 <= profile["connect_timeout_seconds"] <= 60:
        raise ValueError("connect_timeout_seconds must be between 1 and 60")
    profile["remote_repo"] = absolute_posix(profile["remote_repo"], "remote_repo")
    profile["remote_output_dir"] = absolute_posix(profile["remote_output_dir"], "remote_output_dir")
    if profile["remote_repo"] == profile["remote_output_dir"]:
        raise ValueError("remote_output_dir must not equal remote_repo")
    if "analysis_timeout_seconds" in profile:
        value = profile["analysis_timeout_seconds"]
        if not isinstance(value, int) or not 60 <= value <= 3600:
            raise ValueError("analysis_timeout_seconds must be between 60 and 3600")
    return profile


def analyzer_path() -> Path:
    return Path(__file__).with_name("causal_index.py").resolve(strict=True)


def run_remote(profile_path: Path, founder_intent: str, product_effect: str) -> int:
    try:
        profile = validate_profile(profile_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps(public_result(
            "PRECONDITION_MISSING", "node://unresolved",
            REASON=f"PRIVATE_PROFILE_INVALID:{type(exc).__name__}",
            SOURCE_ENUMERATION_COUNT=0,
        ), sort_keys=True))
        return 2

    node_ref = profile["node_ref"]
    remote_args = [
        "python3", "-c", REMOTE_BOOTSTRAP, "--repo", profile["remote_repo"],
        "--output-dir", profile["remote_output_dir"], "--node-ref", node_ref,
        "--founder-intent", founder_intent,
    ]
    if product_effect:
        remote_args.extend(["--product-effect", product_effect])
    remote_command = shlex.join(remote_args)
    ssh_command = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"ConnectTimeout={profile['connect_timeout_seconds']}",
        "-o", "ClearAllForwardings=yes",
        "-o", "ForwardAgent=no",
        "-o", "RequestTTY=no",
        "-p", str(profile["ssh_port"]),
        f"{profile['ssh_user']}@{profile['host_ip']}",
        remote_command,
    ]
    try:
        proc = subprocess.run(
            ssh_command,
            input=analyzer_path().read_bytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=profile["connect_timeout_seconds"] + profile.get("analysis_timeout_seconds", 900),
        )
    except (OSError, subprocess.TimeoutExpired):
        print(json.dumps(public_result(
            "PRECONDITION_MISSING", node_ref,
            REASON="FIXED_IP_SSH_PRECONDITION_UNAVAILABLE",
            SOURCE_ENUMERATION_COUNT=0,
        ), sort_keys=True))
        return 3
    if proc.returncode:
        print(json.dumps(public_result(
            "PRECONDITION_MISSING", node_ref,
            REASON="REMOTE_ANALYZER_DID_NOT_COMPLETE",
            SOURCE_ENUMERATION_COUNT=0,
        ), sort_keys=True))
        return 4
    try:
        last_line = next(line for line in reversed(proc.stdout.decode("utf-8", "replace").splitlines()) if line.strip())
        remote_receipt = json.loads(last_line)
    except (StopIteration, json.JSONDecodeError):
        print(json.dumps(public_result(
            "PRECONDITION_MISSING", node_ref,
            REASON="REMOTE_RECEIPT_INVALID",
            SOURCE_ENUMERATION_COUNT=1,
        ), sort_keys=True))
        return 5
    if (
        remote_receipt.get("state") != "CANDIDATE_NOT_CANONICAL"
        or remote_receipt.get("edge_contract_validation") != "CANDIDATE_CHECK_COMPLETE"
        or remote_receipt.get("git_consulted") is not False
    ):
        print(json.dumps(public_result(
            "PRECONDITION_MISSING", node_ref,
            REASON="REMOTE_RECEIPT_CONTRACT_INCOMPLETE",
            SOURCE_ENUMERATION_COUNT=remote_receipt.get("source_enumeration_count", 1),
        ), sort_keys=True))
        return 6
    print(json.dumps(public_result(
        "CANDIDATE_NOT_CANONICAL", node_ref,
        SOURCE_ENUMERATION_COUNT=remote_receipt.get("source_enumeration_count", 1),
        REMOTE_SNAPSHOT_ID=remote_receipt.get("snapshot_id"),
        REMOTE_OUTPUT_FILE_COUNT=len(remote_receipt.get("files", [])),
        CAUSAL_STATUS=remote_receipt.get("causal_status"),
        RECONSTRUCTED_CAUSAL_CHAIN_COUNT=remote_receipt.get("reconstructed_causal_chain_count", 0),
        VERIFIED_CAUSAL_CHAIN_COUNT=remote_receipt.get("verified_causal_chain_count", 0),
        SOURCE_COVERAGE_STATUS=remote_receipt.get("source_coverage_status"),
        RED_TEAM_STATE=remote_receipt.get("red_team_state"),
        EDGE_CONTRACT_VALIDATION=remote_receipt.get("edge_contract_validation"),
        NETWORK_CARRIER="ORDINARY_SSH_NOT_GENERATIVE_TRANSMISSION",
    ), sort_keys=True))
    return 0


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="trace-fixed-profile-") as tmp:
        path = Path(tmp) / "profile.json"
        path.write_text(json.dumps({
            "schema_version": PROFILE_SCHEMA,
            "node_ref": "node://self-test",
            "host_ip": "192.0.2.1",
            "ssh_user": "test_user",
            "ssh_port": 22,
            "remote_repo": "/srv/repo",
            "remote_output_dir": "/srv/repo/evidence/run",
            "connect_timeout_seconds": 5,
            "analysis_timeout_seconds": 900,
        }), encoding="utf-8")
        os.chmod(path, 0o600)
        profile = validate_profile(path)
        if profile["host_ip"] != "192.0.2.1" or profile["node_ref"] != "node://self-test":
            raise AssertionError("profile validation changed exact coordinate")
        invalid = dict(profile)
        invalid["password"] = "forbidden"
        path.write_text(json.dumps(invalid), encoding="utf-8")
        try:
            validate_profile(path)
        except ValueError:
            pass
        else:
            raise AssertionError("forbidden credential field accepted")
        bootstrap = subprocess.run(
            [sys.executable, "-c", REMOTE_BOOTSTRAP, "--self-test"],
            input=analyzer_path().read_bytes(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=30,
        )
        if bootstrap.returncode or b"SELF_TEST_COMPLETE" not in bootstrap.stdout:
            raise AssertionError("stdin analyzer bootstrap failed")
    print(json.dumps({"STATE": "SELF_TEST_COMPLETE", "network_used": False}, sort_keys=True))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--founder-intent", default="")
    parser.add_argument("--product-effect", default="")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if not args.self_test and (args.profile is None or not args.founder_intent.strip()):
        parser.error("--profile and --founder-intent are required unless --self-test is used")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return self_test() if args.self_test else run_remote(args.profile, args.founder_intent, args.product_effect)


if __name__ == "__main__":
    raise SystemExit(main())
