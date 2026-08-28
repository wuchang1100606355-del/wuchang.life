"""Pure Python candidate adapter for the observed W7G3 known/novel codec.

The compatibility coordinate is the read-only source observed at
``root@wuchang-us-free-node:/tmp/w7tp_genbench_v3.py`` with SHA-256
``d9ce00a7656926a57ecbfc1c639c0c53ac12790dba2eec2802e23dd8477d8913``.

This module deliberately contains no HTTP listener and no startup side effect.
It provides:

* an exact decoder for the observed ``W7G3`` binary format;
* a deterministic encoder for that exact format;
* a deterministic, fail-closed packet wrapper carrying lookup reference,
  lookup version, and lookup-profile hash;
* a separately named previous-base block lookup codec whose unmatched blocks
  are carried as novel residuals.

The previous-base mode uses a distinct magic, mode, and codec version.  It is a
candidate generalisation and is never presented as wire-compatible with W7G3.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import struct
from typing import Any, Mapping


SOURCE_COORDINATE = "root@wuchang-us-free-node:/tmp/w7tp_genbench_v3.py"
SOURCE_SHA256 = "d9ce00a7656926a57ecbfc1c639c0c53ac12790dba2eec2802e23dd8477d8913"

MAX_SIZE = 8 * 1024 * 1024
MAX_BLOCKS = 65_535

# Exact observed W7G3 constants.  Do not change these in compatibility mode.
W7G3_MAGIC = b"W7G3"
W7G3_HEADER = struct.Struct("!4sIIII")
W7G3_KNOWN = struct.Struct("!HB")
BLOCK_INDEX = struct.Struct("!H")
W7G3_BASE_PATTERN = b"W7TP-8D-ADI-BASE-V3|"
W7G3_TOKEN_TABLE: Mapping[int, bytes] = {
    0: b"W7TP-KNOWN-A|",
    1: b"W7TP-KNOWN-B|",
    2: b"W7TP-KNOWN-C|",
    3: b"W7TP-KNOWN-D|",
}

# Candidate previous-base format.  It is intentionally distinct from W7G3.
PREVIOUS_BASE_MAGIC = b"W7B1"
PREVIOUS_BASE_HEADER = struct.Struct("!4sIIII")
PREVIOUS_BASE_KNOWN = struct.Struct("!HH")

PACKET_SCHEMA_ID = "W7TP_ADI_KNOWN_NOVEL_PACKET_V1"
PACKET_VERSION = "1.0.0"
LOOKUP_SCHEMA_ID = "W7TP_ADI_LOOKUP_PROFILE_V1"

MODE_W7G3_EXACT = "W7G3_EXACT"
MODE_PREVIOUS_BASE = "PREVIOUS_BASE_BLOCK_LOOKUP"
W7G3_CODEC_VERSION = "W7G3-EXACT-1"
PREVIOUS_BASE_CODEC_VERSION = "W7B1-CANDIDATE-1"

W7G3_LOOKUP_REF = "w7tp://lookup/adi-known-novel-v3/public-fixture-table"
W7G3_LOOKUP_VERSION = "3.0.0"

_PACKET_KEYS = frozenset(
    {
        "schema_id",
        "packet_version",
        "codec_mode",
        "codec_version",
        "source_sha256",
        "lookup_ref",
        "lookup_version",
        "lookup_sha256",
        "payload_encoding",
        "payload_bytes",
        "payload_sha256",
        "payload_b64",
        "target_bytes",
        "target_sha256",
        "known_count",
        "novel_count",
    }
)


class KnownNovelV3Error(ValueError):
    """A stable fail-closed error for codec and contract violations."""


@dataclass(frozen=True)
class DecodeResult:
    """Verified reconstruction plus the packet-carried lookup binding."""

    state: bytes
    codec_mode: str
    codec_version: str
    known_count: int
    novel_count: int
    lookup_ref: str
    lookup_version: str
    lookup_sha256: str


def canonical_json_bytes(value: Any) -> bytes:
    """Return the sole JSON representation used for hashes and packets."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repeat_to_size(pattern: bytes, size: int) -> bytes:
    """Repeat and truncate a non-empty pattern exactly like the live source."""

    if not pattern:
        raise KnownNovelV3Error("PATTERN_EMPTY")
    count = (size + len(pattern) - 1) // len(pattern)
    return (pattern * count)[:size]


def _require_bytes(value: object, reason: str) -> bytes:
    if not isinstance(value, bytes):
        raise KnownNovelV3Error(reason)
    return value


def _require_block_geometry(size: int, block_size: int) -> int:
    if isinstance(block_size, bool) or not isinstance(block_size, int):
        raise KnownNovelV3Error("BLOCK_SIZE_INVALID")
    if size <= 0 or size > MAX_SIZE:
        raise KnownNovelV3Error("SIZE_INVALID")
    if block_size <= 0 or size % block_size != 0:
        raise KnownNovelV3Error("BLOCK_SIZE_INVALID")
    total_blocks = size // block_size
    if total_blocks > MAX_BLOCKS:
        raise KnownNovelV3Error("BLOCK_COUNT_TOO_LARGE")
    return total_blocks


def w7g3_lookup_profile() -> dict[str, object]:
    """Canonical public lookup profile required to reconstruct W7G3 known blocks."""

    return {
        "schema_id": LOOKUP_SCHEMA_ID,
        "mode": MODE_W7G3_EXACT,
        "lookup_ref": W7G3_LOOKUP_REF,
        "lookup_version": W7G3_LOOKUP_VERSION,
        "base_pattern_b64": base64.b64encode(W7G3_BASE_PATTERN).decode("ascii"),
        "tokens": [
            {
                "token_id": token_id,
                "pattern_b64": base64.b64encode(pattern).decode("ascii"),
            }
            for token_id, pattern in sorted(W7G3_TOKEN_TABLE.items())
        ],
    }


def w7g3_lookup_sha256() -> str:
    return sha256_hex(canonical_json_bytes(w7g3_lookup_profile()))


def previous_base_lookup_profile(
    previous_base: bytes,
    *,
    block_size: int,
    lookup_ref: str,
    lookup_version: str,
) -> dict[str, object]:
    """Describe a previous-base lookup without embedding the base in the packet."""

    previous_base = _require_bytes(previous_base, "PREVIOUS_BASE_INVALID")
    _validate_lookup_identity(lookup_ref, lookup_version)
    base_blocks = _require_block_geometry(len(previous_base), block_size)
    return {
        "schema_id": LOOKUP_SCHEMA_ID,
        "mode": MODE_PREVIOUS_BASE,
        "lookup_ref": lookup_ref,
        "lookup_version": lookup_version,
        "block_size": block_size,
        "base_bytes": len(previous_base),
        "base_blocks": base_blocks,
        "base_sha256": sha256_hex(previous_base),
    }


def previous_base_lookup_sha256(
    previous_base: bytes,
    *,
    block_size: int,
    lookup_ref: str,
    lookup_version: str,
) -> str:
    profile = previous_base_lookup_profile(
        previous_base,
        block_size=block_size,
        lookup_ref=lookup_ref,
        lookup_version=lookup_version,
    )
    return sha256_hex(canonical_json_bytes(profile))


def decode_w7g3(body: bytes) -> tuple[bytes, int, int]:
    """Decode the exact observed W7G3 wire format.

    Valid input reconstructs identically to the live ``reconstruct`` function.
    Stable rejection reasons intentionally mirror the observed decoder.
    """

    body = _require_bytes(body, "PACKET_INVALID")
    if len(body) < W7G3_HEADER.size:
        raise KnownNovelV3Error("PACKET_TOO_SMALL")

    magic, size, block_size, known_count, novel_count = W7G3_HEADER.unpack_from(body, 0)
    if magic != W7G3_MAGIC:
        raise KnownNovelV3Error("MAGIC_INVALID")
    if size <= 0 or size > MAX_SIZE:
        raise KnownNovelV3Error("SIZE_INVALID")
    if block_size <= 0 or size % block_size != 0:
        raise KnownNovelV3Error("BLOCK_SIZE_INVALID")

    total_blocks = size // block_size
    if total_blocks > MAX_BLOCKS:
        raise KnownNovelV3Error("BLOCK_COUNT_TOO_LARGE")
    if known_count + novel_count != total_blocks:
        raise KnownNovelV3Error("COVERAGE_COUNT_INVALID")

    state = bytearray(repeat_to_size(W7G3_BASE_PATTERN, size))
    seen: set[int] = set()
    offset = W7G3_HEADER.size

    for _ in range(known_count):
        if offset + W7G3_KNOWN.size > len(body):
            raise KnownNovelV3Error("KNOWN_RECORD_TRUNCATED")
        block, token_id = W7G3_KNOWN.unpack_from(body, offset)
        offset += W7G3_KNOWN.size
        if block >= total_blocks or block in seen:
            raise KnownNovelV3Error("KNOWN_COORDINATE_INVALID")
        if token_id not in W7G3_TOKEN_TABLE:
            raise KnownNovelV3Error("ADI_TOKEN_NOT_FOUND")
        seen.add(block)
        start = block * block_size
        state[start : start + block_size] = repeat_to_size(
            W7G3_TOKEN_TABLE[token_id], block_size
        )

    for _ in range(novel_count):
        if offset + BLOCK_INDEX.size + block_size > len(body):
            raise KnownNovelV3Error("NOVEL_RECORD_TRUNCATED")
        block = BLOCK_INDEX.unpack_from(body, offset)[0]
        offset += BLOCK_INDEX.size
        if block >= total_blocks or block in seen:
            raise KnownNovelV3Error("NOVEL_COORDINATE_INVALID")
        seen.add(block)
        payload = body[offset : offset + block_size]
        offset += block_size
        start = block * block_size
        state[start : start + block_size] = payload

    if len(seen) != total_blocks:
        raise KnownNovelV3Error("STATE_COVERAGE_INCOMPLETE")
    if offset != len(body):
        raise KnownNovelV3Error("TRAILING_BYTES")
    return bytes(state), known_count, novel_count


def encode_w7g3(target: bytes, *, block_size: int) -> tuple[bytes, int, int]:
    """Deterministically encode a target for the exact W7G3 decoder."""

    target = _require_bytes(target, "TARGET_INVALID")
    total_blocks = _require_block_geometry(len(target), block_size)
    token_blocks = {
        token_id: repeat_to_size(pattern, block_size)
        for token_id, pattern in sorted(W7G3_TOKEN_TABLE.items())
    }
    known: list[tuple[int, int]] = []
    novel: list[tuple[int, bytes]] = []
    for block in range(total_blocks):
        raw = target[block * block_size : (block + 1) * block_size]
        token_id = next(
            (
                candidate
                for candidate, candidate_block in token_blocks.items()
                if candidate_block == raw
            ),
            None,
        )
        if token_id is None:
            novel.append((block, raw))
        else:
            known.append((block, token_id))

    body = bytearray(
        W7G3_HEADER.pack(
            W7G3_MAGIC,
            len(target),
            block_size,
            len(known),
            len(novel),
        )
    )
    for block, token_id in known:
        body.extend(W7G3_KNOWN.pack(block, token_id))
    for block, raw in novel:
        body.extend(BLOCK_INDEX.pack(block))
        body.extend(raw)

    wire = bytes(body)
    rebuilt, known_count, novel_count = decode_w7g3(wire)
    if rebuilt != target:
        raise KnownNovelV3Error("ENCODER_SELF_VERIFY_FAILED")
    return wire, known_count, novel_count


def decode_previous_base_wire(
    body: bytes,
    *,
    previous_base: bytes,
) -> tuple[bytes, int, int]:
    """Decode the distinct W7B1 previous-base block lookup format."""

    body = _require_bytes(body, "PACKET_INVALID")
    previous_base = _require_bytes(previous_base, "PREVIOUS_BASE_INVALID")
    if len(body) < PREVIOUS_BASE_HEADER.size:
        raise KnownNovelV3Error("PACKET_TOO_SMALL")
    magic, size, block_size, known_count, novel_count = PREVIOUS_BASE_HEADER.unpack_from(
        body, 0
    )
    if magic != PREVIOUS_BASE_MAGIC:
        raise KnownNovelV3Error("MAGIC_INVALID")
    total_blocks = _require_block_geometry(size, block_size)
    base_blocks = _require_block_geometry(len(previous_base), block_size)
    if known_count + novel_count != total_blocks:
        raise KnownNovelV3Error("COVERAGE_COUNT_INVALID")

    state = bytearray(size)
    seen: set[int] = set()
    offset = PREVIOUS_BASE_HEADER.size
    for _ in range(known_count):
        if offset + PREVIOUS_BASE_KNOWN.size > len(body):
            raise KnownNovelV3Error("KNOWN_RECORD_TRUNCATED")
        target_block, base_block = PREVIOUS_BASE_KNOWN.unpack_from(body, offset)
        offset += PREVIOUS_BASE_KNOWN.size
        if target_block >= total_blocks or target_block in seen:
            raise KnownNovelV3Error("KNOWN_COORDINATE_INVALID")
        if base_block >= base_blocks:
            raise KnownNovelV3Error("BASE_COORDINATE_INVALID")
        seen.add(target_block)
        target_start = target_block * block_size
        base_start = base_block * block_size
        state[target_start : target_start + block_size] = previous_base[
            base_start : base_start + block_size
        ]

    for _ in range(novel_count):
        if offset + BLOCK_INDEX.size + block_size > len(body):
            raise KnownNovelV3Error("NOVEL_RECORD_TRUNCATED")
        target_block = BLOCK_INDEX.unpack_from(body, offset)[0]
        offset += BLOCK_INDEX.size
        if target_block >= total_blocks or target_block in seen:
            raise KnownNovelV3Error("NOVEL_COORDINATE_INVALID")
        seen.add(target_block)
        state_start = target_block * block_size
        state[state_start : state_start + block_size] = body[
            offset : offset + block_size
        ]
        offset += block_size

    if len(seen) != total_blocks:
        raise KnownNovelV3Error("STATE_COVERAGE_INCOMPLETE")
    if offset != len(body):
        raise KnownNovelV3Error("TRAILING_BYTES")
    return bytes(state), known_count, novel_count


def encode_previous_base_wire(
    target: bytes,
    *,
    previous_base: bytes,
    block_size: int,
) -> tuple[bytes, int, int]:
    """Encode exact base-block references and raw novel blocks deterministically."""

    target = _require_bytes(target, "TARGET_INVALID")
    previous_base = _require_bytes(previous_base, "PREVIOUS_BASE_INVALID")
    total_blocks = _require_block_geometry(len(target), block_size)
    base_blocks = _require_block_geometry(len(previous_base), block_size)

    # Repeated base blocks resolve to the lowest coordinate, making the wire
    # result independent of hash-map implementation details.
    first_base_coordinate: dict[bytes, int] = {}
    for base_block in range(base_blocks):
        start = base_block * block_size
        raw = previous_base[start : start + block_size]
        first_base_coordinate.setdefault(raw, base_block)

    known: list[tuple[int, int]] = []
    novel: list[tuple[int, bytes]] = []
    for target_block in range(total_blocks):
        start = target_block * block_size
        raw = target[start : start + block_size]
        base_block = first_base_coordinate.get(raw)
        if base_block is None:
            novel.append((target_block, raw))
        else:
            known.append((target_block, base_block))

    body = bytearray(
        PREVIOUS_BASE_HEADER.pack(
            PREVIOUS_BASE_MAGIC,
            len(target),
            block_size,
            len(known),
            len(novel),
        )
    )
    for target_block, base_block in known:
        body.extend(PREVIOUS_BASE_KNOWN.pack(target_block, base_block))
    for target_block, raw in novel:
        body.extend(BLOCK_INDEX.pack(target_block))
        body.extend(raw)

    wire = bytes(body)
    rebuilt, known_count, novel_count = decode_previous_base_wire(
        wire, previous_base=previous_base
    )
    if rebuilt != target:
        raise KnownNovelV3Error("ENCODER_SELF_VERIFY_FAILED")
    return wire, known_count, novel_count


def _validate_lookup_identity(lookup_ref: object, lookup_version: object) -> None:
    if not isinstance(lookup_ref, str) or not lookup_ref.strip():
        raise KnownNovelV3Error("LOOKUP_REF_INVALID")
    if not isinstance(lookup_version, str) or not lookup_version.strip():
        raise KnownNovelV3Error("LOOKUP_VERSION_INVALID")


def _build_packet(
    *,
    codec_mode: str,
    codec_version: str,
    lookup_ref: str,
    lookup_version: str,
    lookup_sha256: str,
    wire: bytes,
    target: bytes,
    known_count: int,
    novel_count: int,
) -> bytes:
    _validate_lookup_identity(lookup_ref, lookup_version)
    packet = {
        "schema_id": PACKET_SCHEMA_ID,
        "packet_version": PACKET_VERSION,
        "codec_mode": codec_mode,
        "codec_version": codec_version,
        "source_sha256": SOURCE_SHA256,
        "lookup_ref": lookup_ref,
        "lookup_version": lookup_version,
        "lookup_sha256": lookup_sha256,
        "payload_encoding": "base64",
        "payload_bytes": len(wire),
        "payload_sha256": sha256_hex(wire),
        "payload_b64": base64.b64encode(wire).decode("ascii"),
        "target_bytes": len(target),
        "target_sha256": sha256_hex(target),
        "known_count": known_count,
        "novel_count": novel_count,
    }
    return canonical_json_bytes(packet)


def encode_w7g3_packet(target: bytes, *, block_size: int) -> bytes:
    """Wrap an exact W7G3 wire body with its immutable lookup contract."""

    wire, known_count, novel_count = encode_w7g3(target, block_size=block_size)
    return _build_packet(
        codec_mode=MODE_W7G3_EXACT,
        codec_version=W7G3_CODEC_VERSION,
        lookup_ref=W7G3_LOOKUP_REF,
        lookup_version=W7G3_LOOKUP_VERSION,
        lookup_sha256=w7g3_lookup_sha256(),
        wire=wire,
        target=target,
        known_count=known_count,
        novel_count=novel_count,
    )


def encode_previous_base_packet(
    target: bytes,
    *,
    previous_base: bytes,
    block_size: int,
    lookup_ref: str,
    lookup_version: str,
) -> bytes:
    """Wrap W7B1 with a hash binding to the referenced previous base."""

    wire, known_count, novel_count = encode_previous_base_wire(
        target,
        previous_base=previous_base,
        block_size=block_size,
    )
    lookup_hash = previous_base_lookup_sha256(
        previous_base,
        block_size=block_size,
        lookup_ref=lookup_ref,
        lookup_version=lookup_version,
    )
    return _build_packet(
        codec_mode=MODE_PREVIOUS_BASE,
        codec_version=PREVIOUS_BASE_CODEC_VERSION,
        lookup_ref=lookup_ref,
        lookup_version=lookup_version,
        lookup_sha256=lookup_hash,
        wire=wire,
        target=target,
        known_count=known_count,
        novel_count=novel_count,
    )


def _parse_packet(packet_bytes: bytes) -> dict[str, object]:
    packet_bytes = _require_bytes(packet_bytes, "PACKET_INVALID")
    try:
        packet = json.loads(packet_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KnownNovelV3Error("PACKET_JSON_INVALID") from exc
    if not isinstance(packet, dict) or set(packet) != _PACKET_KEYS:
        raise KnownNovelV3Error("PACKET_SHAPE_INVALID")
    if canonical_json_bytes(packet) != packet_bytes:
        raise KnownNovelV3Error("PACKET_NOT_CANONICAL")
    if packet.get("schema_id") != PACKET_SCHEMA_ID:
        raise KnownNovelV3Error("PACKET_SCHEMA_INVALID")
    if packet.get("packet_version") != PACKET_VERSION:
        raise KnownNovelV3Error("PACKET_VERSION_INVALID")
    if packet.get("source_sha256") != SOURCE_SHA256:
        raise KnownNovelV3Error("SOURCE_BINDING_INVALID")
    _validate_lookup_identity(packet.get("lookup_ref"), packet.get("lookup_version"))
    for key in ("payload_bytes", "target_bytes", "known_count", "novel_count"):
        value = packet.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise KnownNovelV3Error("PACKET_NUMERIC_FIELD_INVALID")
    for key in ("lookup_sha256", "payload_sha256", "target_sha256"):
        value = packet.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise KnownNovelV3Error("PACKET_HASH_FIELD_INVALID")
    if packet.get("payload_encoding") != "base64":
        raise KnownNovelV3Error("PAYLOAD_ENCODING_INVALID")
    return packet


def _packet_wire(packet: Mapping[str, object]) -> bytes:
    payload_b64 = packet.get("payload_b64")
    if not isinstance(payload_b64, str):
        raise KnownNovelV3Error("PAYLOAD_INVALID")
    try:
        wire = base64.b64decode(payload_b64.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise KnownNovelV3Error("PAYLOAD_INVALID") from exc
    if packet.get("payload_bytes") != len(wire):
        raise KnownNovelV3Error("PAYLOAD_SIZE_INVALID")
    if packet.get("payload_sha256") != sha256_hex(wire):
        raise KnownNovelV3Error("PAYLOAD_HASH_INVALID")
    return wire


def decode_packet(
    packet_bytes: bytes,
    *,
    previous_base: bytes | None = None,
) -> DecodeResult:
    """Verify the packet contract and reconstruct its exact target.

    W7G3 uses the pinned public fixture lookup.  Previous-base packets require
    the caller to resolve ``lookup_ref`` to bytes and provide those bytes here;
    the packet-carried profile hash then verifies that resolution before use.
    """

    packet = _parse_packet(packet_bytes)
    wire = _packet_wire(packet)
    codec_mode = packet["codec_mode"]

    if codec_mode == MODE_W7G3_EXACT:
        if packet.get("codec_version") != W7G3_CODEC_VERSION:
            raise KnownNovelV3Error("CODEC_VERSION_INVALID")
        if (
            packet.get("lookup_ref") != W7G3_LOOKUP_REF
            or packet.get("lookup_version") != W7G3_LOOKUP_VERSION
            or packet.get("lookup_sha256") != w7g3_lookup_sha256()
        ):
            raise KnownNovelV3Error("LOOKUP_BINDING_INVALID")
        state, known_count, novel_count = decode_w7g3(wire)
    elif codec_mode == MODE_PREVIOUS_BASE:
        if packet.get("codec_version") != PREVIOUS_BASE_CODEC_VERSION:
            raise KnownNovelV3Error("CODEC_VERSION_INVALID")
        if previous_base is None:
            raise KnownNovelV3Error("PREVIOUS_BASE_REQUIRED")
        if len(wire) < PREVIOUS_BASE_HEADER.size:
            raise KnownNovelV3Error("PACKET_TOO_SMALL")
        _, _, block_size, _, _ = PREVIOUS_BASE_HEADER.unpack_from(wire, 0)
        expected_lookup_hash = previous_base_lookup_sha256(
            previous_base,
            block_size=block_size,
            lookup_ref=packet["lookup_ref"],  # validated as str by _parse_packet
            lookup_version=packet["lookup_version"],
        )
        if packet.get("lookup_sha256") != expected_lookup_hash:
            raise KnownNovelV3Error("LOOKUP_BINDING_INVALID")
        state, known_count, novel_count = decode_previous_base_wire(
            wire, previous_base=previous_base
        )
    else:
        raise KnownNovelV3Error("CODEC_MODE_INVALID")

    if (
        packet.get("known_count") != known_count
        or packet.get("novel_count") != novel_count
    ):
        raise KnownNovelV3Error("COUNT_BINDING_INVALID")
    if packet.get("target_bytes") != len(state):
        raise KnownNovelV3Error("TARGET_SIZE_INVALID")
    if packet.get("target_sha256") != sha256_hex(state):
        raise KnownNovelV3Error("TARGET_HASH_INVALID")

    return DecodeResult(
        state=state,
        codec_mode=codec_mode,
        codec_version=packet["codec_version"],
        known_count=known_count,
        novel_count=novel_count,
        lookup_ref=packet["lookup_ref"],
        lookup_version=packet["lookup_version"],
        lookup_sha256=packet["lookup_sha256"],
    )


__all__ = [
    "DecodeResult",
    "KnownNovelV3Error",
    "MAX_SIZE",
    "MODE_PREVIOUS_BASE",
    "MODE_W7G3_EXACT",
    "PACKET_SCHEMA_ID",
    "PREVIOUS_BASE_CODEC_VERSION",
    "SOURCE_COORDINATE",
    "SOURCE_SHA256",
    "W7G3_CODEC_VERSION",
    "W7G3_LOOKUP_REF",
    "W7G3_LOOKUP_VERSION",
    "W7G3_TOKEN_TABLE",
    "canonical_json_bytes",
    "decode_packet",
    "decode_previous_base_wire",
    "decode_w7g3",
    "encode_previous_base_packet",
    "encode_previous_base_wire",
    "encode_w7g3",
    "encode_w7g3_packet",
    "previous_base_lookup_profile",
    "previous_base_lookup_sha256",
    "repeat_to_size",
    "sha256_hex",
    "w7g3_lookup_profile",
    "w7g3_lookup_sha256",
]
