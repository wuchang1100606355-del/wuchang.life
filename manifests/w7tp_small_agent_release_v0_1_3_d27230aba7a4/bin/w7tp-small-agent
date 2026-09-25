#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic installed entry point for the candidate W7TP small agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence, cast

sys.dont_write_bytecode = True


CLI_SCHEMA_VERSION = "w7tp-small-agent-cli/v0.1.1"
RECEIVE_SCHEMA_VERSION = "w7tp-small-agent-receive-candidate/v0.1"
AGENT_NAME = "w7tp-small-agent"
SOURCE_MODES = frozenset({"TOTAL_FIELD_PULL", "LLM_PUSH"})
_RECEIVE_KEYS = frozenset(
    {
        "schema_version",
        "source_mode",
        "request",
        "previous_state",
        "observation_domains",
    }
)
_SENSITIVE_KEYS = frozenset(
    {"api_key", "credential", "password", "private_key", "secret", "token"}
)
_KEY_BLOCK_PREFIX = b"-----" + b"BEGIN "
_KEY_BLOCK_SUFFIX = b"-----"
_RAW_SECRET_MARKERS = (
    _KEY_BLOCK_PREFIX + b"PRIVATE KEY" + _KEY_BLOCK_SUFFIX,
    _KEY_BLOCK_PREFIX + b"OPENSSH PRIVATE KEY" + _KEY_BLOCK_SUFFIX,
    _KEY_BLOCK_PREFIX + b"RSA PRIVATE KEY" + _KEY_BLOCK_SUFFIX,
)


class CLIError(ValueError):
    """Stable command failure without governance or secret payload disclosure."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        """Store one stable code and structural path."""

        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate members."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CLIError("HOLD_DUPLICATE_JSON_MEMBER", f"$.{key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> NoReturn:
    """Reject non-finite JSON tokens before any gateway call."""

    raise CLIError("HOLD_NON_FINITE_JSON_NUMBER", f"$.{token}")


def _read_json(path: Path, reason_code: str = "HOLD_JSON_READ_FAILED") -> dict[str, Any]:
    """Read one strict UTF-8 JSON object from an exact path."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except CLIError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CLIError(reason_code, str(path)) from exc
    if not isinstance(value, dict):
        raise CLIError("HOLD_JSON_OBJECT_REQUIRED", str(path))
    return value


def _canonical_json(value: Any) -> str:
    """Render one deterministic JSON line with finite-number enforcement."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise CLIError("HOLD_JSON_SERIALIZATION_FAILED") from exc


def _canonical_sha256(value: Any) -> str:
    """Hash one canonical UTF-8 JSON representation."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _resolve_release_root() -> Path:
    """Resolve a repository or installed release solely from this entry file."""

    entry = Path(__file__).resolve()
    candidates: list[Path] = []
    if entry.parent.name == "bin":
        candidates.append(entry.parent.parent)
    if entry.parent.name == "tools" and entry.parent.parent.name == "lib":
        candidates.append(entry.parents[2])
    if entry.parent.name == "tools":
        candidates.append(entry.parent.parent)
    for candidate in candidates:
        if (candidate / "release_manifest.json").is_file():
            return candidate
    raise CLIError("HOLD_RELEASE_ROOT_UNRESOLVED", str(entry))


def _bootstrap_release_imports(release_root: Path) -> None:
    """Prepend the installed lib directory without relying on PYTHONPATH."""

    library = release_root / "lib"
    source_root = release_root
    import_root = library if library.is_dir() else source_root
    import_text = str(import_root)
    if import_text not in sys.path:
        sys.path.insert(0, import_text)


def _manifest_identity(release_root: Path) -> dict[str, str]:
    """Read and validate the fixed release identity used by every command."""

    manifest = _read_json(
        release_root / "release_manifest.json",
        "HOLD_RELEASE_MANIFEST_INVALID",
    )
    identity = manifest.get("release_identity")
    if not isinstance(identity, dict):
        raise CLIError("HOLD_RELEASE_IDENTITY_MISSING", "$.release_identity")
    values = {
        "release_version": manifest.get("release_version"),
        "release_sha256": manifest.get("release_sha256"),
        "policy_sha256": identity.get("policy_sha256"),
    }
    for key, value in values.items():
        if not isinstance(value, str) or not value:
            raise CLIError("HOLD_RELEASE_IDENTITY_INVALID", f"$.{key}")
    if values["release_version"] != identity.get("release_version"):
        raise CLIError("HOLD_RELEASE_VERSION_MISMATCH", "$.release_identity")
    return cast(dict[str, str], values)


def _capability_path(release_root: Path) -> Path:
    """Return the fixed release capability manifest path."""

    return release_root / "capability_manifest_template.json"


def _vector_path(release_root: Path) -> Path:
    """Return the installed fixed-vector path for either supported layout."""

    installed = release_root / "fixtures" / "w7tp_small_agent_deployment_vectors.json"
    if installed.is_file():
        return installed
    legacy = release_root / "tests" / "fixtures" / "w7tp_small_agent_deployment_vectors.json"
    if legacy.is_file():
        return legacy
    raise CLIError("HOLD_FIXED_VECTOR_MISSING", "$.fixtures")


def _contains_sensitive_key(value: Any) -> bool:
    """Detect secret-bearing keys without printing their values."""

    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).casefold() in _SENSITIVE_KEYS:
                return True
            if _contains_sensitive_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _raw_secret_scan(release_root: Path) -> str:
    """Scan only manifest-declared release files for high-signal key material."""

    files_document = _read_json(
        release_root / "files_sha256.json",
        "HOLD_RELEASE_FILES_MANIFEST_INVALID",
    )
    files = files_document.get("files")
    if not isinstance(files, dict):
        raise CLIError("HOLD_RELEASE_FILES_MANIFEST_INVALID", "$.files")
    root = release_root.resolve()
    for relative in sorted(files):
        if not isinstance(relative, str):
            raise CLIError("HOLD_RELEASE_FILES_MANIFEST_INVALID", "$.files")
        target = (release_root / relative).resolve()
        if root != target and root not in target.parents:
            raise CLIError("HOLD_RELEASE_FILE_PATH_UNSAFE", relative)
        try:
            content = target.read_bytes()
        except OSError as exc:
            raise CLIError("HOLD_RELEASE_FILE_READ_FAILED", relative) from exc
        if any(marker in content for marker in _RAW_SECRET_MARKERS):
            raise CLIError("HOLD_RAW_SECRET_DETECTED", relative)
    return "PASS"


def _emit_state(state: str, evidence: Mapping[str, Any]) -> None:
    """Print the locked two-line state and canonical evidence contract."""

    print(f"STATE={state}")
    print(_canonical_json(dict(evidence)))


def _command_version(release_root: Path) -> int:
    """Print the five immutable release identity fields exactly once."""

    identity = _manifest_identity(release_root)
    print(f"agent_name={AGENT_NAME}")
    print(f"agent_version={identity['release_version']}")
    print(f"release_sha256={identity['release_sha256']}")
    print(f"policy_sha256={identity['policy_sha256']}")
    print(f"schema_version={CLI_SCHEMA_VERSION}")
    return 0


def _command_health(release_root: Path) -> int:
    """Run embedded release health checks without recursively invoking the CLI."""

    _bootstrap_release_imports(release_root)
    from tools.w7tp_small_agent_healthcheck import run_embedded_healthcheck

    evidence = run_embedded_healthcheck(
        release_root,
        vector_path=_vector_path(release_root),
    )
    if evidence.get("status") == "PASS":
        _emit_state("PASS_W7TP_SMALL_AGENT_HEALTH", evidence)
        return 0
    reason = evidence.get("reason_code")
    state = reason if isinstance(reason, str) and reason else "HOLD_W7TP_SMALL_AGENT_HEALTH"
    _emit_state(state, evidence)
    return 2


def _command_self_test(release_root: Path) -> int:
    """Run the installed deterministic vector and emit closed check evidence."""

    _bootstrap_release_imports(release_root)
    from tools.w7tp_small_agent_healthcheck import run_embedded_healthcheck
    from tools.w7tp_small_agent_service_runner import load_json_file, run_self_test

    health = run_embedded_healthcheck(release_root, vector_path=_vector_path(release_root))
    if health.get("status") != "PASS":
        reason = health.get("reason_code")
        state = reason if isinstance(reason, str) and reason else "HOLD_W7TP_SMALL_AGENT_HEALTH"
        _emit_state(state, health)
        return 2
    service = run_self_test(load_json_file(_vector_path(release_root)))
    gates = service.get("commit_gates")
    if not isinstance(gates, dict):
        raise CLIError("HOLD_SELF_TEST_GATE_EVIDENCE_MISSING")
    checks = {
        "d1_projection": service.get("d1_projection"),
        "candidate_replay": service.get("candidate_replay"),
        "total_field_pull": (
            "PASS" if service.get("total_field_pull") == "TEST_ONLY_PASS" else "HOLD"
        ),
        "llm_push": "PASS" if service.get("llm_push") == "TEST_ONLY_PASS" else "HOLD",
        "common_receive_path": service.get("common_receive_path"),
        "allow_only_commit": service.get("allow_only_commit"),
        "hold_preserves_previous": gates.get("HOLD"),
        "block_preserves_previous": gates.get("BLOCK"),
        "quarantine_preserves_previous": gates.get("QUARANTINE"),
        "persona_governance_separation": service.get("persona_governance_separation"),
        "llm_direct_commit": service.get("llm_direct_commit"),
        "raw_secret_scan": _raw_secret_scan(release_root),
    }
    expected = {
        key: ("BLOCKED" if key == "llm_direct_commit" else "PASS")
        for key in checks
    }
    status = "PASS" if checks == expected else "HOLD"
    identity = _manifest_identity(release_root)
    evidence = {
        "release_version": identity["release_version"],
        "release_sha256": identity["release_sha256"],
        "policy_sha256": identity["policy_sha256"],
        "status": status,
        "checks": checks,
        "candidate_hash": service.get("candidate_hash"),
        "d1_projection_hash": service.get("d1_projection_hash"),
        "common_receive_path_marker": service.get("common_receive_path_marker"),
        "gateway_fixture_mode": "TEST_ONLY",
    }
    if status == "PASS":
        _emit_state("PASS_W7TP_SMALL_AGENT_SELF_TEST", evidence)
        return 0
    _emit_state("HOLD_W7TP_SMALL_AGENT_SELF_TEST", evidence)
    return 2


def _command_capabilities(release_root: Path) -> int:
    """Print the release capability manifest only when it contains no secrets."""

    capability = _read_json(
        _capability_path(release_root),
        "HOLD_CAPABILITY_MANIFEST_INVALID",
    )
    if _contains_sensitive_key(capability):
        raise CLIError("HOLD_CAPABILITY_SECRET_FIELD_BLOCKED")
    print(_canonical_json(capability))
    return 0


def _command_receive_candidate(release_root: Path, request_path: Path) -> int:
    """Validate one closed JSON envelope and route it through the existing gateway."""

    envelope = _read_json(request_path, "HOLD_CANDIDATE_JSON_INVALID")
    if frozenset(envelope) != _RECEIVE_KEYS:
        raise CLIError("HOLD_RECEIVE_CANDIDATE_MEMBER_MISMATCH")
    if envelope.get("schema_version") != RECEIVE_SCHEMA_VERSION:
        raise CLIError("HOLD_RECEIVE_CANDIDATE_SCHEMA_VERSION")
    source_mode = envelope.get("source_mode")
    if source_mode not in SOURCE_MODES:
        raise CLIError("HOLD_RECEIVE_CANDIDATE_SOURCE_MODE")
    request = envelope.get("request")
    previous = envelope.get("previous_state")
    domains = envelope.get("observation_domains")
    if not all(isinstance(value, dict) for value in (request, previous, domains)):
        raise CLIError("HOLD_RECEIVE_CANDIDATE_OBJECT_REQUIRED")
    _bootstrap_release_imports(release_root)
    from tools.total_field_candidate_gateway import llm_push, total_field_pull
    from tools.w7tp_small_agent_service_runner import canonical_sha256

    try:
        if source_mode == "TOTAL_FIELD_PULL":
            result = total_field_pull(
                cast(dict[str, Any], request),
                previous_state=cast(dict[str, Any], previous),
                observation_domains=cast(dict[str, Any], domains),
            )
        else:
            result = llm_push(
                cast(dict[str, Any], request),
                previous_state=cast(dict[str, Any], previous),
                observation_domains=cast(dict[str, Any], domains),
            )
    except Exception as exc:
        reason = getattr(exc, "reason_code", "HOLD_TOTAL_FIELD_GATEWAY_REJECTED")
        raise CLIError(str(reason), "$.request") from exc
    decision = result.get("final_decision")
    commit_applied = result.get("commit_applied")
    previous_result = result.get("previous")
    proposed_result = result.get("proposed")
    committed_result = result.get("committed")
    if decision not in {"ALLOW", "HOLD", "BLOCK", "QUARANTINE"}:
        raise CLIError("HOLD_GATEWAY_DECISION_INVALID")
    if not isinstance(commit_applied, bool):
        raise CLIError("HOLD_GATEWAY_COMMIT_FLAG_INVALID")
    if any(value is None for value in (previous_result, proposed_result, committed_result)):
        raise CLIError("HOLD_GATEWAY_STATE_EVIDENCE_MISSING")
    if decision != "ALLOW" and commit_applied:
        raise CLIError("HOLD_ALLOW_ONLY_COMMIT_GUARD_FAILED")
    allow_commit = decision == "ALLOW" and commit_applied is True
    expected_committed = proposed_result if allow_commit else previous_result
    if committed_result != expected_committed:
        raise CLIError("HOLD_ALLOW_ONLY_COMMIT_GUARD_FAILED")
    evidence = {
        "schema_version": "w7tp-small-agent-adjudication-evidence/v0.1",
        "status": "PASS",
        "source_mode": source_mode,
        "final_decision": decision,
        "commit_applied": commit_applied,
        "previous_hash": canonical_sha256(previous_result),
        "proposed_hash": canonical_sha256(proposed_result),
        "committed_hash": canonical_sha256(committed_result),
        "tfid": result.get("tfid"),
        "total_field_hash": result.get("total_field_hash"),
        "decision_reason_codes": result.get("decision_reason_codes"),
    }
    print(_canonical_json(evidence))
    return 0


def _command_service_run(release_root: Path) -> int:
    """Enter an IDLE_READY foreground loop and exit cleanly on a stop signal."""

    _bootstrap_release_imports(release_root)
    from tools.w7tp_small_agent_healthcheck import run_embedded_healthcheck

    health = run_embedded_healthcheck(release_root, vector_path=_vector_path(release_root))
    if health.get("status") != "PASS":
        reason = health.get("reason_code")
        state = reason if isinstance(reason, str) and reason else "HOLD_W7TP_SMALL_AGENT_HEALTH"
        _emit_state(state, health)
        return 2
    _read_json(release_root / "install_manifest.json", "HOLD_SERVICE_CONFIG_INVALID")
    _read_json(_capability_path(release_root), "HOLD_CAPABILITY_MANIFEST_INVALID")
    stopped = threading.Event()

    def request_stop(_signum: int, _frame: Any) -> None:
        """Mark the foreground service for a normal deterministic exit."""

        stopped.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    print("STATE=IDLE_READY", flush=True)
    stopped.wait()
    print("STATE=STOPPED", flush=True)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Create the complete installed command parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("version")
    subparsers.add_parser("health")
    subparsers.add_parser("self-test")
    subparsers.add_parser("capabilities")
    receive = subparsers.add_parser("receive-candidate")
    receive.add_argument("json_path", type=Path)
    subparsers.add_parser("service-run")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch exactly one local command and emit stable HOLD evidence on failure."""

    arguments = _parser().parse_args(argv)
    try:
        release_root = _resolve_release_root()
        if arguments.command == "version":
            return _command_version(release_root)
        if arguments.command == "health":
            return _command_health(release_root)
        if arguments.command == "self-test":
            return _command_self_test(release_root)
        if arguments.command == "capabilities":
            return _command_capabilities(release_root)
        if arguments.command == "receive-candidate":
            return _command_receive_candidate(release_root, arguments.json_path)
        return _command_service_run(release_root)
    except CLIError as exc:
        _emit_state(
            exc.reason_code,
            {
                "schema_version": CLI_SCHEMA_VERSION,
                "status": "HOLD",
                "reason_code": exc.reason_code,
                "path": exc.path,
            },
        )
        return 2
    except Exception as exc:
        reason = getattr(exc, "reason_code", "HOLD_W7TP_SMALL_AGENT_COMMAND_FAILED")
        _emit_state(
            str(reason),
            {
                "schema_version": CLI_SCHEMA_VERSION,
                "status": "HOLD",
                "reason_code": str(reason),
            },
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "AGENT_NAME",
    "CLIError",
    "CLI_SCHEMA_VERSION",
    "RECEIVE_SCHEMA_VERSION",
    "main",
)
