"""taiji01 本機節點證據候選。

用途：
- 證明目前執行載體為 taiji01 的候選證據。
- 不建立自然人身份。
- 不建立設備主權。
- 不修改設備清單。
- 不建立正式權威。
- 原始本機識別材料只在本機雜湊，不輸出明文。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import stat
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "W7TP-LOCAL-NODE-EVIDENCE-CANDIDATE/1.0"
PACKET_TYPE = "LOCAL_NODE_EXECUTION_CARRIER_EVIDENCE_CANDIDATE"
TARGET_HOSTNAME = "taiji01"
NODE_REF = "node_ref:taiji01"

MACHINE_ID_PATH = Path("/etc/machine-id")
PRODUCT_UUID_PATH = Path("/sys/class/dmi/id/product_uuid")

SSH_PUBLIC_KEY_PATHS = (
    Path("/etc/ssh/ssh_host_ed25519_key.pub"),
    Path("/etc/ssh/ssh_host_ecdsa_key.pub"),
    Path("/etc/ssh/ssh_host_rsa_key.pub"),
)

ALLOWED_SOURCE_NAMES = frozenset(
    {
        "machine_id",
        "ssh_host_public_key",
        "product_uuid",
    }
)

SAFETY_FALSE_FIELDS = (
    "identity_created",
    "device_sovereignty_created",
    "inventory_write",
    "db_write",
    "deploy",
    "restart",
    "git_push",
    "raw_identifier_exposed",
)

MAX_SOURCE_BYTES = 16 * 1024

PACKET_FIELDS = frozenset(
    {
        "schema_version",
        "packet_type",
        "state",
        "reason_code",
        "candidate_only",
        "node_ref",
        "observed_hostname",
        "source_hashes",
        "source_count",
        "challenge_sha256",
        "local_node_fingerprint_sha256",
        "semantic_boundary",
        "authority",
        *SAFETY_FALSE_FIELDS,
        "evidence_sha256",
    }
)


def _semantic_boundary() -> dict[str, Any]:
    return {
        "natural_person_identity": False,
        "device_is_identity": False,
        "node_is_authority": False,
        "purpose": "LOCAL_EXECUTION_CARRIER_EVIDENCE",
    }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _read_nonempty(path: Path) -> str | None:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None
        data = os.read(descriptor, MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            return None
        value = data.decode("utf-8").strip()
    except (OSError, UnicodeError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return value or None


def collect_local_material() -> dict[str, str]:
    """只讀取非秘密或公開本機識別材料；不讀任何 SSH 私鑰。"""

    material: dict[str, str] = {}

    machine_id = _read_nonempty(MACHINE_ID_PATH)
    if machine_id:
        material["machine_id"] = machine_id

    for path in SSH_PUBLIC_KEY_PATHS:
        public_key = _read_nonempty(path)
        if public_key:
            material["ssh_host_public_key"] = public_key
            break

    product_uuid = _read_nonempty(PRODUCT_UUID_PATH)
    if product_uuid:
        material["product_uuid"] = product_uuid

    return material


def _source_hashes(source_material: Mapping[str, str]) -> dict[str, str]:
    hashes: dict[str, str] = {}

    for name in sorted(ALLOWED_SOURCE_NAMES):
        value = source_material.get(name)
        if isinstance(value, str) and value.strip():
            hashes[name] = _sha256_bytes(value.strip().encode("utf-8"))

    return hashes


def _finalize(packet: dict[str, Any]) -> dict[str, Any]:
    basis = dict(packet)
    basis.pop("evidence_sha256", None)
    packet["evidence_sha256"] = _canonical_sha256(basis)
    return packet


def _hold(
    reason_code: str,
    *,
    hostname: str,
    source_hashes: Mapping[str, str],
    challenge_sha256: str | None,
) -> dict[str, Any]:
    return _finalize(
        {
            "schema_version": SCHEMA_VERSION,
            "packet_type": PACKET_TYPE,
            "state": "HOLD_LOCAL_NODE_EVIDENCE_CANDIDATE",
            "reason_code": reason_code,
            "candidate_only": True,
            "node_ref": NODE_REF,
            "observed_hostname": hostname,
            "source_hashes": dict(sorted(source_hashes.items())),
            "source_count": len(source_hashes),
            "challenge_sha256": challenge_sha256,
            "local_node_fingerprint_sha256": None,
            "semantic_boundary": _semantic_boundary(),
            "authority": "NONE",
            "identity_created": False,
            "device_sovereignty_created": False,
            "inventory_write": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "git_push": False,
            "raw_identifier_exposed": False,
        }
    )


def build_local_node_evidence(
    *,
    hostname: str,
    source_material: Mapping[str, str],
    challenge: str | None,
) -> dict[str, Any]:
    """建立 taiji01 本機節點證據候選。"""

    hashes = _source_hashes(source_material)
    challenge_sha256 = (
        _sha256_bytes(challenge.encode("utf-8"))
        if isinstance(challenge, str) and challenge
        else None
    )

    if hostname != TARGET_HOSTNAME:
        return _hold(
            "HOLD_LOCAL_NODE_TARGET_MISMATCH",
            hostname=hostname,
            source_hashes=hashes,
            challenge_sha256=challenge_sha256,
        )

    if challenge_sha256 is None:
        return _hold(
            "HOLD_LOCAL_NODE_CHALLENGE_REQUIRED",
            hostname=hostname,
            source_hashes=hashes,
            challenge_sha256=None,
        )

    # 至少要求兩類本機材料，避免單靠 hostname 或單一識別值成立。
    if len(hashes) < 2:
        return _hold(
            "HOLD_LOCAL_NODE_EVIDENCE_INSUFFICIENT",
            hostname=hostname,
            source_hashes=hashes,
            challenge_sha256=challenge_sha256,
        )

    fingerprint_basis = {
        "node_ref": NODE_REF,
        "source_hashes": dict(sorted(hashes.items())),
        "challenge_sha256": challenge_sha256,
    }
    fingerprint = _canonical_sha256(fingerprint_basis)

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "packet_type": PACKET_TYPE,
        "state": "PASS_LOCAL_NODE_EVIDENCE_CANDIDATE",
        "reason_code": "EVIDENCED_LOCAL_NODE_EXECUTION_CARRIER",
        "candidate_only": True,
        "node_ref": NODE_REF,
        "observed_hostname": hostname,
        "source_hashes": dict(sorted(hashes.items())),
        "source_count": len(hashes),
        "challenge_sha256": challenge_sha256,
        "local_node_fingerprint_sha256": fingerprint,
        "semantic_boundary": _semantic_boundary(),
        "authority": "NONE",
        "identity_created": False,
        "device_sovereignty_created": False,
        "inventory_write": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "git_push": False,
        "raw_identifier_exposed": False,
    }

    return _finalize(packet)


def verify_local_node_evidence(
    packet: Mapping[str, Any],
    *,
    expected_source_material: Mapping[str, str] | None = None,
    expected_challenge: str | None = None,
) -> tuple[bool, str]:
    """唯讀驗證候選完整性，並在提供本機材料與挑戰時重驗來源。"""

    packet_fields = set(packet)
    if packet_fields != PACKET_FIELDS:
        if packet_fields - PACKET_FIELDS:
            return False, "UNKNOWN_FIELD_REJECTED"
        return False, "REQUIRED_FIELD_MISSING"

    if packet.get("schema_version") != SCHEMA_VERSION:
        return False, "SCHEMA_VERSION_MISMATCH"

    if packet.get("packet_type") != PACKET_TYPE:
        return False, "PACKET_TYPE_MISMATCH"

    if packet.get("candidate_only") is not True:
        return False, "CANDIDATE_BOUNDARY_FAIL"

    if packet.get("authority") != "NONE":
        return False, "AUTHORITY_ESCALATION"

    if packet.get("node_ref") != NODE_REF:
        return False, "NODE_REF_MISMATCH"

    if packet.get("semantic_boundary") != _semantic_boundary():
        return False, "SEMANTIC_BOUNDARY_MISMATCH"

    for field in SAFETY_FALSE_FIELDS:
        if packet.get(field) is not False:
            return False, f"{field.upper()}_FORBIDDEN"

    source_hashes = packet.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        return False, "SOURCE_HASHES_INVALID"

    if not set(source_hashes).issubset(ALLOWED_SOURCE_NAMES):
        return False, "SOURCE_NAME_NOT_ALLOWED"

    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in source_hashes.values()
    ):
        return False, "SOURCE_HASH_INVALID"

    if packet.get("source_count") != len(source_hashes):
        return False, "SOURCE_COUNT_MISMATCH"

    challenge_sha256 = packet.get("challenge_sha256")
    if challenge_sha256 is not None and (
        not isinstance(challenge_sha256, str)
        or len(challenge_sha256) != 64
        or any(character not in "0123456789abcdef" for character in challenge_sha256)
    ):
        return False, "CHALLENGE_HASH_INVALID"

    state = packet.get("state")
    reason_code = packet.get("reason_code")
    hostname = packet.get("observed_hostname")
    if not isinstance(hostname, str) or not hostname:
        return False, "OBSERVED_HOSTNAME_INVALID"

    if state == "PASS_LOCAL_NODE_EVIDENCE_CANDIDATE":
        if reason_code != "EVIDENCED_LOCAL_NODE_EXECUTION_CARRIER":
            return False, "PASS_REASON_MISMATCH"
        if hostname != TARGET_HOSTNAME:
            return False, "PASS_HOSTNAME_MISMATCH"
        if challenge_sha256 is None:
            return False, "PASS_CHALLENGE_MISSING"
        if len(source_hashes) < 2:
            return False, "SOURCE_COUNT_INSUFFICIENT"

        expected_fingerprint = _canonical_sha256(
            {
                "node_ref": NODE_REF,
                "source_hashes": dict(sorted(source_hashes.items())),
                "challenge_sha256": challenge_sha256,
            }
        )
        if packet.get("local_node_fingerprint_sha256") != expected_fingerprint:
            return False, "LOCAL_NODE_FINGERPRINT_MISMATCH"
    elif state == "HOLD_LOCAL_NODE_EVIDENCE_CANDIDATE":
        if packet.get("local_node_fingerprint_sha256") is not None:
            return False, "HOLD_FINGERPRINT_FORBIDDEN"
        if reason_code == "HOLD_LOCAL_NODE_TARGET_MISMATCH":
            if hostname == TARGET_HOSTNAME:
                return False, "HOLD_REASON_MISMATCH"
        elif reason_code == "HOLD_LOCAL_NODE_CHALLENGE_REQUIRED":
            if hostname != TARGET_HOSTNAME or challenge_sha256 is not None:
                return False, "HOLD_REASON_MISMATCH"
        elif reason_code == "HOLD_LOCAL_NODE_EVIDENCE_INSUFFICIENT":
            if (
                hostname != TARGET_HOSTNAME
                or challenge_sha256 is None
                or len(source_hashes) >= 2
            ):
                return False, "HOLD_REASON_MISMATCH"
        else:
            return False, "HOLD_REASON_UNKNOWN"
    else:
        return False, "STATE_INVALID"

    basis = dict(packet)
    supplied_hash = basis.pop("evidence_sha256", None)
    expected_hash = _canonical_sha256(basis)

    if supplied_hash != expected_hash:
        return False, "EVIDENCE_SHA256_MISMATCH"

    if state == "HOLD_LOCAL_NODE_EVIDENCE_CANDIDATE":
        return False, f"VERIFIED_{reason_code}"

    if expected_challenge is None:
        return False, "AUTHENTICITY_UNVERIFIED_CHALLENGE"
    expected_challenge_sha256 = _sha256_bytes(
        expected_challenge.encode("utf-8")
    )
    if challenge_sha256 != expected_challenge_sha256:
        return False, "CHALLENGE_MISMATCH"

    if expected_source_material is None:
        return False, "AUTHENTICITY_UNVERIFIED_SOURCE"
    expected_source_hashes = _source_hashes(expected_source_material)
    if dict(source_hashes) != expected_source_hashes:
        return False, "LOCAL_SOURCE_MISMATCH"

    return True, "PASS_LOCAL_NODE_EVIDENCE_LOCAL_RECHECKED"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 taiji01 本機節點證據候選"
    )
    parser.add_argument(
        "--challenge",
        required=True,
        help="由驗證端提供的一次性非秘密挑戰值",
    )
    args = parser.parse_args()

    source_material = collect_local_material()
    candidate = build_local_node_evidence(
        hostname=socket.gethostname(),
        source_material=source_material,
        challenge=args.challenge,
    )

    valid, verifier_state = verify_local_node_evidence(
        candidate,
        expected_source_material=source_material,
        expected_challenge=args.challenge,
    )
    envelope = {
        "candidate": candidate,
        "verifier": {
            "decision": "PASS" if valid else "HOLD",
            "result": verifier_state,
            "local_source_rechecked": True,
            "challenge_rechecked": True,
            "authority": "NONE",
        },
    }
    print(
        json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
    return 0 if valid else 4


if __name__ == "__main__":
    raise SystemExit(main())
