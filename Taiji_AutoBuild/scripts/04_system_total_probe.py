#!/usr/bin/env python3
"""System total probe with hardware-bound one-time decrypt envelopes.

The probe never prints raw hardware identifiers. Decryption is local-only,
hardware-bound, audited, and one-time by marker file.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT = ROOT_DIR / "Taiji_Governance" / "logs" / "system_total_probe_audit.jsonl"
DEFAULT_USED_DIR = ROOT_DIR / "Taiji_Governance" / "one_time_decrypt" / "used"
DEFAULT_RESCUE_DIR = ROOT_DIR / "Taiji_Governance" / "rescue_snapshots"
DEFAULT_DECISION_DIR = ROOT_DIR / "Taiji_Governance" / "human_decisions"
SCHEMA = "taiji.hardware_bound_one_time_envelope.v1"
DECISION_SCHEMA = "taiji.human_decision_receipt.v1"
KDF_NAME = "pbkdf2_hmac_sha256"
KDF_ITERATIONS = 390_000
LOCAL_AUTH_MIN_LENGTH = 8
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
CRITICAL_FILES = [
    "legacy_core/wuchang_tailscale_deployer.py",
    "services/gateway/app.py",
    "Taiji_Odoo/docker-compose.yml",
    "Taiji_Vector_Runtime_Lite/manifest.yml",
    "Taiji_Vector_Runtime_Lite/app/main.py",
    "Taiji_Governance/worklist/worklist.md",
    "Taiji_Governance/progress/progress.md",
    "Taiji_Governance/identity/digital_identity.yml",
    "Taiji_Governance/architecture/layers_standards.yml",
    "Taiji_Governance/deployments/cafe_main_redeploy_status.md",
    "Taiji_Governance/deployments/tailscale_deployment_manifest.json",
    "Taiji_Governance/deployments/tailscale_preflight_record.json",
    "Taiji_AutoBuild/scripts/00_readonly_probe.sh",
    "Taiji_AutoBuild/scripts/03_collect_runtime_snapshot.sh",
    "Taiji_AutoBuild/scripts/04_system_total_probe.py",
]
FORBIDDEN_PATTERNS = [
    r"taiji-guarded-run",
    r"--execute",
    r"StrictHostKeyChecking=no",
    r"systemctl\s+restart",
    r"docker\s+compose\s+up",
    r"docker\s+compose\s+down",
    r"create_subprocess_shell",
    r"os\.system",
    r"\bPopen\b",
    r"\bscp\b",
]


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


def read_signal(path: Path, max_bytes: int = 4096) -> bytes | None:
    try:
        data = path.read_bytes()[:max_bytes].strip()
    except OSError:
        return None
    return data or None


def commandless_hardware_signals() -> list[dict[str, Any]]:
    candidates = {
        "etc_machine_id": Path("/etc/machine-id"),
        "dbus_machine_id": Path("/var/lib/dbus/machine-id"),
        "dmi_product_uuid": Path("/sys/class/dmi/id/product_uuid"),
        "dmi_product_serial": Path("/sys/class/dmi/id/product_serial"),
        "dmi_board_serial": Path("/sys/class/dmi/id/board_serial"),
    }
    signals: list[dict[str, Any]] = []
    for name, path in candidates.items():
        data = read_signal(path)
        signals.append(
            {
                "name": name,
                "available": data is not None,
                "sha256": sha256_bytes(data) if data else None,
                "raw_printed": False,
            }
        )

    platform_blob = "\n".join(
        [
            platform.system(),
            platform.release(),
            platform.machine(),
            str(os.cpu_count() or ""),
            socket.gethostname(),
        ]
    ).encode("utf-8")
    signals.append(
        {
            "name": "platform_runtime",
            "available": True,
            "sha256": sha256_bytes(platform_blob),
            "raw_printed": False,
        }
    )
    return signals


def hardware_fingerprint() -> dict[str, Any]:
    signals = commandless_hardware_signals()
    stable = [
        f"{item['name']}={item['sha256']}"
        for item in signals
        if item.get("available") and item.get("sha256")
    ]
    aggregate = "\n".join(sorted(stable)).encode("utf-8")
    return {
        "schema": "taiji.hardware_fingerprint.v1",
        "generated_at": utc_now(),
        "fingerprint_sha256": sha256_bytes(aggregate),
        "signal_count": len(stable),
        "signals": signals,
        "raw_hardware_printed": False,
    }


def append_audit(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts", utc_now())
    event.setdefault("actor", "system_total_probe")
    event.setdefault("secret_material_printed", False)
    event.setdefault("raw_hardware_printed", False)
    event.setdefault("external_api_called", False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


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


def read_secret(
    *,
    env_name: str | None,
    file_path: Path | None,
    prompt: str,
    label: str,
    min_length: int = 1,
) -> tuple[str, str]:
    if env_name:
        value = os.environ.get(env_name)
        if not value:
            raise SystemExit(f"missing {label} env: {env_name}")
        secret = value
        source = "env"
    elif file_path:
        data = Path(file_path).read_text(encoding="utf-8")
        secret = data.rstrip("\n")
        source = "file"
    else:
        if not sys.stdin.isatty():
            raise SystemExit(
                f"{label} requires an env var, a local file, or an interactive TTY"
            )
        secret = getpass.getpass(prompt)
        source = "tty"
    if len(secret) < min_length:
        raise SystemExit(f"{label} is too short")
    return secret, source


def read_passphrase(args: argparse.Namespace) -> str:
    secret, _source = read_secret(
        env_name=args.passphrase_env,
        file_path=args.passphrase_file,
        prompt="Taiji one-time passphrase: ",
        label="passphrase",
    )
    return secret


def authorize_local_use(args: argparse.Namespace, purpose: str) -> dict[str, Any]:
    secret, source = read_secret(
        env_name=args.local_auth_env,
        file_path=args.local_auth_file,
        prompt=f"Taiji local authorization for {purpose}: ",
        label="local authorization",
        min_length=LOCAL_AUTH_MIN_LENGTH,
    )
    fingerprint = hardware_fingerprint()["fingerprint_sha256"]
    auth_material = f"{fingerprint}\0{purpose}\0{secret}".encode("utf-8")
    auth_event_id = sha256_bytes(auth_material + os.urandom(16))[:24]
    return {
        "local_authorization": "passed",
        "local_authorization_source": source,
        "local_authorization_event_id": auth_event_id,
        "local_authorization_secret_printed": False,
    }


def human_decision_id(payload: dict[str, Any]) -> str:
    clone = dict(payload)
    clone.pop("decision_id", None)
    data = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(data)


def create_human_decision(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "human-decision")
    proof, proof_source = read_secret(
        env_name=args.human_proof_env,
        file_path=args.human_proof_file,
        prompt="Human decision proof: ",
        label="human decision proof",
        min_length=LOCAL_AUTH_MIN_LENGTH,
    )
    fingerprint = hardware_fingerprint()["fingerprint_sha256"]
    proof_hash = sha256_bytes(f"{fingerprint}\0{args.scope}\0{proof}".encode("utf-8"))
    issued_at = utc_now()
    receipt = {
        "schema": DECISION_SCHEMA,
        "issued_at": issued_at,
        "expires_at": args.expires_at,
        "scope": args.scope,
        "decision": args.decision,
        "hardware_fingerprint_sha256": fingerprint,
        "human_proof_sha256": proof_hash,
        "human_proof_source": proof_source,
        "human_proof_printed": False,
        "local_authorization_event_id": auth["local_authorization_event_id"],
    }
    receipt["decision_id"] = human_decision_id(receipt)
    output_dir = Path(args.output_dir)
    output = output_dir / f"{receipt['decision_id']}.decision.json"
    write_json(output, receipt)
    append_audit(
        Path(args.audit_log),
        {
            "event": "human_decision_receipt_created",
            "result": "ok",
            "decision_id": receipt["decision_id"],
            "scope": args.scope,
            "decision": args.decision,
            "human_proof_printed": False,
            **auth,
        },
    )
    print(f"human_decision_written={output.resolve()}")
    print(f"decision_id={receipt['decision_id']}")
    print("human_proof_printed=false")
    print("secret_material_printed=false")
    return 0


def verify_human_decision(args: argparse.Namespace, purpose: str) -> dict[str, Any]:
    path = getattr(args, "human_decision", None)
    if not path:
        raise SystemExit(f"human decision receipt required for {purpose}")
    receipt_path = Path(path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != DECISION_SCHEMA:
        raise SystemExit("invalid human decision receipt schema")
    current_fingerprint = hardware_fingerprint()["fingerprint_sha256"]
    if receipt.get("hardware_fingerprint_sha256") != current_fingerprint:
        raise SystemExit("human decision receipt hardware mismatch")
    if receipt.get("decision") != "allow":
        raise SystemExit("human decision does not allow this action")
    scope = receipt.get("scope")
    if scope not in {purpose, "all"}:
        raise SystemExit(f"human decision scope mismatch: {scope}")
    expires_at = receipt.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        raise SystemExit("human decision receipt expired")
    expected = human_decision_id(receipt)
    if receipt.get("decision_id") != expected:
        raise SystemExit("human decision receipt integrity check failed")
    return {
        "human_decision": "passed",
        "human_decision_id": receipt["decision_id"],
        "human_decision_scope": scope,
        "human_decision_secret_printed": False,
    }


def derive_key(passphrase: str, fingerprint: str, salt: bytes) -> bytes:
    material = f"{fingerprint}\0{passphrase}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", material, salt, KDF_ITERATIONS, dklen=KEY_BYTES)


def envelope_id(envelope: dict[str, Any]) -> str:
    clone = dict(envelope)
    clone.pop("envelope_id", None)
    data = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(data)


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


def used_marker_path(used_dir: Path, envelope: dict[str, Any]) -> Path:
    return used_dir / f"{envelope['envelope_id']}.used.json"


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


def scan_file_forbidden(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                findings.append({"file": str(path.relative_to(ROOT_DIR)), "line": index, "pattern": pattern})
    return findings


def critical_file_manifest() -> list[dict[str, Any]]:
    manifest = []
    for relative in CRITICAL_FILES:
        path = ROOT_DIR / relative
        manifest.append(
            {
                "path": relative,
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else None,
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )
    return manifest


def build_rescue_snapshot(auth: dict[str, Any]) -> dict[str, Any]:
    fingerprint = hardware_fingerprint()
    deployer = ROOT_DIR / "legacy_core" / "wuchang_tailscale_deployer.py"
    forbidden_findings = scan_file_forbidden(deployer)
    preflight_record = ROOT_DIR / "Taiji_Governance" / "deployments" / "tailscale_preflight_record.json"
    progress = ROOT_DIR / "Taiji_Governance" / "progress" / "progress.md"
    worklist = ROOT_DIR / "Taiji_Governance" / "worklist" / "worklist.md"
    architecture = ROOT_DIR / "Taiji_Governance" / "architecture" / "layers_standards.yml"
    return {
        "schema": "taiji.ai_rescue_snapshot.v1",
        "generated_at": utc_now(),
        "purpose": "AI derailment / context-loss rescue anchor",
        "local_authorization": {
            "status": auth["local_authorization"],
            "source": auth["local_authorization_source"],
            "event_id": auth["local_authorization_event_id"],
            "secret_printed": False,
        },
        "safety": {
            "raw_hardware_printed": False,
            "secret_material_printed": False,
            "chatgpt_export_text_included": False,
            "google_private_data_included": False,
            "odoo_member_plaintext_included": False,
            "external_api_called": False,
            "remote_execution": False,
        },
        "hardware_anchor": {
            "fingerprint_sha256": fingerprint["fingerprint_sha256"],
            "signal_count": fingerprint["signal_count"],
            "raw_signals_printed": False,
        },
        "physical_layer": {
            "binding": "local_hardware_fingerprint",
            "signals": [
                {
                    "name": signal["name"],
                    "available": signal["available"],
                    "sha256": signal["sha256"],
                    "raw_printed": False,
                }
                for signal in fingerprint["signals"]
            ],
            "raw_machine_id_printed": False,
            "raw_serial_printed": False,
            "raw_hostname_printed": False,
        },
        "cryptographic_layer": {
            "envelope_schema": SCHEMA,
            "aead": "AES-256-GCM",
            "kdf": KDF_NAME,
            "kdf_iterations": KDF_ITERATIONS,
            "hardware_bound_key_material": True,
            "local_authorization_required_every_use": True,
            "one_time_decrypt_marker_required": True,
            "plaintext_stdout_allowed": False,
            "secret_material_printed": False,
        },
        "governance_mode": {
            "allowed_modes": ["manifest-only", "preflight-only", "local-auth-required"],
            "forbidden_commands": [
                "ssh",
                "scp",
                "systemctl restart",
                "docker compose up",
                "docker compose down",
                "taiji-guarded-run",
                "--execute",
            ],
            "risk_scale": {
                "L0_exact_match": "allow",
                "L1_near": "allow_with_audit",
                "L2_drift": "warn",
                "L3_metric_hazard": "block",
            },
        },
        "runtime_checks": {
            "tailscale_status": run_status_check(["tailscale", "status"]),
            "tailscale_ip": run_status_check(["tailscale", "ip", "-4"]),
            "five_metric_health": local_json_get("http://127.0.0.1:8105/health"),
            "five_metric_policy": local_json_get("http://127.0.0.1:8105/policy"),
            "taiji_metric_preflight_exists": shutil.which("taiji-metric-preflight") is not None,
        },
        "critical_files": critical_file_manifest(),
        "forbidden_scan": {
            "target": str(deployer.relative_to(ROOT_DIR)),
            "findings": forbidden_findings,
            "risk": "L3_metric_hazard" if forbidden_findings else "L0_exact_match",
        },
        "preflight_record": safe_text_excerpt(preflight_record),
        "architecture_profile": safe_text_excerpt(architecture),
        "progress_excerpt": safe_text_excerpt(progress),
        "worklist_excerpt": safe_text_excerpt(worklist),
        "resume_instructions": [
            "Treat this file as a rescue anchor, not a source of secrets.",
            "Do not execute remote deployment from this snapshot.",
            "Resume by reading critical files, then rerun syntax and forbidden-command scans.",
            "If runtime_checks show Five Metric or Tailscale unavailable, keep deployment blocked.",
        ],
    }


def command_rescue_snapshot(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "rescue-snapshot")
    decision = verify_human_decision(args, "rescue-snapshot")
    snapshot = build_rescue_snapshot(auth)
    snapshot["human_decision"] = decision
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"ai_rescue_snapshot_{stamp}.json"
    write_json(output, snapshot)
    snapshot_hash = sha256_file(output)
    append_audit(
        Path(args.audit_log),
        {
            "event": "ai_rescue_snapshot",
            "result": "ok",
            "snapshot_path": str(output),
            "snapshot_sha256": snapshot_hash,
            "risk": snapshot["forbidden_scan"]["risk"],
            **auth,
            **decision,
        },
    )
    print(f"rescue_snapshot_written={output.resolve()}")
    print(f"rescue_snapshot_sha256={snapshot_hash}")
    print("raw_hardware_printed=false")
    print("secret_material_printed=false")
    print("external_api_called=false")
    return 0


def add_local_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--local-auth-env",
        help="Environment variable containing local authorization secret for this use.",
    )
    parser.add_argument(
        "--local-auth-file",
        type=Path,
        help="Local file containing authorization secret for this use. Content is never printed.",
    )


def add_human_decision_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--human-decision",
        type=Path,
        help="Required human decision receipt for this command.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Taiji system total probe and one-time decrypt tool.")
    parser.set_defaults(func=command_probe)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(parser)

    subparsers = parser.add_subparsers(dest="command")

    decision = subparsers.add_parser("human-decision", help="Create a local human decision receipt.")
    decision.add_argument(
        "--scope",
        required=True,
        choices=[
            "probe",
            "seal",
            "decrypt-once",
            "self-test",
            "rescue-snapshot",
            "red-blue-exchange",
            "all",
        ],
    )
    decision.add_argument("--decision", choices=["allow", "deny"], default="allow")
    decision.add_argument("--expires-at", required=True, help="ISO-8601 timestamp with timezone.")
    decision.add_argument("--human-proof-env")
    decision.add_argument("--human-proof-file", type=Path)
    decision.add_argument("--output-dir", type=Path, default=DEFAULT_DECISION_DIR)
    decision.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(decision)
    decision.set_defaults(func=create_human_decision)

    probe = subparsers.add_parser("probe", help="Print or write hardware-bound probe metadata.")
    probe.add_argument("--output", type=Path)
    probe.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(probe)
    add_human_decision_arg(probe)
    probe.set_defaults(func=command_probe)

    seal = subparsers.add_parser("seal", help="Create a hardware-bound one-time envelope.")
    seal.add_argument("--input", required=True, type=Path)
    seal.add_argument("--output", required=True, type=Path)
    seal.add_argument("--passphrase-env")
    seal.add_argument("--passphrase-file", type=Path)
    seal.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(seal)
    add_human_decision_arg(seal)
    seal.set_defaults(func=command_seal)

    decrypt = subparsers.add_parser("decrypt-once", help="Decrypt one envelope once on this hardware.")
    decrypt.add_argument("--envelope", required=True, type=Path)
    decrypt.add_argument("--output", required=True, type=Path)
    decrypt.add_argument("--used-dir", type=Path, default=DEFAULT_USED_DIR)
    decrypt.add_argument("--passphrase-env")
    decrypt.add_argument("--passphrase-file", type=Path)
    decrypt.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(decrypt)
    add_human_decision_arg(decrypt)
    decrypt.set_defaults(func=command_decrypt_once)

    self_test = subparsers.add_parser("self-test", help="Run a non-secret local crypto self-test.")
    self_test.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(self_test)
    add_human_decision_arg(self_test)
    self_test.set_defaults(func=command_self_test)

    rescue = subparsers.add_parser("rescue-snapshot", help="Write an AI context-loss rescue snapshot.")
    rescue.add_argument("--output-dir", type=Path, default=DEFAULT_RESCUE_DIR)
    rescue.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    add_local_auth_args(rescue)
    add_human_decision_arg(rescue)
    rescue.set_defaults(func=command_rescue_snapshot)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
