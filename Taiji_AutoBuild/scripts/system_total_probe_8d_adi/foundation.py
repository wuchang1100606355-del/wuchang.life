from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_text_excerpt(path: Path, max_chars: int = 1600) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "excerpt": ""}
    text = path.read_text(encoding="utf-8", errors="replace")
    redacted_lines = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in ("password", "token", "secret", "private_key", "api_key")):
            redacted_lines.append("[REDACTED_SENSITIVE_LINE]")
        else:
            redacted_lines.append(line)
        if sum(len(item) + 1 for item in redacted_lines) >= max_chars:
            break
    return {
        "exists": True,
        "excerpt": "\n".join(redacted_lines)[:max_chars],
        "truncated": len(text) > max_chars,
    }


def run_status_check(command: list[str], timeout: float = 2.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "output_stored": False}
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output_stored": False}


def local_json_get(url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        data = json.loads(payload)
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
    safe = {
        key: data.get(key)
        for key in ("status", "service", "version", "policy_locked", "locked")
        if key in data
    }
    return {"ok": True, "json": safe}


def write_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()
