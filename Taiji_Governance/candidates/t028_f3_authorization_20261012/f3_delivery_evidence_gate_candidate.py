#!/usr/bin/env python3
"""Isolated T-028 F3 evidence gate. NOT an installation or D8 authorization gate.

Purpose: preserve one existing ACTION_ID and reject every unsigned, stale,
replayed-across-nodes or locally asserted ALLOW receipt as proof of trusted
issuance. No new authority root, key minting, or production integration.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

EXPECTED_TASK = "T-028"
EXPECTED_ACTION = "A-T028-F3-AUTHDELIVERY-TAIJI01-20261012-001"
EXPECTED_NODE = "taiji01"
EXPECTED_DEVICE_REF = "RemoteDesktop:0a8cb96c-0944-459c-9af3-bc2aeb70aacf"
EXPECTED_F3 = "F3_TRUSTED_AUTHORIZATION_DELIVERY_NOT_VERIFIED"
REQUIRED_STOP = ("F3", "F4", "F5")
REQUIRED_AUTHORITY_PROOFS = (
    "trusted_issuer_identity_proven_by_existing_D8",
    "founder_sealed_root_and_dual_factor_verified",
    "signed_exact_ACTION_ID_and_payload_and_receiver",
    "issuer_signature_verified_against_independently_trusted_key",
    "fresh_single_use_nonce_and_expiry_enforced",
    "receiver_local_identity_and_delivery_acknowledged",
    "F4_F5_acceptance_separately_recorded",
)

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        time = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return time.astimezone(timezone.utc) if time.tzinfo else None

def audit(
    contract: Mapping[str, Any],
    *,
    observed_manifest_sha256: str,
    observed_payload_sha256: str,
    receiver_node: str = EXPECTED_NODE,
    now: datetime | None = None,
    claimed_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate evidence only. This cannot grant install/enable authority."""
    reasons: list[str] = []
    if not isinstance(contract, Mapping):
        return {"decision": "BLOCK", "reasons": ["BLOCK_CONTRACT_OBJECT_REQUIRED"], "authority_effect": "NONE"}
    unsigned = {key: val for key, val in contract.items() if key != "candidate_sha256"}
    if hashlib.sha256(canonical(unsigned)).hexdigest() != contract.get("candidate_sha256"):
        reasons.append("BLOCK_F3_CONTRACT_SELF_HASH_MISMATCH")
    if contract.get("ACTION_ID") != EXPECTED_ACTION or contract.get("TASK_ID") != EXPECTED_TASK:
        reasons.append("BLOCK_F3_ACTION_OR_TASK_MISMATCH")
    if contract.get("candidate_only") is not True or contract.get("signable_release") is not False:
        reasons.append("BLOCK_F3_AUTHORITY_OVERCLAIM")
    if contract.get("state") != "HOLD_F3_F4_F5_NO_EXECUTION":
        reasons.append("BLOCK_F3_CANDIDATE_STATE_MISMATCH")
    source = contract.get("source") if isinstance(contract.get("source"), Mapping) else {}
    for field, observed in (("manifest_sha256", observed_manifest_sha256), ("payload_sha256", observed_payload_sha256)):
        if source.get(field) != observed or not isinstance(observed, str) or len(observed) != 64:
            reasons.append("BLOCK_F3_PACKAGE_" + field.upper() + "_MISMATCH")
    target = contract.get("target") if isinstance(contract.get("target"), Mapping) else {}
    if (target.get("authority_node") != EXPECTED_NODE
        or target.get("receiver_node") != EXPECTED_NODE
        or target.get("receiver_device_ref") != EXPECTED_DEVICE_REF
        or receiver_node != EXPECTED_NODE):
        reasons.append("BLOCK_F3_RECEIVER_SCOPE_MISMATCH")
    stop = contract.get("stop_conditions") if isinstance(contract.get("stop_conditions"), Mapping) else {}
    if any(not isinstance(stop.get(key), str) or not stop[key] for key in REQUIRED_STOP):
        reasons.append("BLOCK_F3_F4_F5_STOP_CONDITIONS_MISSING")
    authority = contract.get("authority") if isinstance(contract.get("authority"), Mapping) else {}
    if (authority.get("decision") != "HOLD"
        or authority.get("authority_effect") != "NONE"
        or authority.get("founder_approval_received") is not False
        or authority.get("trusted_delivery_channel_verified") is not False):
        reasons.append("BLOCK_F3_UNVERIFIED_AUTHORITY_CLAIM")
    created = _parse_time(contract.get("created_at_utc"))
    expires = _parse_time(contract.get("review_expires_at_utc"))
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None or not created or not expires or not created <= moment <= expires:
        reasons.append("HOLD_F3_CANDIDATE_EXPIRED_OR_INVALID_TIME")
    # A receipt can contain self-declared ALLOW without authentic issuance;
    # the current legacy package verifier has demonstrated acceptance of it.
    # Never treat this assertion as proof. All trust proofs remain external.
    if claimed_receipt is not None:
        reasons.append("HOLD_F3_UNTRUSTED_RECEIPT_CLAIM_NOT_AUTHORITY")
    reasons.extend([
        "HOLD_F3_ISSUER_TRUST_PROVENANCE_UNVERIFIED",
        "HOLD_F3_SIGNATURE_AND_NONCE_NOT_VERIFIED",
        "HOLD_F3_RECEIVER_LOCAL_DELIVERY_NOT_VERIFIED",
        "HOLD_F4_F5_SEPARATE_GATES_STILL_OPEN",
    ])
    return {
        "schema_version": "W7TP_T028_F3_RECEIPT_EVIDENCE_GATE_CANDIDATE/1.0",
        "ACTION_ID": EXPECTED_ACTION,
        "decision": "BLOCK" if any(x.startswith("BLOCK") for x in reasons) else "HOLD",
        "structural_candidate_pass": not any(x.startswith("BLOCK") or x.startswith("HOLD_F3_CANDIDATE_EXPIRED") for x in reasons),
        "reasons": reasons,
        "required_trust_proofs": list(REQUIRED_AUTHORITY_PROOFS),
        "legacy_receipt_is_authority": False,
        "verified_F3_closure": False,
        "signable_release": False,
        "effects": {"install": False, "enable": False, "deploy": False, "d8_decision": "UNCHANGED"},
        "authority_effect": "NONE",
    }

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--manifest-sha256", required=True)
    ap.add_argument("--payload-sha256", required=True)
    ap.add_argument("--receiver-node", default=EXPECTED_NODE)
    args = ap.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    result = audit(contract, observed_manifest_sha256=args.manifest_sha256,
                   observed_payload_sha256=args.payload_sha256, receiver_node=args.receiver_node)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["decision"] == "HOLD" and result["structural_candidate_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
