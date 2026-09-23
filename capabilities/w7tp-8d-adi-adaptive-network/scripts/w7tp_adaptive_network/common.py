from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


OBSERVER_ID = "w7tp-8d-adi-adaptive-network/0.1.0-candidate.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_command(argv: Sequence[str], timeout: float = 8.0) -> dict[str, Any]:
    """Run one bounded command without a shell and preserve result classification."""

    started = time.monotonic()
    try:
        proc = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "executed": True,
            "argv": list(argv),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "status": "PASS" if proc.returncode == 0 else "FAIL",
        }
    except FileNotFoundError:
        return {
            "executed": False,
            "argv": list(argv),
            "returncode": None,
            "stdout": "",
            "stderr": "command_not_found",
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "status": "LOCALIZED_UNKNOWN",
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "executed": True,
            "argv": list(argv),
            "returncode": None,
            "stdout": stdout,
            "stderr": stderr or "timeout",
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "status": "TIMEOUT",
        }


def parse_json_result(result: dict[str, Any], fallback: Any) -> Any:
    if result.get("returncode") != 0 or not result.get("stdout", "").strip():
        return fallback
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError:
        return fallback


def evidence_envelope(
    *,
    schema_id: str,
    timestamp: str,
    source_node: str,
    confidence: str = "MEDIUM",
    authority_scope: str = "CANDIDATE_EVIDENCE_ONLY",
) -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "timestamp": timestamp,
        "observer": OBSERVER_ID,
        "source_node": source_node,
        "evidence_class": "D4_EVIDENCE",
        "confidence": confidence,
        "authority_scope": authority_scope,
    }

