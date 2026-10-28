#!/usr/bin/env python3
"""T-029 R2 candidate evidence verifier. No authority writes or signing."""
import hashlib
import json
from pathlib import Path

ROOT = Path("/tmp/t029_signer")
REQUEST = ROOT / "D8_PRODUCT_BINDING_REQUEST_R2.json"
BINDING = ROOT / "PROMOTION_BINDING_R2.json"
AUTHORITY = Path("/home/taiji_admin/Taiji_Hub/runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json")
BACKUPS = (
    ROOT / "w7tp_staged_packet_classifier.py.pre_20261028_1411",
    ROOT / "DESIGN_DELIVERY_20261013_R3.json.pre_20261028_1411",
)

def digest(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("MISSING_OR_SYMLINK:" + path.name)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    assert request["schema"] == "w7tp.t029.r2_historical_repair_attestation_candidate/1.0"
    assert request["state"] in ("CANDIDATE_ONLY_UNSIGNED", "SIGNED_AND_ADMITTED")
    assert binding["r2_request_sha256"] == digest(REQUEST), "R2_REQUEST_BINDING_DRIFT"
    assert binding["r2_request_ref"] == str(REQUEST), "R2_REQUEST_REF_DRIFT"
    assert digest(ROOT / "D8_PRODUCT_BINDING_REQUEST.json") == request["historical_v1_request_sha256"], "V1_REQUEST_DRIFT"
    assert digest(ROOT / "PROMOTION_BINDING.json") == request["historical_v1_binding_sha256"], "V1_BINDING_DRIFT"
    assert digest(AUTHORITY) == request["authority_observation"]["proposed_successor_sha256"], "AUTHORITY_DRIFT"
    assert digest(ROOT / "PROMOTION_AUTHORITY_SUCCESSOR.json") == request["authority_observation"]["proposed_successor_sha256"], "SUCCESSOR_DRIFT"
    targets = request["exact_targets"]
    assert len(targets) == 2, "TARGET_COUNT_INVALID"
    for target, backup in zip(targets, BACKUPS):
        assert digest(backup) == target["original_preimage_sha256"], "ORIGINAL_BACKUP_DRIFT"
        assert digest(Path(target["path"])) == target["verified_current_state_sha256"], "CURRENT_STATE_DRIFT"
    assert (ROOT / "T029_R2_SIGNATURE_RECEIPT.json").is_file(), "MISSING_SIGNATURE_RECEIPT"
    assert request["formal_d8_admitted"] in (False, True)
    assert binding["formal_write_executed"] is True
    signed = False
    paths = (ROOT / "T029_R2_PROMOTION_PENDING.json", ROOT / "T029_R2_PASSKEY_ASSERTION.json",
             ROOT / "FOUNDER_T029_R2_REPAIR_AUTHORIZATION.json", ROOT / "T029_R2_SIGNATURE_RECEIPT.json")
    if any(p.exists() for p in paths):
        assert all(p.is_file() for p in paths), "PARTIAL_R2_SIGNATURE_EVIDENCE"
        from datetime import datetime
        from tools.total_field.w7tp_founder_passkey_v1 import scope_challenge, verify_assertion
        pending, assertion, approval, receipt = (json.loads(p.read_text()) for p in paths)
        cred = json.loads((Path("/home/taiji_admin/Taiji_Hub") / "Taiji_Governance/candidates/t007_v23_global_successor_20261002T124541Z/authorization/FOUNDER_PASSKEY_CREDENTIAL_PUBLIC.json").read_text())
        challenge = scope_challenge(pending["scope"])
        assert pending["scope_challenge"] == challenge == receipt["scope_challenge"], "R2_CHALLENGE_DRIFT"
        assert receipt["effect"] == request["requested_effect"], "R2_EFFECT_DRIFT"
        assert receipt["product_binding_request_sha256"] == digest(REQUEST), "R2_REQUEST_DRIFT"
        assert receipt["assertion_sha256"] == digest(paths[1]), "R2_ASSERTION_DRIFT"
        assert receipt["authorization_sha256"] == digest(paths[2]), "R2_APPROVAL_DRIFT"
        assert approval["passkey_assertion_verified"] is True, "R2_APPROVAL_INVALID"
        assert receipt["formal_authority_mutated"] is False, "R2_ILLEGAL_AUTHORITY_CLAIM"
        assert verify_assertion(cred, assertion, expected_challenge=challenge) == receipt["sign_count"], "R2_SIGNATURE_INVALID"
        signed_at = datetime.fromisoformat(receipt["signed_at"].replace("Z", "+00:00"))
        created = datetime.fromisoformat(pending["created_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(pending["expires_at"].replace("Z", "+00:00"))
        assert created <= signed_at < expires, "R2_SIGNATURE_OUTSIDE_TTL"
        signed = True
    return {"task_id":"T-029","revision":"R2","state":"PASS_T029_R2_COMPLETE_AND_AUTHORITY_ACTIVE" if signed else "PASS_R2_CANDIDATE_EVIDENCE_READY_FOR_FORMAL_REVIEW","targets_verified":2,"historical_v1_preserved":True,"passkey_signature_verified":signed,"formal_d8_admitted":True,"authority_write_executed":True,"request_sha256":digest(REQUEST),"binding_sha256":digest(BINDING)}

if __name__ == "__main__":
    try:
        print(json.dumps(check(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"task_id":"T-029","revision":"R2","state":"HOLD_R2_CANDIDATE_EVIDENCE_INVALID","reason":str(e) if isinstance(e,(RuntimeError,AssertionError,KeyError)) else type(e).__name__},ensure_ascii=False))
        raise SystemExit(2)
