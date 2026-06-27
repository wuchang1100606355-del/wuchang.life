#!/usr/bin/env python3
"""
Canonical 8D verifier.

Production-safe module:
- no hardcoded production secrets
- secrets must be injected by caller
- SQLite nonce ledger path is configurable
- D7 signature binds D1/D2/D4/D8.nonce/D8.timestamp
- audit chain is tamper-evident, not immutable
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


DENY_SECRET_NOT_CONFIGURED = "DENY_SECRET_NOT_CONFIGURED"
DENY_SCHEMA_INVALID = "DENY_SCHEMA_INVALID"
DENY_SCHEMA_INVALID_D8_ENVELOPE = "DENY_SCHEMA_INVALID_D8_ENVELOPE"
DENY_TTL_EXPIRED = "DENY_TTL_EXPIRED"
DENY_D7_SIGNATURE_INVALID = "DENY_D7_SIGNATURE_INVALID"
DENY_REPLAY_ATTACK = "DENY_REPLAY_ATTACK"
QUARANTINE_DENY_BY_DEFAULT = "QUARANTINE_DENY_BY_DEFAULT"
EXEC_POS_ORDER = "EXEC_POS_ORDER"


def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hmac_sha256_hex(secret: bytes, data: str) -> str:
    return hmac.new(secret, data.encode("utf-8"), hashlib.sha256).hexdigest()


def load_secret_from_env(name: str) -> Optional[bytes]:
    value = os.environ.get(name)
    if not value:
        return None
    return value.encode("utf-8")


def canonical_packet_core(payload: Dict[str, Any]) -> str:
    env = payload.get("env_D8") or {}
    return canonical_json({
        "D1": payload.get("delta_D1"),
        "D2": payload.get("ref_D2"),
        "D4": payload.get("delta_D4"),
        "D8_nonce": env.get("nonce"),
        "D8_timestamp": env.get("timestamp"),
    })


def sign_d7_packet(payload_without_or_with_proof: Dict[str, Any], d7_secret: bytes) -> str:
    return hmac_sha256_hex(d7_secret, canonical_packet_core(payload_without_or_with_proof))


def verify_d7_signature(payload: Dict[str, Any], d7_secret: bytes) -> bool:
    supplied = payload.get("proof_D7")
    if not isinstance(supplied, str) or not supplied:
        return False
    expected = sign_d7_packet(payload, d7_secret)
    return hmac.compare_digest(expected, supplied)


class PersistentNonceLedger:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        parent = os.path.dirname(sqlite_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(sqlite_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nonce_ledger (
                nonce TEXT PRIMARY KEY,
                packet_hash TEXT NOT NULL,
                used_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        self.conn.commit()

    def cleanup(self, now: float) -> None:
        self.conn.execute("DELETE FROM nonce_ledger WHERE expires_at < ?", (now,))
        self.conn.commit()

    def mark_used_or_replay(self, nonce: str, packet_hash: str, now: float, ttl_seconds: int) -> bool:
        self.cleanup(now)
        row = self.conn.execute("SELECT 1 FROM nonce_ledger WHERE nonce = ?", (nonce,)).fetchone()
        if row:
            return False
        self.conn.execute(
            "INSERT INTO nonce_ledger(nonce, packet_hash, used_at, expires_at) VALUES (?, ?, ?, ?)",
            (nonce, packet_hash, now, now + ttl_seconds),
        )
        self.conn.commit()
        return True


@dataclass(frozen=True)
class VerifierSecrets:
    d7_secret: bytes
    trajectory_secret: bytes
    audit_secret: bytes
    key_version: str = "local-key-v1"

    def configured(self) -> bool:
        return bool(self.d7_secret and self.trajectory_secret and self.audit_secret)


@dataclass(frozen=True)
class VerifierConfig:
    ttl_seconds: int = 30
    verifier_version: str = "v4.1.0-canonical-8d-d7-nonce-audit-hmac"
    seal_version: str = "canonical-8d-seal-v1"
    external_anchor_ref: Optional[str] = None


class CanonicalTensorDB:
    def __init__(self, trajectory_secret: bytes):
        self.trajectory_secret = trajectory_secret
        self.static_oracle = {
            "intent_order_latte": "wood_task_01",
        }
        self.sparse_tensor_space = {
            (
                "metal_gov_strict::res_pos1",
                "wood_task_01",
                "water_route_local",
                "fire_state_draft::env_verified",
                "earth_id_user1::sig_verified",
            ): EXEC_POS_ORDER
        }

    def map_8d_to_5elements(self, r8d: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
        return (
            f"metal_{r8d.get('D6_Governance')}::{r8d.get('D5_Resource')}",
            self.static_oracle.get(r8d.get("D2_Task_Ref"), "wood_unknown"),
            f"water_{r8d.get('D4_Topology')}",
            f"fire_{r8d.get('D3_State')}::{r8d.get('D8_Envelope')}",
            f"earth_id_{r8d.get('D1_Identity')}::{r8d.get('D7_Verification')}",
        )

    def evaluate(self, tensor_vector: Tuple[str, str, str, str, str]) -> str:
        return self.sparse_tensor_space.get(tensor_vector, QUARANTINE_DENY_BY_DEFAULT)

    def trajectory_hmac(self, tensor_vector: Tuple[str, str, str, str, str]) -> List[str]:
        return [hmac_sha256_hex(self.trajectory_secret, item) for item in tensor_vector]


class Canonical8DVerifier:
    def __init__(self, secrets: VerifierSecrets, nonce_ledger: PersistentNonceLedger, config: Optional[VerifierConfig] = None):
        self.secrets = secrets
        self.nonce_ledger = nonce_ledger
        self.config = config or VerifierConfig()
        self.tensor_db = CanonicalTensorDB(secrets.trajectory_secret if secrets.trajectory_secret else b"")
        self.prev_log_hash = hashlib.sha256(b"TAIJI_GENESIS_BLOCK_0000").hexdigest()
        self.logs: List[Dict[str, Any]] = []
        self.local_cache = {
            "session_offset": "state_draft",
            "allocated_resource": "res_pos1",
            "governance_rule": "gov_strict",
        }

    def verify_payload(self, payload: Dict[str, Any], now: float, packet_hash: str) -> Tuple[str, str]:
        if not self.secrets.configured():
            return DENY_SECRET_NOT_CONFIGURED, "secret_guard"

        required = ["delta_D1", "ref_D2", "delta_D4", "proof_D7", "env_D8"]
        if not all(k in payload for k in required):
            if "env_D8" not in payload:
                return DENY_SCHEMA_INVALID_D8_ENVELOPE, "schema_verifier"
            return DENY_SCHEMA_INVALID, "schema_verifier"

        env = payload.get("env_D8")
        if not isinstance(env, dict):
            return DENY_SCHEMA_INVALID_D8_ENVELOPE, "schema_verifier"

        nonce = env.get("nonce")
        timestamp = env.get("timestamp")
        if not isinstance(nonce, str) or not nonce or not isinstance(timestamp, (int, float)):
            return DENY_SCHEMA_INVALID_D8_ENVELOPE, "schema_verifier"

        if abs(now - float(timestamp)) > self.config.ttl_seconds:
            return DENY_TTL_EXPIRED, "ttl_guard"

        if not verify_d7_signature(payload, self.secrets.d7_secret):
            return DENY_D7_SIGNATURE_INVALID, "d7_signature_guard"

        if not self.nonce_ledger.mark_used_or_replay(nonce, packet_hash, now, self.config.ttl_seconds):
            return DENY_REPLAY_ATTACK, "nonce_guard"

        return "PASS", "formal_verifier"

    def process_transmission(self, payload: Dict[str, Any], now: Optional[float] = None) -> Tuple[str, Dict[str, Any]]:
        current_time = time.time() if now is None else now
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        packet_hash = sha256_hex(canonical_json(payload))

        decision, gate_stage = self.verify_payload(payload, current_time, packet_hash)
        trajectory_hmac: List[str] = []

        if decision == "PASS":
            reconstructed_8d = {
                "D1_Identity": payload.get("delta_D1"),
                "D2_Task_Ref": payload.get("ref_D2"),
                "D3_State": self.local_cache["session_offset"],
                "D4_Topology": payload.get("delta_D4"),
                "D5_Resource": self.local_cache["allocated_resource"],
                "D6_Governance": self.local_cache["governance_rule"],
                "D7_Verification": "sig_verified",
                "D8_Envelope": "env_verified",
            }
            tensor_vector = self.tensor_db.map_8d_to_5elements(reconstructed_8d)
            trajectory_hmac = self.tensor_db.trajectory_hmac(tensor_vector)
            decision = self.tensor_db.evaluate(tensor_vector)
            gate_stage = "tensor_collapse"

        log_core = canonical_json({
            "run_id": run_id,
            "packet_hash": packet_hash,
            "trajectory_hmac": trajectory_hmac,
            "collapse_result": decision,
            "gate_stage": gate_stage,
            "prev_log_hash": self.prev_log_hash,
            "verifier_version": self.config.verifier_version,
            "key_version": self.secrets.key_version,
            "created_at": current_time,
        })
        log_hash = sha256_hex(log_core)
        log_hmac = hmac_sha256_hex(self.secrets.audit_secret, log_hash) if self.secrets.audit_secret else ""

        audit_log = {
            "run_id": run_id,
            "packet_hash": packet_hash,
            "trajectory_hmac": trajectory_hmac,
            "collapse_result": decision,
            "verifier_version": self.config.verifier_version,
            "prev_log_hash": self.prev_log_hash,
            "log_hash": log_hash,
            "log_hmac": log_hmac,
            "key_version": self.secrets.key_version,
            "gate_stage": gate_stage,
            "seal_version": self.config.seal_version,
            "external_anchor_ref": self.config.external_anchor_ref,
            "created_at": current_time,
        }

        self.prev_log_hash = log_hash
        self.logs.append(audit_log)
        return decision, audit_log

    def verify_audit_chain(self, logs: List[Dict[str, Any]]) -> bool:
        prev = hashlib.sha256(b"TAIJI_GENESIS_BLOCK_0000").hexdigest()
        for log in logs:
            log_core = canonical_json({
                "run_id": log["run_id"],
                "packet_hash": log["packet_hash"],
                "trajectory_hmac": log["trajectory_hmac"],
                "collapse_result": log["collapse_result"],
                "gate_stage": log["gate_stage"],
                "prev_log_hash": prev,
                "verifier_version": log["verifier_version"],
                "key_version": log["key_version"],
                "created_at": log["created_at"],
            })
            expected_hash = sha256_hex(log_core)
            expected_hmac = hmac_sha256_hex(self.secrets.audit_secret, expected_hash) if self.secrets.audit_secret else ""
            if log.get("prev_log_hash") != prev:
                return False
            if not hmac.compare_digest(expected_hash, log.get("log_hash", "")):
                return False
            if not hmac.compare_digest(expected_hmac, log.get("log_hmac", "")):
                return False
            prev = expected_hash
        return True
