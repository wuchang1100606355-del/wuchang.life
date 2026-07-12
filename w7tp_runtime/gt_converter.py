"""Deterministic L1 generative-transfer converter for reducible byte patterns."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any


PROTOCOL = "W7TP-GTF"
PROTOCOL_VERSION = "1.0.0"
MAX_BLOCK_BYTES = 1024 * 1024


class NotGenerativelyReducible(ValueError):
    """Raised when an input cannot be represented by a supported recipe."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _minimal_repeated_block(data: bytes) -> tuple[bytes, int]:
    if not data:
        raise NotGenerativelyReducible("empty input has no repeat recipe")

    prefix = [0] * len(data)
    matched = 0
    for index in range(1, len(data)):
        while matched and data[index] != data[matched]:
            matched = prefix[matched - 1]
        if data[index] == data[matched]:
            matched += 1
            prefix[index] = matched

    period = len(data) - prefix[-1]
    if period == len(data) or len(data) % period:
        raise NotGenerativelyReducible("input is not a repeated byte block")
    repeat_count = len(data) // period
    if repeat_count < 2 or period > MAX_BLOCK_BYTES:
        raise NotGenerativelyReducible("repeat recipe is outside public limits")
    return data[:period], repeat_count


def pack(source_path: str | Path, packet_path: str | Path, *, run_id: str | None = None) -> dict[str, Any]:
    source = Path(source_path)
    packet_file = Path(packet_path)
    data = source.read_bytes()
    block, repeat_count = _minimal_repeated_block(data)
    run = run_id or f"W7TP_GTF_{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    expected_sha256 = _sha256_bytes(data)
    packet = {
        "protocol": PROTOCOL,
        "protocol_version": PROTOCOL_VERSION,
        "run_id": run,
        "source": {
            "size_bytes": len(data),
            "sha256": expected_sha256,
            "plaintext_embedded": False,
        },
        "reconstruction_target": {"mode": "TARGET_PORTABLE"},
        "recipe": {
            "type": "repeat_block",
            "block_hex": block.hex(),
            "block_size_bytes": len(block),
            "repeat_count": repeat_count,
            "output_size_bytes": len(data),
        },
        "verification": {
            "method": "sha256",
            "expected_sha256": expected_sha256,
        },
    }
    packet_file.parent.mkdir(parents=True, exist_ok=True)
    packet_file.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return packet


def load_packet(packet_path: str | Path) -> dict[str, Any]:
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    if packet.get("protocol") != PROTOCOL or packet.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("unsupported W7TP-GTF protocol")
    recipe = packet.get("recipe")
    if not isinstance(recipe, dict) or recipe.get("type") != "repeat_block":
        raise ValueError("unsupported reconstruction recipe")
    return packet


def reconstruct(packet_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    packet = load_packet(packet_path)
    recipe = packet["recipe"]
    block = bytes.fromhex(recipe.get("block_hex", ""))
    repeat_count = recipe.get("repeat_count")
    output_size = recipe.get("output_size_bytes")
    if not block or len(block) > MAX_BLOCK_BYTES:
        raise ValueError("invalid repeat block")
    if not isinstance(repeat_count, int) or repeat_count < 2:
        raise ValueError("invalid repeat count")
    if not isinstance(output_size, int) or output_size != len(block) * repeat_count:
        raise ValueError("recipe output size mismatch")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        for _ in range(repeat_count):
            stream.write(block)
    return {
        "run_id": packet["run_id"],
        "output_path": str(output),
        "actual_sha256": _sha256_file(output),
    }


def verify(packet_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    packet = load_packet(packet_path)
    expected = packet.get("verification", {}).get("expected_sha256", "")
    actual = _sha256_file(Path(output_path))
    decision = "PASS" if expected and expected == actual else "HOLD"
    return {
        "run_id": packet["run_id"],
        "expected_sha256": expected,
        "actual_sha256": actual,
        "verifier_decision": decision,
    }


def seal(
    packet_path: str | Path,
    output_path: str | Path,
    seal_path: str | Path,
    verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet_file = Path(packet_path)
    result = verification or verify(packet_file, output_path)
    record = {
        "state": "PASS" if result["verifier_decision"] == "PASS" else "HOLD",
        "run_id": result["run_id"],
        "packet_path": str(packet_file),
        "output_path": str(Path(output_path)),
        "packet_sha256": _sha256_file(packet_file),
        "expected_sha256": result["expected_sha256"],
        "actual_sha256": result["actual_sha256"],
        "verifier_decision": result["verifier_decision"],
    }
    target = Path(seal_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record
