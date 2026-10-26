from __future__ import annotations
from typing import Iterable
from core.adi_native.evidence_ledger import VerifiableSpacetimeSystem


def append_fact(
    ledger: VerifiableSpacetimeSystem,
    *,
    fact_id: str,
    fact_type: str,
    payload_sha256: str,
    source_ref: str,
    actor_ref: str,
    accountable_person_ref: str,
):
    return ledger.append_event(
        "W7TP_FACT_OBSERVED",
        {
            "fact_id": fact_id,
            "fact_type": fact_type,
            "payload_sha256": payload_sha256,
            "source_ref": source_ref,
        },
        actor_ref=actor_ref,
        accountable_person_ref=accountable_person_ref,
    )


def append_privacy_access(
    ledger: VerifiableSpacetimeSystem,
    *,
    request_id: str,
    requester_ref: str,
    accountable_person_ref: str,
    authority_ref: str,
    purpose: str,
    disclosed_fields: Iterable[str],
    result: str,
):
    return ledger.append_event(
        "W7TP_PRIVACY_ACCESS",
        {
            "request_id": request_id,
            "authority_ref": authority_ref,
            "purpose": purpose,
            "disclosed_fields": sorted(set(disclosed_fields)),
            "result": result,
            "contains_member_plaintext": False,
        },
        actor_ref=requester_ref,
        accountable_person_ref=accountable_person_ref,
    )


def verify(ledger: VerifiableSpacetimeSystem) -> dict[str, str]:
    valid, reason = ledger.verify_chain()
    if not valid:
        return {"state": "BLOCK_LEDGER_CHAIN_BROKEN", "reason": reason}
    return {"state": "PASS_LEDGER_VERIFIED", "reason": reason}
