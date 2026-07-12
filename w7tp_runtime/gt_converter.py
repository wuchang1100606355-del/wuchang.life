"""Deterministic, fail-closed W7TP-GTF L1 generative transfer."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


PROTOCOL = "W7TP-GTF"
PROTOCOL_VERSION = "1.0.0"
RECIPE_TYPE = "repeat_block"
MIN_REDUCTION_RATIO = 16
MAX_PACKET_BYTES = 1024 * 1024
MAX_BLOCK_BYTES = 64 * 1024
MAX_REPEAT_COUNT = 10_000_000
MAX_OUTPUT_BYTES = 1024 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_RE = re.compile(r"^(?:[0-9a-fA-F]{2})+$")


class ConverterHold(ValueError):
    """Raised when a packet or operation must fail closed."""


class NotGenerativelyReducible(ConverterHold):
    """Raised when an input cannot be represented by a supported recipe."""


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _packet_hash_input(packet: dict[str, Any]) -> dict[str, Any]:
    clone = json.loads(_canonical_bytes(packet))
    clone["packet_integrity"]["canonical_sha256"] = ""
    return clone


def _set_packet_hash(packet: dict[str, Any]) -> None:
    packet["packet_integrity"]["canonical_sha256"] = _sha256_bytes(
        _canonical_bytes(_packet_hash_input(packet))
    )


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
    if repeat_count < 2:
        raise NotGenerativelyReducible("single-block embedding is forbidden")
    if period > MAX_BLOCK_BYTES:
        raise NotGenerativelyReducible("repeat block exceeds public limit")
    if repeat_count > MAX_REPEAT_COUNT or len(data) > MAX_OUTPUT_BYTES:
        raise NotGenerativelyReducible("recipe exceeds resource limits")
    return data[:period], repeat_count


def _portable_target(value: str) -> str:
    if not value or value.strip() != value or "\\" in value:
        raise ConverterHold("target path is not portable")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise ConverterHold("absolute target path is forbidden")
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise ConverterHold("target path traversal is forbidden")
    return posix.as_posix()


def _resolve_output(output_root: str | Path, relative_target: str) -> Path:
    root = Path(output_root)
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ConverterHold("output root must be an existing real directory")
    root = root.resolve(strict=True)
    target = root.joinpath(*PurePosixPath(_portable_target(relative_target)).parts)
    resolved = target.resolve(strict=False)
    if resolved == root or root not in resolved.parents:
        raise ConverterHold("output path escaped output root")
    current = root
    for part in PurePosixPath(relative_target).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ConverterHold("symlink path component is forbidden")
    if target.exists() or target.is_symlink():
        raise ConverterHold("existing output will not be overwritten")
    return target


def _validate_packet(packet: dict[str, Any], packet_size: int) -> None:
    required = {
        "protocol",
        "protocol_version",
        "run_id",
        "source",
        "reconstruction_target",
        "recipe",
        "verification",
        "packet_integrity",
        "authenticity",
    }
    if set(packet) != required:
        raise ConverterHold("packet fields are missing or unknown")
    if packet["protocol"] != PROTOCOL or packet["protocol_version"] != PROTOCOL_VERSION:
        raise ConverterHold("unsupported protocol or version")
    if packet_size <= 0 or packet_size > MAX_PACKET_BYTES:
        raise ConverterHold("packet size exceeds limit")
    if packet["authenticity"] != "UNVERIFIED":
        raise ConverterHold("unsigned packets cannot claim authenticity")

    integrity = packet["packet_integrity"]
    if not isinstance(integrity, dict) or set(integrity) != {"method", "canonicalization", "canonical_sha256"}:
        raise ConverterHold("invalid packet integrity declaration")
    if integrity["method"] != "sha256" or integrity["canonicalization"] != "JSON_SORTED_KEYS_COMPACT_UTF8_SELF_HASH_EMPTY":
        raise ConverterHold("unsupported packet integrity method")
    claimed = integrity["canonical_sha256"]
    actual = _sha256_bytes(_canonical_bytes(_packet_hash_input(packet)))
    if not SHA256_RE.fullmatch(str(claimed)) or claimed != actual:
        raise ConverterHold("canonical packet hash mismatch")

    target = packet["reconstruction_target"]
    if not isinstance(target, dict) or set(target) != {"mode", "relative_path"}:
        raise ConverterHold("invalid reconstruction target")
    if target["mode"] != "TARGET_PORTABLE":
        raise ConverterHold("unsupported reconstruction target mode")
    _portable_target(target["relative_path"])

    source = packet["source"]
    if not isinstance(source, dict) or set(source) != {"size_bytes", "sha256", "plaintext_embedded"}:
        raise ConverterHold("invalid source declaration")
    if source["plaintext_embedded"] is not False or not SHA256_RE.fullmatch(str(source["sha256"])):
        raise ConverterHold("invalid source integrity declaration")

    recipe = packet["recipe"]
    required_recipe = {"type", "block_hex", "block_size_bytes", "repeat_count", "output_size_bytes"}
    if not isinstance(recipe, dict) or set(recipe) != required_recipe:
        raise ConverterHold("invalid recipe fields")
    if recipe["type"] != RECIPE_TYPE:
        raise ConverterHold("unknown recipe type")
    block_hex = recipe["block_hex"]
    if not isinstance(block_hex, str) or not HEX_RE.fullmatch(block_hex):
        raise ConverterHold("block_hex must be non-empty even-length hexadecimal")
    block_size = len(block_hex) // 2
    repeat_count = recipe["repeat_count"]
    output_size = recipe["output_size_bytes"]
    if not isinstance(repeat_count, int) or isinstance(repeat_count, bool) or not 2 <= repeat_count <= MAX_REPEAT_COUNT:
        raise NotGenerativelyReducible("repeat count is not generatively reducible")
    if recipe["block_size_bytes"] != block_size or block_size > MAX_BLOCK_BYTES:
        raise ConverterHold("block size is invalid")
    if not isinstance(output_size, int) or isinstance(output_size, bool):
        raise ConverterHold("output size is invalid")
    estimated_size = block_size * repeat_count
    if estimated_size != output_size or estimated_size != source["size_bytes"]:
        raise ConverterHold("estimated output size mismatch")
    if estimated_size <= 0 or estimated_size > MAX_OUTPUT_BYTES:
        raise ConverterHold("estimated output exceeds limit")
    if packet_size * MIN_REDUCTION_RATIO > estimated_size:
        raise NotGenerativelyReducible("packet reduction ratio is below 16x")

    verification = packet["verification"]
    if not isinstance(verification, dict) or set(verification) != {"method", "expected_sha256"}:
        raise ConverterHold("invalid verification declaration")
    if verification["method"] != "sha256" or not SHA256_RE.fullmatch(str(verification["expected_sha256"])):
        raise ConverterHold("invalid expected SHA-256")
    if verification["expected_sha256"] != source["sha256"]:
        raise ConverterHold("source and verification hashes diverge")

def pack(
    source_path: str | Path,
    packet_path: str | Path,
    *,
    run_id: str | None = None,
    target_relative_path: str = "reconstructed.bin",
) -> dict[str, Any]:
    source = Path(source_path)
    packet_file = Path(packet_path)
    if packet_file.exists() or packet_file.is_symlink():
        raise ConverterHold("existing packet will not be overwritten")
    data = source.read_bytes()
    block, repeat_count = _minimal_repeated_block(data)
    target = _portable_target(target_relative_path)
    run = run_id or f"W7TP_GTF_{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    expected_sha256 = _sha256_bytes(data)
    packet = {
        "protocol": PROTOCOL,
        "protocol_version": PROTOCOL_VERSION,
        "run_id": run,
        "source": {"size_bytes": len(data), "sha256": expected_sha256, "plaintext_embedded": False},
        "reconstruction_target": {"mode": "TARGET_PORTABLE", "relative_path": target},
        "recipe": {
            "type": RECIPE_TYPE,
            "block_hex": block.hex(),
            "block_size_bytes": len(block),
            "repeat_count": repeat_count,
            "output_size_bytes": len(data),
        },
        "verification": {"method": "sha256", "expected_sha256": expected_sha256},
        "packet_integrity": {
            "method": "sha256",
            "canonicalization": "JSON_SORTED_KEYS_COMPACT_UTF8_SELF_HASH_EMPTY",
            "canonical_sha256": "",
        },
        "authenticity": "UNVERIFIED",
    }
    _set_packet_hash(packet)
    packet_bytes = _canonical_bytes(packet) + b"\n"
    _validate_packet(packet, len(packet_bytes))
    packet_file.parent.mkdir(parents=True, exist_ok=True)
    packet_file.write_bytes(packet_bytes)
    return packet


def load_packet(packet_path: str | Path) -> dict[str, Any]:
    packet_file = Path(packet_path)
    size = packet_file.stat().st_size
    if size <= 0 or size > MAX_PACKET_BYTES:
        raise ConverterHold("packet size exceeds limit")
    raw = packet_file.read_bytes()
    try:
        packet = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConverterHold("packet is not valid UTF-8 JSON") from exc
    if not isinstance(packet, dict):
        raise ConverterHold("packet root must be an object")
    if raw != _canonical_bytes(packet) + b"\n":
        raise ConverterHold("packet bytes are not canonical JSON")
    _validate_packet(packet, size)
    return packet


def reconstruct(packet_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    packet = load_packet(packet_path)
    recipe = packet["recipe"]
    output = _resolve_output(output_root, packet["reconstruction_target"]["relative_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    block = bytes.fromhex(recipe["block_hex"])
    expected = packet["verification"]["expected_sha256"]
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".w7tp-gtf-", suffix=".tmp", dir=output.parent, delete=False
        ) as stream:
            temporary_path = Path(stream.name)
            for _ in range(recipe["repeat_count"]):
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
        actual = _sha256_file(temporary_path)
        if actual != expected:
            raise ConverterHold("reconstructed SHA-256 mismatch")
        try:
            os.link(temporary_path, output, follow_symlinks=False)
        except FileExistsError as exc:
            raise ConverterHold("existing output will not be overwritten") from exc
        temporary_path.unlink()
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return {
        "run_id": packet["run_id"],
        "output_path": str(output),
        "actual_sha256": _sha256_file(output),
        "authenticity": "UNVERIFIED",
    }


def verify(packet_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    packet = load_packet(packet_path)
    expected = packet["verification"]["expected_sha256"]
    actual = _sha256_file(Path(output_path))
    decision = "PASS" if expected == actual else "HOLD"
    return {
        "run_id": packet["run_id"],
        "expected_sha256": expected,
        "actual_sha256": actual,
        "verifier_decision": decision,
        "integrity": "PASS" if decision == "PASS" else "HOLD",
        "authenticity": "UNVERIFIED",
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
        "integrity": result["integrity"],
        "authenticity": "UNVERIFIED",
    }
    target = Path(seal_path)
    if target.exists() or target.is_symlink():
        raise ConverterHold("existing seal will not be overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
