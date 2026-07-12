"""Product-grade, offline, fail-closed W7TP-GTF generative transfer core."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable, Literal, Protocol

PROTOCOL = "W7TP-GTF"
PROTOCOL_VERSION = "1.0.0"
RECIPE_TYPE = "repeat_block"
MIN_REDUCTION_RATIO = 16
MAX_PACKET_BYTES = 1024 * 1024
MAX_BLOCK_BYTES = 64 * 1024
MAX_REPEAT_COUNT = 10_000_000
MAX_OUTPUT_BYTES = 1024 * 1024 * 1024
MAX_JSON_DEPTH = 16
CHUNK_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_RE = re.compile(r"^(?:[0-9a-fA-F]{2})+$")
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

Decision = Literal["PASS", "HOLD", "BLOCK", "ERROR"]


@dataclass(frozen=True)
class ConverterPolicy:
    max_packet_bytes: int = MAX_PACKET_BYTES
    max_block_bytes: int = MAX_BLOCK_BYTES
    max_output_bytes: int = MAX_OUTPUT_BYTES
    minimum_reduction_ratio: float = 16.0
    overwrite: bool = False
    network_allowed: bool = False


@dataclass(frozen=True)
class OperationResult:
    state: Decision
    run_id: str
    packet_path: Path | None = None
    output_path: Path | None = None
    packet_sha256: str | None = None
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    integrity: str = "UNVERIFIED"
    authenticity: str = "UNVERIFIED"
    reason_code: str | None = None


class SignatureVerifier(Protocol):
    """Verifies public signature metadata without accepting or retaining raw keys."""

    def verify(self, packet: dict[str, Any]) -> bool: ...


class ConverterFailure(ValueError):
    state: Decision = "HOLD"

    def __init__(self, reason_code: str, message: str = "") -> None:
        super().__init__(message or reason_code)
        self.reason_code = reason_code


class ConverterHold(ConverterFailure):
    pass


class ConverterBlock(ConverterHold):
    state: Decision = "BLOCK"


class NotGenerativelyReducible(ConverterHold):
    pass


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConverterHold("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _json_depth(value: Any, depth: int = 0) -> int:
    if depth > MAX_JSON_DEPTH:
        raise ConverterHold("JSON_DEPTH_EXCEEDED")
    if isinstance(value, dict):
        for item in value.values():
            _json_depth(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _json_depth(item, depth + 1)
    return depth


def _packet_hash_input(packet: dict[str, Any]) -> dict[str, Any]:
    clone = json.loads(_canonical_bytes(packet), object_pairs_hook=_no_duplicate_pairs)
    clone["packet_integrity"]["canonical_sha256"] = ""
    return clone


def _set_packet_hash(packet: dict[str, Any]) -> None:
    packet["packet_integrity"]["canonical_sha256"] = _sha256_bytes(_canonical_bytes(_packet_hash_input(packet)))


def _minimal_repeated_block(data: bytes, policy: ConverterPolicy) -> tuple[bytes, int]:
    if not data:
        raise NotGenerativelyReducible("EMPTY_INPUT")
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
        raise NotGenerativelyReducible("NOT_GENERATIVELY_REDUCIBLE")
    count = len(data) // period
    if count < 2:
        raise NotGenerativelyReducible("SINGLE_BLOCK_FORBIDDEN")
    if period > policy.max_block_bytes:
        raise NotGenerativelyReducible("BLOCK_LIMIT_EXCEEDED")
    if count > MAX_REPEAT_COUNT or len(data) > policy.max_output_bytes:
        raise NotGenerativelyReducible("RESOURCE_LIMIT_EXCEEDED")
    return data[:period], count


def _portable_target(value: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value or "\\" in value:
        raise ConverterHold("TARGET_NOT_PORTABLE")
    posix, windows = PurePosixPath(value), PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise ConverterBlock("ABSOLUTE_PATH_FORBIDDEN")
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise ConverterBlock("PATH_TRAVERSAL_FORBIDDEN")
    for part in posix.parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED or part.endswith((" ", ".")):
            raise ConverterBlock("WINDOWS_RESERVED_NAME")
    return posix.as_posix()


def _resolve_output(output_root: str | Path, relative_target: str) -> Path:
    root = Path(output_root)
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ConverterBlock("INVALID_OUTPUT_ROOT")
    root = root.resolve(strict=True)
    target = root.joinpath(*PurePosixPath(_portable_target(relative_target)).parts)
    resolved = target.resolve(strict=False)
    if resolved == root or root not in resolved.parents:
        raise ConverterBlock("OUTPUT_ROOT_ESCAPE", "output path escaped output root")
    current = root
    for part in PurePosixPath(relative_target).parts[:-1]:
        current /= part
        if current.is_symlink():
                raise ConverterBlock("SYMLINK_ESCAPE", "symlink path component is forbidden")
    if target.exists() or target.is_symlink():
        raise ConverterBlock("OUTPUT_EXISTS", "existing output will not be overwritten")
    if target.parent.exists():
        folded = target.name.casefold()
        if any(entry.name.casefold() == folded for entry in target.parent.iterdir()):
            raise ConverterBlock("CASE_INSENSITIVE_COLLISION")
    return target


def _validate_packet(packet: dict[str, Any], packet_size: int, policy: ConverterPolicy | None = None) -> None:
    policy = policy or ConverterPolicy()
    required = {"protocol", "protocol_version", "run_id", "source", "reconstruction_target", "recipe", "limits", "verification", "packet_integrity", "authenticity"}
    legacy_required = required - {"limits"}
    if set(packet) not in (required, legacy_required):
        raise ConverterHold("UNKNOWN_OR_MISSING_FIELDS")
    if packet["protocol"] != PROTOCOL or packet["protocol_version"] != PROTOCOL_VERSION:
        raise ConverterHold("UNSUPPORTED_PROTOCOL")
    if not isinstance(packet["run_id"], str) or not SAFE_RUN_ID_RE.fullmatch(packet["run_id"]):
        raise ConverterHold("UNSAFE_RUN_ID")
    if packet_size <= 0 or packet_size > policy.max_packet_bytes:
        raise ConverterHold("PACKET_SIZE_LIMIT")
    if packet["authenticity"] != "UNVERIFIED":
        raise ConverterBlock("UNTRUSTED_AUTHENTICITY_CLAIM")
    integrity = packet["packet_integrity"]
    if not isinstance(integrity, dict) or set(integrity) != {"method", "canonicalization", "canonical_sha256"}:
        raise ConverterHold("INVALID_PACKET_INTEGRITY")
    if integrity["method"] != "sha256" or integrity["canonicalization"] != "JSON_SORTED_KEYS_COMPACT_UTF8_SELF_HASH_EMPTY":
        raise ConverterHold("UNSUPPORTED_PACKET_INTEGRITY")
    claimed = integrity["canonical_sha256"]
    if not isinstance(claimed, str) or not SHA256_RE.fullmatch(claimed) or claimed != _sha256_bytes(_canonical_bytes(_packet_hash_input(packet))):
        raise ConverterBlock("PACKET_HASH_MISMATCH", "canonical packet hash mismatch")
    target = packet["reconstruction_target"]
    if not isinstance(target, dict) or set(target) != {"mode", "relative_path", "target_os"} and set(target) != {"mode", "relative_path"}:
        raise ConverterHold("INVALID_TARGET")
    if target["mode"] != "TARGET_PORTABLE":
        raise ConverterHold("UNSUPPORTED_TARGET_MODE")
    if "target_os" in target and target["target_os"] not in {"portable", "windows", "linux"}:
        raise ConverterHold("INVALID_TARGET_OS")
    _portable_target(target["relative_path"])
    source = packet["source"]
    if not isinstance(source, dict) or set(source) != {"size_bytes", "sha256", "plaintext_embedded"}:
        raise ConverterHold("INVALID_SOURCE")
    if source["plaintext_embedded"] is not False or not isinstance(source["size_bytes"], int) or isinstance(source["size_bytes"], bool) or not isinstance(source["sha256"], str) or not SHA256_RE.fullmatch(source["sha256"]):
        raise ConverterHold("INVALID_SOURCE")
    recipe = packet["recipe"]
    if not isinstance(recipe, dict) or set(recipe) != {"type", "block_hex", "block_size_bytes", "repeat_count", "output_size_bytes"}:
        raise ConverterHold("INVALID_RECIPE_FIELDS")
    if recipe["type"] != RECIPE_TYPE:
        raise ConverterHold("UNKNOWN_RECIPE_TYPE")
    block_hex = recipe["block_hex"]
    if not isinstance(block_hex, str) or not HEX_RE.fullmatch(block_hex):
        raise ConverterHold("INVALID_BLOCK_HEX")
    block_size, count, size = len(block_hex) // 2, recipe["repeat_count"], recipe["output_size_bytes"]
    if not isinstance(count, int) or isinstance(count, bool) or not 2 <= count <= MAX_REPEAT_COUNT:
        raise NotGenerativelyReducible("INVALID_REPEAT_COUNT")
    if not isinstance(recipe["block_size_bytes"], int) or isinstance(recipe["block_size_bytes"], bool) or recipe["block_size_bytes"] != block_size or block_size > policy.max_block_bytes:
        raise ConverterHold("INVALID_BLOCK_SIZE")
    if not isinstance(size, int) or isinstance(size, bool):
        raise ConverterHold("INVALID_OUTPUT_SIZE")
    estimated = block_size * count
    if estimated != size or estimated != source["size_bytes"]:
        raise ConverterHold("OUTPUT_SIZE_MISMATCH")
    if estimated <= 0 or estimated > policy.max_output_bytes:
        raise ConverterBlock("OUTPUT_SIZE_LIMIT")
    if packet_size * policy.minimum_reduction_ratio > estimated:
        raise NotGenerativelyReducible("REDUCTION_RATIO_TOO_LOW")
    verification = packet["verification"]
    if not isinstance(verification, dict) or set(verification) != {"method", "expected_sha256"} or verification.get("method") != "sha256":
        raise ConverterHold("INVALID_VERIFICATION")
    expected = verification.get("expected_sha256")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected) or expected != source["sha256"]:
        raise ConverterBlock("EXPECTED_HASH_MISMATCH")


def _load_packet(packet_path: Path, policy: ConverterPolicy) -> tuple[dict[str, Any], bytes]:
    size = packet_path.stat().st_size
    if size <= 0 or size > policy.max_packet_bytes:
        raise ConverterHold("PACKET_SIZE_LIMIT")
    raw = packet_path.read_bytes()
    try:
        packet = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_pairs)
    except ConverterFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConverterHold("INVALID_JSON") from exc
    if not isinstance(packet, dict):
        raise ConverterHold("INVALID_JSON_ROOT")
    _json_depth(packet)
    if raw != _canonical_bytes(packet) + b"\n":
        raise ConverterHold("NONCANONICAL_JSON", "packet bytes are not canonical JSON")
    _validate_packet(packet, size, policy)
    return packet, raw


class GTConverter:
    def __init__(self, policy: ConverterPolicy | None = None, signature_verifier: SignatureVerifier | None = None) -> None:
        self.policy = policy or ConverterPolicy()
        if self.policy.overwrite or self.policy.network_allowed:
            raise ConverterBlock("UNSAFE_POLICY")
        self.signature_verifier = signature_verifier

    def pack(self, source: Path, packet: Path, *, run_id: str | None = None, target_relative_path: str = "reconstructed.bin", target_os: str = "portable") -> OperationResult:
        if packet.exists() or packet.is_symlink():
            raise ConverterBlock("PACKET_EXISTS")
        data = source.read_bytes()
        block, count = _minimal_repeated_block(data, self.policy)
        target = _portable_target(target_relative_path)
        run = run_id or f"W7TP_GTF_{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        if not SAFE_RUN_ID_RE.fullmatch(run):
            raise ConverterHold("UNSAFE_RUN_ID")
        digest = _sha256_bytes(data)
        document = {
            "protocol": PROTOCOL, "protocol_version": PROTOCOL_VERSION, "run_id": run,
            "source": {"size_bytes": len(data), "sha256": digest, "plaintext_embedded": False},
            "reconstruction_target": {"mode": "TARGET_PORTABLE", "relative_path": target, "target_os": target_os},
            "recipe": {"type": RECIPE_TYPE, "block_hex": block.hex(), "block_size_bytes": len(block), "repeat_count": count, "output_size_bytes": len(data)},
            "limits": {"max_output_bytes": self.policy.max_output_bytes, "minimum_reduction_ratio": self.policy.minimum_reduction_ratio},
            "verification": {"method": "sha256", "expected_sha256": digest},
            "packet_integrity": {"method": "sha256", "canonicalization": "JSON_SORTED_KEYS_COMPACT_UTF8_SELF_HASH_EMPTY", "canonical_sha256": ""},
            "authenticity": "UNVERIFIED",
        }
        _set_packet_hash(document)
        raw = _canonical_bytes(document) + b"\n"
        _validate_packet(document, len(raw), self.policy)
        packet.parent.mkdir(parents=True, exist_ok=True)
        try:
            with packet.open("xb") as stream:
                stream.write(raw)
        except FileExistsError as exc:
            raise ConverterBlock("PACKET_EXISTS") from exc
        return OperationResult("PASS", run, packet_path=packet, packet_sha256=_sha256_bytes(raw), expected_sha256=digest, integrity="PASS")

    def inspect(self, packet: Path) -> OperationResult:
        document, raw = _load_packet(packet, self.policy)
        return OperationResult("PASS", document["run_id"], packet_path=packet, packet_sha256=_sha256_bytes(raw), expected_sha256=document["verification"]["expected_sha256"], integrity="PASS")

    def reconstruct(self, packet: Path, output_root: Path) -> OperationResult:
        document, raw = _load_packet(packet, self.policy)
        output = _resolve_output(output_root, document["reconstruction_target"]["relative_path"])
        output.parent.mkdir(parents=True, exist_ok=True)
        lock = output.with_name(f".{output.name}.w7tp.lock")
        temporary: Path | None = None
        lock_fd: int | None = None
        try:
            try:
                lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(lock_fd, document["run_id"].encode("ascii"))
                os.fsync(lock_fd)
            except FileExistsError as exc:
                raise ConverterBlock("OUTPUT_LOCKED") from exc
            block = bytes.fromhex(document["recipe"]["block_hex"])
            remaining = document["recipe"]["repeat_count"]
            per_chunk = max(1, CHUNK_BYTES // len(block))
            with tempfile.NamedTemporaryFile("xb", prefix=".w7tp-gtf-", suffix=".tmp", dir=output.parent, delete=False) as stream:
                temporary = Path(stream.name)
                while remaining:
                    count = min(remaining, per_chunk)
                    stream.write(block * count)
                    remaining -= count
                stream.flush(); os.fsync(stream.fileno())
            actual = _sha256_file(temporary)
            expected = document["verification"]["expected_sha256"]
            if actual != expected:
                raise ConverterBlock("RECONSTRUCTED_HASH_MISMATCH", "reconstructed SHA-256 mismatch")
            try:
                os.link(temporary, output, follow_symlinks=False)
            except FileExistsError as exc:
                raise ConverterBlock("OUTPUT_EXISTS", "existing output will not be overwritten") from exc
            temporary.unlink(); temporary = None
            return OperationResult("PASS", document["run_id"], packet, output, _sha256_bytes(raw), expected, _sha256_file(output), "PASS", "UNVERIFIED")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if lock_fd is not None:
                os.close(lock_fd)
                lock.unlink(missing_ok=True)

    def verify(self, packet: Path, reconstructed: Path) -> OperationResult:
        document, raw = _load_packet(packet, self.policy)
        expected, actual = document["verification"]["expected_sha256"], _sha256_file(reconstructed)
        state: Decision = "PASS" if expected == actual else "HOLD"
        return OperationResult(state, document["run_id"], packet, reconstructed, _sha256_bytes(raw), expected, actual, "PASS" if state == "PASS" else "HOLD", "UNVERIFIED", None if state == "PASS" else "OUTPUT_HASH_MISMATCH")

    def seal(self, result: OperationResult, report: Path) -> Path:
        if report.exists() or report.is_symlink():
            raise ConverterBlock("REPORT_EXISTS")
        source_size = packet_size = 0
        target_os = "portable"
        if result.packet_path:
            document, raw = _load_packet(result.packet_path, self.policy)
            source_size, packet_size = document["source"]["size_bytes"], len(raw)
            target_os = document["reconstruction_target"].get("target_os", "portable")
        record = {
            "actual_sha256": result.actual_sha256, "authenticity": result.authenticity,
            "decision": result.state, "expected_sha256": result.expected_sha256,
            "integrity": result.integrity, "packet_bytes": packet_size,
            "packet_sha256": result.packet_sha256, "protocol": PROTOCOL,
            "protocol_version": PROTOCOL_VERSION, "reason_code": result.reason_code,
            "reduction_ratio": round(source_size / packet_size, 6) if packet_size else None,
            "run_id": result.run_id, "source_bytes": source_size, "state": result.state,
            "target_os": target_os,
        }
        report.parent.mkdir(parents=True, exist_ok=True)
        try:
            with report.open("xb") as stream:
                stream.write(_canonical_bytes(record) + b"\n")
        except FileExistsError as exc:
            raise ConverterBlock("REPORT_EXISTS") from exc
        return report


_DEFAULT = GTConverter()


def pack(source_path: str | Path, packet_path: str | Path, *, run_id: str | None = None, target_relative_path: str = "reconstructed.bin") -> dict[str, Any]:
    _DEFAULT.pack(Path(source_path), Path(packet_path), run_id=run_id, target_relative_path=target_relative_path)
    return load_packet(packet_path)


def load_packet(packet_path: str | Path) -> dict[str, Any]:
    return _load_packet(Path(packet_path), _DEFAULT.policy)[0]


def reconstruct(packet_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    result = _DEFAULT.reconstruct(Path(packet_path), Path(output_root))
    return {"run_id": result.run_id, "output_path": str(result.output_path), "actual_sha256": result.actual_sha256, "authenticity": result.authenticity}


def verify(packet_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    result = _DEFAULT.verify(Path(packet_path), Path(output_path))
    return {"run_id": result.run_id, "expected_sha256": result.expected_sha256, "actual_sha256": result.actual_sha256, "verifier_decision": result.state, "integrity": result.integrity, "authenticity": result.authenticity}


def seal(packet_path: str | Path, output_path: str | Path, seal_path: str | Path, verification: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = verification or verify(packet_path, output_path)
    result = OperationResult(raw["verifier_decision"], raw["run_id"], Path(packet_path), Path(output_path), _sha256_file(Path(packet_path)), raw["expected_sha256"], raw["actual_sha256"], raw["integrity"], "UNVERIFIED")
    _DEFAULT.seal(result, Path(seal_path))
    return json.loads(Path(seal_path).read_text(encoding="utf-8"))
