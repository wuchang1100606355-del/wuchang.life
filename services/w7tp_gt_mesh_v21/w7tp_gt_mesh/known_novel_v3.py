"""Pure thin adapter for the observed US VM ADI known/novel V3 protocol.

Source coordinate (read-only observation):
``root@wuchang-us-free-node:/tmp/w7tp_genbench_v3.py``
SHA-256: ``d9ce00a7656926a57ecbfc1c639c0c53ac12790dba2eec2802e23dd8477d8913``

Only the deterministic binary codec is carried here.  The live HTTP server and
its startup side effect are intentionally excluded.  This capability is a D6
reconstruction mechanism, not canonical or authority.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Sequence

from .core import MeshHold, require_core


V3_SOURCE_SHA256 = "d9ce00a7656926a57ecbfc1c639c0c53ac12790dba2eec2802e23dd8477d8913"
V3_CAPABILITY_REF = "capability:ADI_KNOWN_NOVEL_V3_D9CE00A7"
LOOKUP_VERSION = "ADI_KNOWN_NOVEL_V3_LOOKUP_V1"
MAGIC = b"W7G3"
HEADER = struct.Struct("!4sIIII")
KNOWN = struct.Struct("!HB")
NOVEL_INDEX = struct.Struct("!H")
MAX_SIZE = 8 * 1024 * 1024
BASE_PATTERN = b"W7TP-8D-ADI-BASE-V3|"
TOKEN_TABLE = {
    0: b"W7TP-KNOWN-A|",
    1: b"W7TP-KNOWN-B|",
    2: b"W7TP-KNOWN-C|",
    3: b"W7TP-KNOWN-D|",
}


class KnownNovelV3Error(ValueError):
    pass


def repeat_to_size(pattern: bytes, size: int) -> bytes:
    if not isinstance(pattern, bytes) or not pattern:
        raise KnownNovelV3Error("PATTERN_INVALID")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise KnownNovelV3Error("SIZE_INVALID")
    count = (size + len(pattern) - 1) // len(pattern)
    return (pattern * count)[:size]


def lookup_profile() -> dict[str, object]:
    return {
        "schema_id": "W7TP_ADI_KNOWN_NOVEL_V3_LOOKUP_PROFILE",
        "lookup_version": LOOKUP_VERSION,
        "source_sha256": V3_SOURCE_SHA256,
        "capability_ref": V3_CAPABILITY_REF,
        "authority_state": "EVIDENCE_ONLY_NOT_CANONICAL_AUTHORITY",
        "base_pattern_hex": BASE_PATTERN.hex(),
        "tokens": [
            {"token_id": token_id, "pattern_hex": pattern.hex()}
            for token_id, pattern in sorted(TOKEN_TABLE.items())
        ],
    }


def lookup_sha256() -> str:
    core = require_core()
    return core.sha256_hex(core.canonical_json_bytes(lookup_profile()))


def reconstruct_known_novel_v3(body: bytes) -> tuple[bytes, int, int]:
    """Exact pure receiver semantics observed on the live V3 node."""

    if len(body) < HEADER.size:
        raise KnownNovelV3Error("PACKET_TOO_SMALL")
    magic, size, block_size, known_count, novel_count = HEADER.unpack_from(body, 0)
    if magic != MAGIC:
        raise KnownNovelV3Error("MAGIC_INVALID")
    if size <= 0 or size > MAX_SIZE:
        raise KnownNovelV3Error("SIZE_INVALID")
    if block_size <= 0 or size % block_size != 0:
        raise KnownNovelV3Error("BLOCK_SIZE_INVALID")
    total_blocks = size // block_size
    if total_blocks > 65535:
        raise KnownNovelV3Error("BLOCK_COUNT_TOO_LARGE")
    if known_count + novel_count != total_blocks:
        raise KnownNovelV3Error("COVERAGE_COUNT_INVALID")
    state = bytearray(repeat_to_size(BASE_PATTERN, size))
    seen: set[int] = set()
    offset = HEADER.size
    for _ in range(known_count):
        if offset + KNOWN.size > len(body):
            raise KnownNovelV3Error("KNOWN_RECORD_TRUNCATED")
        block, token_id = KNOWN.unpack_from(body, offset)
        offset += KNOWN.size
        if block >= total_blocks or block in seen:
            raise KnownNovelV3Error("KNOWN_COORDINATE_INVALID")
        if token_id not in TOKEN_TABLE:
            raise KnownNovelV3Error("ADI_TOKEN_NOT_FOUND")
        seen.add(block)
        start = block * block_size
        state[start : start + block_size] = repeat_to_size(TOKEN_TABLE[token_id], block_size)
    for _ in range(novel_count):
        if offset + NOVEL_INDEX.size + block_size > len(body):
            raise KnownNovelV3Error("NOVEL_RECORD_TRUNCATED")
        block = NOVEL_INDEX.unpack_from(body, offset)[0]
        offset += NOVEL_INDEX.size
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


def build_known_novel_v3(target: bytes, *, block_size: int) -> tuple[bytes, int, int]:
    """Deterministic encoder for the observed receiver contract."""

    if not isinstance(target, bytes) or not target or len(target) > MAX_SIZE:
        raise KnownNovelV3Error("SIZE_INVALID")
    if isinstance(block_size, bool) or not isinstance(block_size, int) or block_size <= 0 or len(target) % block_size:
        raise KnownNovelV3Error("BLOCK_SIZE_INVALID")
    total_blocks = len(target) // block_size
    if total_blocks > 65535:
        raise KnownNovelV3Error("BLOCK_COUNT_TOO_LARGE")
    known: list[tuple[int, int]] = []
    novel: list[tuple[int, bytes]] = []
    token_blocks = {
        token_id: repeat_to_size(pattern, block_size)
        for token_id, pattern in TOKEN_TABLE.items()
    }
    for block in range(total_blocks):
        raw = target[block * block_size : (block + 1) * block_size]
        token_id = next((candidate for candidate, value in token_blocks.items() if value == raw), None)
        if token_id is None:
            novel.append((block, raw))
        else:
            known.append((block, token_id))
    body = bytearray(HEADER.pack(MAGIC, len(target), block_size, len(known), len(novel)))
    for block, token_id in known:
        body.extend(KNOWN.pack(block, token_id))
    for block, raw in novel:
        body.extend(NOVEL_INDEX.pack(block))
        body.extend(raw)
    rebuilt, known_count, novel_count = reconstruct_known_novel_v3(bytes(body))
    if rebuilt != target:
        raise KnownNovelV3Error("ENCODER_SELF_VERIFY_FAILED")
    return bytes(body), known_count, novel_count


def build_v3_artifact(
    target: bytes,
    *,
    block_sizes: Sequence[int] = (4096, 1024, 256, 64, 32, 16, 13, 8, 4, 2, 1),
) -> tuple[dict[str, object], bytes] | None:
    """Return the smallest exact canonical wrapper among eligible V3 blocks."""

    core = require_core()
    candidates: list[tuple[int, dict[str, object], bytes]] = []
    for block_size in block_sizes:
        if isinstance(block_size, bool) or not isinstance(block_size, int) or block_size < 1:
            raise MeshHold("HOLD_V3_BLOCK_SIZE_CONFIG")
        if len(target) % block_size:
            continue
        try:
            body, known_count, novel_count = build_known_novel_v3(target, block_size=block_size)
        except KnownNovelV3Error:
            continue
        artifact: dict[str, object] = {
            "schema_id": "W7TP_ADI_KNOWN_NOVEL_V3_PACKET",
            "source_sha256": V3_SOURCE_SHA256,
            "capability_ref": V3_CAPABILITY_REF,
            "lookup_version": LOOKUP_VERSION,
            "lookup_sha256": lookup_sha256(),
            "block_size": block_size,
            "known_count": known_count,
            "novel_count": novel_count,
            "body_bytes": len(body),
            "body_hex": body.hex(),
            "target_bytes": len(target),
            "target_sha256": hashlib.sha256(target).hexdigest(),
        }
        raw = core.canonical_json_bytes(artifact)
        candidates.append((len(raw), artifact, raw))
    if not candidates:
        return None
    _, artifact, raw = min(candidates, key=lambda item: (item[0], int(item[1]["block_size"])))
    return artifact, raw


def reconstruct_v3_artifact(
    artifact: dict[str, object],
    *,
    carried_lookup_profile: dict[str, object],
) -> bytes:
    expected = {
        "schema_id",
        "source_sha256",
        "capability_ref",
        "lookup_version",
        "lookup_sha256",
        "block_size",
        "known_count",
        "novel_count",
        "body_bytes",
        "body_hex",
        "target_bytes",
        "target_sha256",
    }
    if set(artifact) != expected or artifact.get("schema_id") != "W7TP_ADI_KNOWN_NOVEL_V3_PACKET":
        raise KnownNovelV3Error("V3_ARTIFACT_SHAPE_INVALID")
    if artifact.get("source_sha256") != V3_SOURCE_SHA256 or artifact.get("capability_ref") != V3_CAPABILITY_REF:
        raise KnownNovelV3Error("V3_SOURCE_BINDING_INVALID")
    numeric_contracts = {
        "block_size": 1,
        "known_count": 0,
        "novel_count": 0,
        "body_bytes": HEADER.size,
        "target_bytes": 1,
    }
    for key, minimum in numeric_contracts.items():
        value = artifact.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise KnownNovelV3Error("V3_NUMERIC_CONTRACT_INVALID")
    core = require_core()
    carried_lookup_sha = core.sha256_hex(core.canonical_json_bytes(carried_lookup_profile))
    if (
        carried_lookup_profile != lookup_profile()
        or carried_lookup_profile.get("lookup_version") != LOOKUP_VERSION
        or artifact.get("lookup_version") != LOOKUP_VERSION
        or artifact.get("lookup_sha256") != carried_lookup_sha
        or carried_lookup_sha != lookup_sha256()
    ):
        raise KnownNovelV3Error("V3_LOOKUP_HASH_INVALID")
    body_hex = artifact.get("body_hex")
    if not isinstance(body_hex, str):
        raise KnownNovelV3Error("V3_BODY_INVALID")
    try:
        body = bytes.fromhex(body_hex)
    except ValueError as exc:
        raise KnownNovelV3Error("V3_BODY_INVALID") from exc
    if artifact.get("body_bytes") != len(body):
        raise KnownNovelV3Error("V3_BODY_SIZE_INVALID")
    if len(body) < HEADER.size:
        raise KnownNovelV3Error("PACKET_TOO_SMALL")
    magic, header_size, header_block_size, header_known_count, header_novel_count = HEADER.unpack_from(body, 0)
    if magic != MAGIC:
        raise KnownNovelV3Error("MAGIC_INVALID")
    if artifact.get("block_size") != header_block_size:
        raise KnownNovelV3Error("V3_BLOCK_SIZE_BINDING_INVALID")
    if artifact.get("known_count") != header_known_count or artifact.get("novel_count") != header_novel_count:
        raise KnownNovelV3Error("V3_COUNT_BINDING_INVALID")
    if artifact.get("target_bytes") != header_size:
        raise KnownNovelV3Error("V3_TARGET_SIZE_BINDING_INVALID")
    state, known_count, novel_count = reconstruct_known_novel_v3(body)
    if artifact.get("known_count") != known_count or artifact.get("novel_count") != novel_count:
        raise KnownNovelV3Error("V3_COUNT_INVALID")
    if artifact.get("target_bytes") != len(state) or artifact.get("target_sha256") != hashlib.sha256(state).hexdigest():
        raise KnownNovelV3Error("V3_TARGET_HASH_INVALID")
    return state
