from __future__ import annotations
from typing import Iterable
from core.adi_native.evidence_ledger import VerifiableSpacetimeSystem

ALLOWED_DISCLOSED_FIELDS = frozenset({
    "masked_id",
    "masked_phone",
    "phone_last3_hash",
    "member_ref_hash",
    "entitlement_scope",
    "voucher_balance_after",
})

CANONICAL_STAGE_NODES = frozenset({
    "taiji01",
    "MSI",
    "taiji02",
    "taiji03",
    "taiji04",
})


def append_fact(
    ledger: VerifiableSpacetimeSystem,
    *,
    fact_id: str | None = None,
    fact_type: str | None = None,
    payload_sha256: str | None = None,
    source_ref: str | None = None,
    event_id: str | None = None,
    action: str | None = None,
    result: str | None = None,
    actor_ref: str,
    accountable_person_ref: str,
):
    resolved_id = (fact_id or event_id or "").strip()
    resolved_type = (fact_type or action or "").strip()
    if not resolved_id or not resolved_type or not actor_ref.strip() or not accountable_person_ref.strip():
        raise ValueError("append_fact requires non-empty fact_id/event_id, fact_type/action, actor_ref, and accountable_person_ref")
    payload = {
        "fact_id": resolved_id,
        "event_id": resolved_id,
        "fact_type": resolved_type,
        "action": resolved_type,
        "payload_sha256": payload_sha256 or ("0" * 64),
        "source_ref": source_ref or "d4_record_wiring",
        "result": result or "PASS",
        "contains_member_plaintext": False,
    }
    return ledger.append_event(
        "W7TP_FACT",
        payload,
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
    fields = sorted(set(disclosed_fields or []))
    if not fields:
        raise ValueError("disclosed_fields must not be empty")
    disallowed = [f for f in fields if not isinstance(f, str) or f not in ALLOWED_DISCLOSED_FIELDS]
    if disallowed:
        raise ValueError(f"disallowed or plaintext disclosed_fields rejected: {disallowed!r}")
    return ledger.append_event(
        "W7TP_PRIVACY_ACCESS",
        {
            "request_id": request_id,
            "authority_ref": authority_ref,
            "purpose": purpose,
            "disclosed_fields": fields,
            "result": result,
            "contains_member_plaintext": False,
        },
        actor_ref=requester_ref,
        accountable_person_ref=accountable_person_ref,
    )


def append_stage_avatar_dispatch(
    ledger: VerifiableSpacetimeSystem,
    *,
    request_id: str,
    authority_ref: str,
    actor_ref: str,
    accountable_person_ref: str,
    avatar_asset_path: str,
    target_node: str,
    target_pid: int | None,
    result: str,
):
    if (
        not str(request_id or "").strip()
        or not str(authority_ref or "").strip()
        or not str(actor_ref or "").strip()
        or not str(accountable_person_ref or "").strip()
        or not str(avatar_asset_path or "").strip()
        or not str(result or "").strip()
    ):
        raise ValueError("append_stage_avatar_dispatch missing required non-empty fields")
    if target_node not in CANONICAL_STAGE_NODES:
        raise ValueError(f"target_node {target_node!r} not in canonical 5-node whitelist")
    if target_pid is not None and (not isinstance(target_pid, int) or target_pid <= 0):
        raise ValueError("target_pid must be a positive integer or None")
    return ledger.append_event(
        "W7TP_STAGE_AVATAR_DISPATCH",
        {
            "request_id": request_id,
            "authority_ref": authority_ref,
            "avatar_asset_path": avatar_asset_path,
            "target_node": target_node,
            "target_pid": target_pid,
            "result": result,
            "contains_member_plaintext": False,
        },
        actor_ref=actor_ref,
        accountable_person_ref=accountable_person_ref,
    )


def verify(ledger: VerifiableSpacetimeSystem) -> dict[str, str]:
    valid, reason = ledger.verify_chain()
    if not valid:
        raise ValueError(f"BLOCK_LEDGER_CHAIN_BROKEN: {reason}")
    return {"state": "PASS", "ledger_state": "PASS_LEDGER_VERIFIED", "reason": reason}
