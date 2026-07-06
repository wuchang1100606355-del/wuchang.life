#!/usr/bin/env python3
import copy
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.taiji_8d_canonical_verifier import (
    Canonical8DVerifier,
    PersistentNonceLedger,
    VerifierSecrets,
    VerifierConfig,
    sign_d7_packet,
    ALLOW,
    BLOCK,
    DENY_REPLAY_ATTACK,
    DENY_TTL_EXPIRED,
    DENY_D7_SIGNATURE_INVALID,
    DENY_SCHEMA_INVALID_D8_ENVELOPE,
)
from tools.intent_field.adi_5d_absolute_index_verifier import base_pass_packet as base_adi_5d_packet

D7_SECRET = b"dummy-d7-secret-for-test-only"
TRAJ_SECRET = b"dummy-trajectory-secret-for-test-only"
AUDIT_SECRET = b"dummy-audit-secret-for-test-only"


def make_verifier(sqlite_path):
    secrets = VerifierSecrets(
        d7_secret=D7_SECRET,
        trajectory_secret=TRAJ_SECRET,
        audit_secret=AUDIT_SECRET,
        key_version="test-key-v1",
    )
    ledger = PersistentNonceLedger(sqlite_path)
    config = VerifierConfig(ttl_seconds=30)
    return Canonical8DVerifier(secrets=secrets, nonce_ledger=ledger, config=config)


def make_payload(now, nonce, task="intent_order_latte"):
    payload = {
        "delta_D1": "user1",
        "ref_D2": task,
        "delta_D4": "route_local",
        "env_D8": {
            "nonce": nonce,
            "timestamp": now,
        },
        "adi_5d_absolute_index": base_adi_5d_packet(),
    }
    payload["proof_D7"] = sign_d7_packet(payload, D7_SECRET)
    return payload


def assert_eq(name, got, want):
    if got != want:
        raise AssertionError(f"{name}: got={got} want={want}")
    print(f"PASS {name}={got}")


def main():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "nonce.sqlite3")
        now = time.time()

        verifier = make_verifier(db)

        valid = make_payload(now, "nonce-valid")
        decision, _ = verifier.process_transmission(valid, now=now)
        assert_eq("VALID_PACKET", decision, ALLOW)

        restarted = make_verifier(db)
        decision, _ = restarted.process_transmission(valid, now=now + 1)
        assert_eq("REPLAY_AFTER_RESTART", decision, DENY_REPLAY_ATTACK)

        expired = make_payload(now - 100, "nonce-expired")
        decision, _ = verifier.process_transmission(expired, now=now)
        assert_eq("EXPIRED_PACKET", decision, DENY_TTL_EXPIRED)

        bad_sig = make_payload(now, "nonce-bad-sig")
        bad_sig["proof_D7"] = "bad"
        decision, _ = verifier.process_transmission(bad_sig, now=now)
        assert_eq("BAD_SIGNATURE", decision, DENY_D7_SIGNATURE_INVALID)

        missing_d8 = {
            "delta_D1": "user1",
            "ref_D2": "intent_order_latte",
            "delta_D4": "route_local",
            "proof_D7": "bad",
        }
        decision, _ = verifier.process_transmission(missing_d8, now=now)
        assert_eq("MISSING_D8", decision, DENY_SCHEMA_INVALID_D8_ENVELOPE)

        unknown = make_payload(now, "nonce-unknown", task="intent_unknown")
        decision, _ = verifier.process_transmission(unknown, now=now)
        assert_eq("UNKNOWN_TASK", decision, BLOCK)

        if not verifier.verify_audit_chain(verifier.logs):
            raise AssertionError("AUDIT_CHAIN_VERIFY failed")
        print("PASS AUDIT_CHAIN_VERIFY=PASS")

        tampered = copy.deepcopy(verifier.logs)
        tampered[0]["collapse_result"] = "EXEC_TAMPERED"
        if verifier.verify_audit_chain(tampered):
            raise AssertionError("TAMPERED_LOG should break chain")
        print("PASS TAMPERED_LOG=HASH_CHAIN_BREAK")

        logs_text = str(verifier.logs)
        for forbidden in [
            "dummy-d7-secret",
            "dummy-trajectory-secret",
            "dummy-audit-secret",
            "intent_order_latte",
            "route_local",
        ]:
            if forbidden in logs_text:
                raise AssertionError(f"forbidden leak found: {forbidden}")

        print("PASS SECRET_PRINT=FALSE")
        print("PASS PLAINTEXT_STORAGE=FALSE")


if __name__ == "__main__":
    main()
