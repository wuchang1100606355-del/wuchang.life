"""Pure product-grade contracts for the Liaoguo sovereign voucher sandbox.

No Odoo imports and no side effects.  The contract keeps the clerk capability
seat, masked member projection, member disposal authority, and transaction
evidence separate while expressing them as one coupled 8D ADI V2.3 field.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any, Mapping


SCHEMA = "W7TP_LIAOGUO_SOVEREIGN_VOUCHER_CHECKOUT_V1"
V23_DIMENSIONS = (
    "D1_INTENT",
    "D2_STATE",
    "D3_COORDINATE",
    "D4_EVIDENCE",
    "D5_EXECUTION_POLICY",
    "D6_GENERATIVE_STATE_TRANSMISSION",
    "D7_RISK_ISOLATION",
    "D8_ENVELOPE_AUTHORITY",
)
COUPLING_RULE = "ONE_COUPLED_DYNAMIC_STATE_FIELD_NOT_PIPELINE"
NON_DIFFERENTIAL_SEMANTICS = "NON_DIFFERENTIAL_POINTER_FIRST_STATE_RECONSTRUCTION"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HASH_REF = re.compile(r"^[a-z][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")
_LAST3 = re.compile(r"^\d{3}$")


class SovereignCheckoutHold(ValueError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def hash_ref(prefix: str, value: Any) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_.-]*", prefix):
        raise SovereignCheckoutHold("HOLD_HASH_REF_PREFIX_INVALID")
    return f"{prefix}:sha256:{canonical_sha256(value)}"


def _require_text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SovereignCheckoutHold(code)
    return value.strip()


def _require_sha256(value: Any, code: str) -> str:
    value = _require_text(value, code).lower()
    if _SHA256.fullmatch(value) is None:
        raise SovereignCheckoutHold(code)
    return value


def _require_hash_ref(value: Any, code: str) -> str:
    value = _require_text(value, code)
    if _HASH_REF.fullmatch(value) is None:
        raise SovereignCheckoutHold(code)
    return value


def phone_last3_hmac(*, organization_ref: str, last_three: str, pepper: str) -> str:
    organization_ref = _require_text(organization_ref, "HOLD_ORGANIZATION_REF_REQUIRED")
    last_three = _require_text(last_three, "HOLD_PHONE_LAST3_REQUIRED")
    if _LAST3.fullmatch(last_three) is None:
        raise SovereignCheckoutHold("HOLD_PHONE_LAST3_FORMAT_INVALID")
    if not isinstance(pepper, str) or len(pepper) < 32:
        raise SovereignCheckoutHold("HOLD_PHONE_LOOKUP_PEPPER_INVALID")
    message = f"{organization_ref}|{last_three}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), message, hashlib.sha256).hexdigest()


def phone_last3_matches(
    *,
    stored_digest: str,
    organization_ref: str,
    last_three: str,
    pepper: str,
) -> bool:
    stored_digest = _require_sha256(
        stored_digest,
        "HOLD_PHONE_LOOKUP_DIGEST_INVALID",
    )
    candidate = phone_last3_hmac(
        organization_ref=organization_ref,
        last_three=last_three,
        pepper=pepper,
    )
    return hmac.compare_digest(stored_digest, candidate)


def build_lookup_receipt(
    *,
    organization_ref: str,
    seat_ref: str,
    issued_at: str,
    matched: bool,
    ambiguous: bool = False,
    member_ref: str = "",
    masked_display: str = "",
    entitlement_count: int | None = None,
) -> dict[str, Any]:
    organization_ref = _require_text(organization_ref, "HOLD_ORGANIZATION_REF_REQUIRED")
    seat_ref = _require_hash_ref(seat_ref, "HOLD_SEAT_REF_INVALID")
    issued_at = _require_text(issued_at, "HOLD_LOOKUP_TIME_REQUIRED")
    if ambiguous and matched:
        raise SovereignCheckoutHold("HOLD_LOOKUP_MATCH_AMBIGUOUS")
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "event": "LOW_RISK_MEMBER_LOOKUP",
        "organization_ref": organization_ref,
        "seat_ref": seat_ref,
        "issued_at": issued_at,
        "matched": bool(matched),
        "ambiguous": bool(ambiguous),
        "phone_last3_disclosed": False,
        "phone_plaintext_disclosed": False,
        "identity_authentication": False,
        "checkout_consent": False,
    }
    if matched and not ambiguous:
        body.update(
            {
                "member_ref": _require_text(member_ref, "HOLD_MEMBER_REF_REQUIRED"),
                "masked_display": _require_text(
                    masked_display,
                    "HOLD_MASKED_DISPLAY_REQUIRED",
                ),
                "entitlement_count": int(entitlement_count or 0),
            }
        )
    else:
        body["entitlement_state"] = "WITHHELD_UNTIL_UNAMBIGUOUS_MATCH"
    body["receipt_hash"] = canonical_sha256(body)
    return body


def build_red_tea_redeem_request(
    *,
    lookup_receipt: Mapping[str, Any],
    sandbox_member_ref: str,
    sandbox_organization_ref: str,
    sandbox_product_ref: str,
    voucher_ref: str,
    voucher_hash: str,
    order_ref: str,
    issued_at: str,
) -> dict[str, Any]:
    member_ref = _require_text(
        lookup_receipt.get("member_ref"),
        "HOLD_MATCHED_MEMBER_REF_REQUIRED",
    )
    organization_ref = _require_text(
        lookup_receipt.get("organization_ref"),
        "HOLD_ORGANIZATION_REF_REQUIRED",
    )
    seat_ref = _require_hash_ref(
        lookup_receipt.get("seat_ref"),
        "HOLD_SEAT_REF_INVALID",
    )
    if lookup_receipt.get("matched") is not True or lookup_receipt.get("ambiguous"):
        raise SovereignCheckoutHold("HOLD_LOW_RISK_LOOKUP_NOT_MATCHED")
    if member_ref != _require_text(sandbox_member_ref, "HOLD_SANDBOX_MEMBER_REF_REQUIRED"):
        raise SovereignCheckoutHold("HOLD_SANDBOX_MEMBER_SCOPE_MISMATCH")
    if organization_ref != _require_text(
        sandbox_organization_ref,
        "HOLD_SANDBOX_ORGANIZATION_REF_REQUIRED",
    ):
        raise SovereignCheckoutHold("HOLD_SANDBOX_ORGANIZATION_SCOPE_MISMATCH")
    product_ref = _require_text(
        sandbox_product_ref,
        "HOLD_SANDBOX_PRODUCT_REF_REQUIRED",
    )
    voucher_ref = _require_text(voucher_ref, "HOLD_VOUCHER_REF_REQUIRED")
    voucher_hash = _require_sha256(voucher_hash, "HOLD_VOUCHER_HASH_INVALID")
    order_ref = _require_text(order_ref, "HOLD_ORDER_REF_REQUIRED")
    issued_at = _require_text(issued_at, "HOLD_REQUEST_TIME_REQUIRED")
    if int(lookup_receipt.get("entitlement_count") or 0) != 10:
        raise SovereignCheckoutHold("HOLD_SANDBOX_REQUIRES_EXACT_10_TO_9_PREIMAGE")

    field = {
        "schema": SCHEMA,
        "coupling_rule": COUPLING_RULE,
        "D1_INTENT": {
            "intent": "REDEEM_ONE_LIAOGUO_RED_TEA_VOUCHER",
            "quantity": 1,
        },
        "D2_STATE": {
            "state": "PENDING_OWNER_CONFIRMATION",
            "voucher_count_before": int(lookup_receipt["entitlement_count"]),
        },
        "D3_COORDINATE": {
            "organization_ref": organization_ref,
            "member_ref": member_ref,
            "seat_ref": seat_ref,
            "order_ref": order_ref,
            "product_ref": product_ref,
        },
        "D4_EVIDENCE": {
            "lookup_receipt_hash": _require_sha256(
                lookup_receipt.get("receipt_hash"),
                "HOLD_LOOKUP_RECEIPT_HASH_INVALID",
            ),
            "voucher_ref": voucher_ref,
            "voucher_preimage_hash": voucher_hash,
        },
        "D5_EXECUTION_POLICY": {
            "clerk_may_request": True,
            "clerk_may_redeem": False,
            "member_confirmation_required": True,
            "voucher_use_quantity": 1,
        },
        "D6_GENERATIVE_STATE_TRANSMISSION": {
            "semantic_class": NON_DIFFERENTIAL_SEMANTICS,
            "predecessor_state_required": False,
            "differential_payload_bytes": 0,
            "member_plaintext_transmitted": False,
            "phone_plaintext_transmitted": False,
        },
        "D7_RISK_ISOLATION": {
            "sandbox_only": True,
            "cross_member": False,
            "cross_organization": False,
            "happiness_coin_effect": False,
            "other_product_effect": False,
            "fail_closed": True,
        },
        "D8_ENVELOPE_AUTHORITY": {
            "member_disposal_authority_required": True,
            "staff_is_not_member_disposal_authority": True,
            "ai_is_not_member_disposal_authority": True,
            "candidate_until_member_confirmation": True,
        },
        "issued_at": issued_at,
    }
    field["request_hash"] = canonical_sha256(field)
    return field


def build_owner_confirmation(
    *,
    request_packet: Mapping[str, Any],
    confirmer_member_ref: str,
    confirmation_ref: str,
    decision: str,
    confirmed_at: str,
) -> dict[str, Any]:
    request_hash = _require_sha256(
        request_packet.get("request_hash"),
        "HOLD_REQUEST_HASH_INVALID",
    )
    member_ref = _require_text(
        request_packet.get("D3_COORDINATE", {}).get("member_ref"),
        "HOLD_REQUEST_MEMBER_REF_REQUIRED",
    )
    if _require_text(confirmer_member_ref, "HOLD_CONFIRMER_MEMBER_REF_REQUIRED") != member_ref:
        raise SovereignCheckoutHold("HOLD_CROSS_MEMBER_CONFIRMATION")
    confirmation_ref = _require_hash_ref(
        confirmation_ref,
        "HOLD_MEMBER_CONFIRMATION_REF_INVALID",
    )
    if decision not in {"CONSENT", "DENY"}:
        raise SovereignCheckoutHold("HOLD_MEMBER_CONFIRMATION_DECISION_INVALID")
    payload = {
        "schema": SCHEMA,
        "event": "OWNER_CONFIRMATION",
        "request_hash": request_hash,
        "member_ref": member_ref,
        "confirmation_ref": confirmation_ref,
        "decision": decision,
        "confirmed_at": _require_text(confirmed_at, "HOLD_CONFIRMATION_TIME_REQUIRED"),
        "authority": "NATURAL_PERSON_MEMBER",
        "one_time": True,
    }
    payload["confirmation_hash"] = canonical_sha256(payload)
    return payload


def build_transaction_evidence(
    *,
    request_packet: Mapping[str, Any],
    confirmation: Mapping[str, Any],
    voucher_count_before: int,
    voucher_count_after: int,
    voucher_hash_before: str,
    voucher_hash_after: str,
    executed_at: str,
    executor_ref: str,
) -> dict[str, Any]:
    request_hash = _require_sha256(
        request_packet.get("request_hash"),
        "HOLD_REQUEST_HASH_INVALID",
    )
    if confirmation.get("decision") != "CONSENT":
        raise SovereignCheckoutHold("HOLD_MEMBER_CONSENT_REQUIRED")
    if confirmation.get("request_hash") != request_hash:
        raise SovereignCheckoutHold("HOLD_CONFIRMATION_REQUEST_MISMATCH")
    before = int(voucher_count_before)
    after = int(voucher_count_after)
    if before != 10 or after != 9:
        raise SovereignCheckoutHold("HOLD_SANDBOX_REQUIRES_EXACT_10_TO_9_EFFECT")
    evidence = {
        "schema": SCHEMA,
        "event": "VOUCHER_REDEEM_EFFECT",
        "request_hash": request_hash,
        "confirmation_hash": _require_sha256(
            confirmation.get("confirmation_hash"),
            "HOLD_CONFIRMATION_HASH_INVALID",
        ),
        "voucher_count_before": before,
        "voucher_count_after": after,
        "voucher_hash_before": _require_sha256(
            voucher_hash_before,
            "HOLD_VOUCHER_PREIMAGE_HASH_INVALID",
        ),
        "voucher_hash_after": _require_sha256(
            voucher_hash_after,
            "HOLD_VOUCHER_POSTIMAGE_HASH_INVALID",
        ),
        "executed_at": _require_text(executed_at, "HOLD_EXECUTION_TIME_REQUIRED"),
        "executor_ref": _require_text(executor_ref, "HOLD_EXECUTOR_REF_REQUIRED"),
        "state_transition": [
            "LOOKUP_VERIFIED",
            "PENDING_OWNER_CONFIRMATION",
            "AUTHORIZED",
            "CONSUMED",
        ],
        "effect": {
            "product_quantity": 1,
            "voucher_quantity": -1,
            "happiness_coin_delta": 0,
        },
    }
    evidence["transaction_hash"] = canonical_sha256(evidence)
    return evidence
