from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contract import DECISION_SCHEMA, LOCAL_AUTH_MIN_LENGTH
from .foundation import sha256_bytes, utc_now, write_json
from .hardware import hardware_fingerprint


def append_audit(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts", utc_now())
    event.setdefault("actor", "system_total_probe")
    event.setdefault("secret_material_printed", False)
    event.setdefault("raw_hardware_printed", False)
    event.setdefault("external_api_called", False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


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
