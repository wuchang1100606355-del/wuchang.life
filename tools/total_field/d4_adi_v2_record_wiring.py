from pathlib import Path
from typing import Mapping, Any
import hashlib
import json
from core.adi_native.evidence_ledger import VerifiableSpacetimeSystem

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def append_fact(ledger: VerifiableSpacetimeSystem, *, event_id: str, action: str, actor_ref: str, accountable_person_ref: str, result: str):
    return ledger.append_event(
        "W7TP_FACT",
        {"event_id": event_id, "action": action, "result": result},
        actor_ref=actor_ref,
        accountable_person_ref=accountable_person_ref,
    )

def append_privacy_access(ledger: VerifiableSpacetimeSystem, *, request_id: str, requester_ref: str, accountable_person_ref: str, authority_ref: str, purpose: str, disclosed_fields: list[str], result: str):
    allowed = {
        "building", "floor", "unit", "masked_name",
        "masked_id", "birth_year_month", "contact_phone"
    }
    if not disclosed_fields or not set(disclosed_fields) <= allowed:
        raise ValueError("FIELD_SCOPE_INVALID")
    if not authority_ref or not purpose:
        raise ValueError("AUTHORITY_OR_PURPOSE_MISSING")
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

def verify(ledger: VerifiableSpacetimeSystem):
    valid, reason = ledger.verify_chain()
    if not valid:
        raise ValueError("EVIDENCE_CHAIN_INVALID:" + reason)
    return {"state": "PASS", "reason": reason}
