from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .contract import (
    DECISION_SCHEMA,
    KDF_ITERATIONS,
    KDF_NAME,
    NONCE_BYTES,
    SALT_BYTES,
    SCHEMA,
)
from .crypto import derive_key, envelope_id, used_marker_path
from .foundation import b64d, b64e, sha256_bytes, sha256_file, utc_now, write_json
from .governance import (
    append_audit,
    authorize_local_use,
    human_decision_id,
    read_passphrase,
    verify_human_decision,
)
from .hardware import hardware_fingerprint


def command_probe(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "probe")
    decision = verify_human_decision(args, "probe")
    payload = hardware_fingerprint()
    if args.output:
        write_json(Path(args.output), payload)
        print(f"probe_written={Path(args.output).resolve()}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("raw_hardware_printed=false")
    print("secret_material_printed=false")
    append_audit(
        Path(args.audit_log),
        {
            "event": "system_total_probe",
            "result": "ok",
            "fingerprint_sha256": payload["fingerprint_sha256"],
            **auth,
            **decision,
        },
    )
    return 0


def command_seal(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "seal")
    decision = verify_human_decision(args, "seal")
    source = Path(args.input)
    output = Path(args.output)
    if not source.exists():
        raise SystemExit(f"missing input: {source}")
    fingerprint = hardware_fingerprint()["fingerprint_sha256"]
    plaintext = source.read_bytes()
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    passphrase = read_passphrase(args)
    key = derive_key(passphrase, fingerprint, salt)
    aad = f"{SCHEMA}\0{fingerprint}".encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    envelope: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": utc_now(),
        "hardware_fingerprint_sha256": fingerprint,
        "kdf": {
            "name": KDF_NAME,
            "iterations": KDF_ITERATIONS,
            "salt_b64": b64e(salt),
        },
        "aead": {
            "name": "AES-256-GCM",
            "nonce_b64": b64e(nonce),
            "ciphertext_b64": b64e(ciphertext),
        },
        "plaintext_sha256": sha256_bytes(plaintext),
        "plaintext_printed": False,
        "secret_material_printed": False,
        "one_time": True,
    }
    envelope["envelope_id"] = envelope_id(envelope)
    write_json(output, envelope)
    append_audit(
        Path(args.audit_log),
        {
            "event": "seal_hardware_bound_envelope",
            "result": "ok",
            "envelope_id": envelope["envelope_id"],
            "hardware_fingerprint_sha256": fingerprint,
            "plaintext_sha256": envelope["plaintext_sha256"],
            **auth,
            **decision,
        },
    )
    print(f"envelope_written={output.resolve()}")
    print(f"envelope_id={envelope['envelope_id']}")
    print("plaintext_printed=false")
    print("secret_material_printed=false")
    return 0


def command_decrypt_once(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "decrypt-once")
    decision = verify_human_decision(args, "decrypt-once")
    envelope_path = Path(args.envelope)
    output_path = Path(args.output)
    used_dir = Path(args.used_dir)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    if envelope.get("schema") != SCHEMA:
        raise SystemExit("unsupported envelope schema")
    current_fingerprint = hardware_fingerprint()["fingerprint_sha256"]
    expected_fingerprint = envelope.get("hardware_fingerprint_sha256")
    if current_fingerprint != expected_fingerprint:
        append_audit(
            Path(args.audit_log),
            {
                "event": "decrypt_once",
                "result": "block",
                "risk": "L3_metric_hazard",
                "reason": "hardware_fingerprint_mismatch",
                "envelope_id": envelope.get("envelope_id"),
                **auth,
                **decision,
            },
        )
        print("decrypted=false")
        print("risk=L3_metric_hazard")
        print("reason=hardware_fingerprint_mismatch")
        return 3

    marker = used_marker_path(used_dir, envelope)
    if marker.exists():
        append_audit(
            Path(args.audit_log),
            {
                "event": "decrypt_once",
                "result": "block",
                "risk": "L3_metric_hazard",
                "reason": "one_time_marker_exists",
                "envelope_id": envelope.get("envelope_id"),
                **auth,
                **decision,
            },
        )
        print("decrypted=false")
        print("risk=L3_metric_hazard")
        print("reason=one_time_marker_exists")
        return 4

    passphrase = read_passphrase(args)
    salt = b64d(envelope["kdf"]["salt_b64"])
    nonce = b64d(envelope["aead"]["nonce_b64"])
    ciphertext = b64d(envelope["aead"]["ciphertext_b64"])
    key = derive_key(passphrase, current_fingerprint, salt)
    aad = f"{SCHEMA}\0{current_fingerprint}".encode("utf-8")
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except Exception:
        append_audit(
            Path(args.audit_log),
            {
                "event": "decrypt_once",
                "result": "block",
                "risk": "L3_metric_hazard",
                "reason": "decrypt_failed",
                "envelope_id": envelope.get("envelope_id"),
                **auth,
                **decision,
            },
        )
        print("decrypted=false")
        print("risk=L3_metric_hazard")
        print("reason=decrypt_failed")
        return 5

    output_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(output_path, flags, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "wb") as handle:
        handle.write(plaintext)

    output_hash = sha256_bytes(plaintext)
    marker_payload = {
        "schema": "taiji.one_time_decrypt_marker.v1",
        "used_at": utc_now(),
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": sha256_file(envelope_path),
        "hardware_fingerprint_sha256": current_fingerprint,
        "output_sha256": output_hash,
        "plaintext_printed": False,
    }
    write_json(marker, marker_payload)
    append_audit(
        Path(args.audit_log),
        {
            "event": "decrypt_once",
            "result": "ok",
            "risk": "L1_near",
            "envelope_id": envelope["envelope_id"],
            "output_sha256": output_hash,
            **auth,
            **decision,
        },
    )
    print("decrypted=true")
    print(f"output_written={output_path.resolve()}")
    print(f"used_marker_written={marker.resolve()}")
    print("plaintext_printed=false")
    print("secret_material_printed=false")
    return 0


def command_self_test(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "self-test")
    decision = verify_human_decision(args, "self-test")
    append_audit(
        Path(args.audit_log),
        {
            "event": "system_total_probe_self_test",
            "result": "started",
            **auth,
            **decision,
        },
    )
    with tempfile.TemporaryDirectory(prefix="taiji_probe_selftest_") as tmp:
        root = Path(tmp)
        plain = root / "plain.txt"
        envelope = root / "envelope.json"
        output = root / "output.txt"
        pass_file = root / "passphrase.txt"
        auth_file = root / "local_auth.txt"
        decision_file = root / "human_decision.json"
        audit = root / "audit.jsonl"
        used = root / "used"
        plain.write_text("non-secret self-test payload\n", encoding="utf-8")
        pass_file.write_text("public-self-test-passphrase\n", encoding="utf-8")
        auth_file.write_text("public-self-test-local-auth\n", encoding="utf-8")
        fingerprint = hardware_fingerprint()["fingerprint_sha256"]
        receipt = {
            "schema": DECISION_SCHEMA,
            "issued_at": utc_now(),
            "expires_at": "2099-01-01T00:00:00+00:00",
            "scope": "all",
            "decision": "allow",
            "hardware_fingerprint_sha256": fingerprint,
            "human_proof_sha256": sha256_bytes(b"public-self-test-human-proof"),
            "human_proof_source": "self-test",
            "human_proof_printed": False,
            "local_authorization_event_id": "self-test",
        }
        receipt["decision_id"] = human_decision_id(receipt)
        write_json(decision_file, receipt)
        seal_args = argparse.Namespace(
            input=plain,
            output=envelope,
            passphrase_env=None,
            passphrase_file=pass_file,
            local_auth_env=None,
            local_auth_file=auth_file,
            human_decision=decision_file,
            audit_log=audit,
        )
        decrypt_args = argparse.Namespace(
            envelope=envelope,
            output=output,
            used_dir=used,
            passphrase_env=None,
            passphrase_file=pass_file,
            local_auth_env=None,
            local_auth_file=auth_file,
            human_decision=decision_file,
            audit_log=audit,
        )
        seal_code = command_seal(seal_args)
        decrypt_code = command_decrypt_once(decrypt_args)
        second_code = command_decrypt_once(decrypt_args)
        ok = seal_code == 0 and decrypt_code == 0 and second_code == 4
        append_audit(
            Path(args.audit_log),
            {
                "event": "system_total_probe_self_test",
                "result": "ok" if ok else "failed",
                "second_decrypt_blocked": second_code == 4,
            },
        )
        print(f"self_test={'PASS' if ok else 'FAIL'}")
        print("second_decrypt_blocked=true")
        return 0 if ok else 1
