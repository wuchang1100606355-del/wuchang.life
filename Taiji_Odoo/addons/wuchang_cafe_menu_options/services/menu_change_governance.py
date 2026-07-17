"""Pure governance helpers for Odoo cafe menu change candidates.

This module deliberately has no Odoo dependency so the candidate and seal
rules can be tested without a database.  It never applies a product change.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping


ENCODING_REGISTRY_VERSION = "W7TP-CORE-ENCODING/1.0"
CHANGE_TYPES = {"create", "update", "archive", "reactivate"}
MENU_VALUE_KEYS = {
    "thing_code",
    "name",
    "list_price",
    "pos_category_ids",
    "option_group_id",
    "image_sha256",
    "available_in_pos",
    "active",
}
REF_PATTERN = re.compile(r"^[A-Za-z0-9_.:/-]{3,180}$")
THING_CODE_PATTERN = re.compile(
    r"^W7TP_THING_REF:v1:PRODUCT:sha256:[a-f0-9]{64}$"
)
UTC_EVENT_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)


class MenuChangeGovernanceError(ValueError):
    """Raised when a menu change candidate would violate the local gate."""


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {
            _normalize(key): _normalize(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(child) for child in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_odoo_product_thing_code(company_id: int, product_template_id: int) -> str:
    """Build the same authority-scoped thing code as the Total Field core."""

    if not isinstance(company_id, int) or company_id <= 0:
        raise MenuChangeGovernanceError("COMPANY_ID_INVALID")
    if not isinstance(product_template_id, int) or product_template_id <= 0:
        raise MenuChangeGovernanceError("PRODUCT_TEMPLATE_ID_INVALID")
    digest = stable_sha256(
        {
            "encoding_version": ENCODING_REGISTRY_VERSION,
            "thing_class": "PRODUCT",
            "authority_namespace": f"ODOO_COMPANY_{company_id}",
            "stable_coordinate": f"product.template:{product_template_id}",
        }
    )
    return f"W7TP_THING_REF:v1:PRODUCT:sha256:{digest}"


def _opaque_ref(value: Any, field_name: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value or "")).strip()
    if not REF_PATTERN.fullmatch(normalized):
        raise MenuChangeGovernanceError(f"{field_name.upper()}_INVALID")
    return normalized


def _utc_event_time(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not UTC_EVENT_TIME_PATTERN.fullmatch(normalized):
        raise MenuChangeGovernanceError(f"{field_name.upper()}_INVALID")
    return normalized


def _menu_values(value: Mapping[str, Any] | None, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MenuChangeGovernanceError(f"{field_name.upper()}_INVALID")
    unknown = set(value) - MENU_VALUE_KEYS
    if unknown:
        raise MenuChangeGovernanceError(f"{field_name.upper()}_FIELD_NOT_ALLOWED")
    normalized = _normalize(dict(value))
    if "thing_code" in normalized and not THING_CODE_PATTERN.fullmatch(
        str(normalized["thing_code"] or "")
    ):
        raise MenuChangeGovernanceError(f"{field_name.upper()}_THING_CODE_INVALID")
    if "name" in normalized:
        name = str(normalized["name"] or "").strip()
        if not name or len(name) > 180:
            raise MenuChangeGovernanceError(f"{field_name.upper()}_NAME_INVALID")
        normalized["name"] = name
    if "list_price" in normalized:
        price = normalized["list_price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            raise MenuChangeGovernanceError(f"{field_name.upper()}_PRICE_INVALID")
    if "pos_category_ids" in normalized:
        category_ids = normalized["pos_category_ids"]
        if not isinstance(category_ids, list) or any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0
            for item in category_ids
        ):
            raise MenuChangeGovernanceError(
                f"{field_name.upper()}_POS_CATEGORY_IDS_INVALID"
            )
        normalized["pos_category_ids"] = sorted(set(category_ids))
    if "option_group_id" in normalized:
        option_group_id = normalized["option_group_id"]
        if option_group_id not in (None, False) and (
            isinstance(option_group_id, bool)
            or not isinstance(option_group_id, int)
            or option_group_id <= 0
        ):
            raise MenuChangeGovernanceError(
                f"{field_name.upper()}_OPTION_GROUP_ID_INVALID"
            )
    if "image_sha256" in normalized and normalized["image_sha256"] not in (
        None,
        False,
    ) and not re.fullmatch(r"[a-f0-9]{64}", str(normalized["image_sha256"])):
        raise MenuChangeGovernanceError(
            f"{field_name.upper()}_IMAGE_SHA256_INVALID"
        )
    for boolean_field in ("available_in_pos", "active"):
        if boolean_field in normalized and not isinstance(
            normalized[boolean_field], bool
        ):
            raise MenuChangeGovernanceError(
                f"{field_name.upper()}_{boolean_field.upper()}_INVALID"
            )
    return normalized


def build_menu_change_candidate(
    *,
    change_type: str,
    group_ref: str,
    store_ref: str,
    requester_ref: str,
    responsible_person_ref: str,
    same_principal_dual_role: bool,
    action_at_utc: str,
    support_reason_sha256: str,
    current_values: Mapping[str, Any] | None,
    proposed_values: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic, fail-closed remote menu change candidate."""

    if change_type not in CHANGE_TYPES:
        raise MenuChangeGovernanceError("CHANGE_TYPE_INVALID")
    group_ref = _opaque_ref(group_ref, "group_ref")
    store_ref = _opaque_ref(store_ref, "store_ref")
    requester_ref = _opaque_ref(requester_ref, "requester_ref")
    responsible_person_ref = _opaque_ref(
        responsible_person_ref, "responsible_person_ref"
    )
    if not isinstance(same_principal_dual_role, bool):
        raise MenuChangeGovernanceError("SAME_PRINCIPAL_DUAL_ROLE_INVALID")
    action_at_utc = _utc_event_time(action_at_utc, "action_at_utc")
    if not re.fullmatch(r"[a-f0-9]{64}", str(support_reason_sha256 or "")):
        raise MenuChangeGovernanceError("SUPPORT_REASON_SHA256_INVALID")
    current = _menu_values(current_values, "current_values")
    proposed = _menu_values(proposed_values, "proposed_values")

    if change_type == "create":
        if current or not {"name", "list_price"}.issubset(proposed):
            raise MenuChangeGovernanceError("CREATE_VALUES_INVALID")
    elif not current or not current.get("thing_code"):
        raise MenuChangeGovernanceError("CURRENT_PRODUCT_REQUIRED")
    if change_type == "update" and not proposed:
        raise MenuChangeGovernanceError("NO_PROPOSED_CHANGE")
    if change_type == "archive":
        proposed = {"active": False, "available_in_pos": False}
    elif change_type == "reactivate":
        proposed = {"active": True, "available_in_pos": True}

    current_sha256 = stable_sha256(current)
    proposed_sha256 = stable_sha256(proposed)
    packet: dict[str, Any] = {
        "schema_version": "W7TP-ODOO-CAFE-MENU-CHANGE-CANDIDATE/1.0",
        "state": "PENDING_GROUP_RESPONSIBLE_PERSON_REVIEW",
        "profile": "CAFE_POS",
        "D1": {
            "intent": "CHANGE_ONE_ODOO_MENU_ITEM",
            "change_type": change_type,
            "what": proposed,
        },
        "D2": {
            "current_values": current,
            "current_sha256": current_sha256,
            "proposed_values": proposed,
            "proposed_sha256": proposed_sha256,
        },
        "D3": {
            "system": "ODOO_MANAGER_BACKEND",
            "group_ref": group_ref,
            "store_ref": store_ref,
            "target_thing_code": current.get("thing_code"),
            "where": {
                "group_ref": group_ref,
                "store_ref": store_ref,
            },
        },
        "D4": {
            "who": {
                "actor_ref": requester_ref,
                "responsible_person_ref": responsible_person_ref,
                "single_account_multi_role": same_principal_dual_role,
            },
            "when": {"submitted_at_utc": action_at_utc},
            "evidence_refs": [
                f"odoo-product-snapshot-sha256:{current_sha256}",
                f"proposed-menu-values-sha256:{proposed_sha256}",
                f"support-reason-sha256:{support_reason_sha256}",
            ]
        },
        "D5": {
            "execution": "RESPONSIBLE_PERSON_REVIEW_THEN_ODOO_APPLY",
            "candidate_only": True,
            "remote_support_direct_write": False,
            "db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
        },
        "D6": {
            "generative_transmission": "PROTOCOL_NATIVE_8D_STATE_FIELD_PACKET",
            "lookup": True,
            "reconstruction_level": "L3_CANDIDATE",
            "file_moving": False,
        },
        "D7": {
            "distinct_second_person_required": False,
            "single_human_identity_single_account": True,
            "requester_ref": requester_ref,
            "responsible_person_ref": responsible_person_ref,
            "same_natural_person_multiple_roles_supported": True,
            "same_principal_dual_role": same_principal_dual_role,
            "automatic_apply_after_request": "BLOCK",
            "explicit_second_human_action_for_remote_support": "REQUIRED",
            "concurrent_product_change": "REVALIDATE_OR_BLOCK",
        },
        "D8": {
            "decision": "PENDING_GROUP_RESPONSIBLE_PERSON_REVIEW",
            "authority": "GROUP_RESPONSIBLE_PERSON_HUMAN_REVIEW",
            "formal_execution_authority": False,
        },
    }
    packet["candidate_sha256"] = stable_sha256(packet)
    return packet


def build_responsible_approval_seal(
    *,
    candidate_sha256: str,
    responsible_person_ref: str,
    product_thing_code: str,
    applied_values: Mapping[str, Any],
    same_principal_dual_role: bool,
    review_note_sha256: str,
    actor_ref: str,
    action_location_ref: str,
    reviewed_at_utc: str,
) -> dict[str, Any]:
    """Seal an already-applied candidate without retaining account plaintext."""

    if not re.fullmatch(r"[a-f0-9]{64}", str(candidate_sha256 or "")):
        raise MenuChangeGovernanceError("CANDIDATE_SHA256_INVALID")
    responsible_person_ref = _opaque_ref(
        responsible_person_ref, "responsible_person_ref"
    )
    if not THING_CODE_PATTERN.fullmatch(str(product_thing_code or "")):
        raise MenuChangeGovernanceError("PRODUCT_THING_CODE_INVALID")
    if not isinstance(same_principal_dual_role, bool):
        raise MenuChangeGovernanceError("SAME_PRINCIPAL_DUAL_ROLE_INVALID")
    actor_ref = _opaque_ref(actor_ref, "actor_ref")
    action_location_ref = _opaque_ref(
        action_location_ref, "action_location_ref"
    )
    reviewed_at_utc = _utc_event_time(reviewed_at_utc, "reviewed_at_utc")
    if not re.fullmatch(r"[a-f0-9]{64}", str(review_note_sha256 or "")):
        raise MenuChangeGovernanceError("REVIEW_NOTE_SHA256_INVALID")
    applied = _menu_values(applied_values, "applied_values")
    seal: dict[str, Any] = {
        "schema_version": "W7TP-ODOO-CAFE-MENU-RESPONSIBLE-APPROVAL/1.0",
        "state": "APPLIED_AFTER_GROUP_RESPONSIBLE_PERSON_REVIEW",
        "candidate_sha256": candidate_sha256,
        "responsible_person_ref": responsible_person_ref,
        "product_thing_code": product_thing_code,
        "applied_values_sha256": stable_sha256(applied),
        "same_natural_person_multiple_roles_supported": True,
        "same_principal_dual_role": same_principal_dual_role,
        "event": {
            "who": actor_ref,
            "where": action_location_ref,
            "when": reviewed_at_utc,
            "what": "APPROVE_AND_APPLY_ONE_ODOO_MENU_ITEM_CHANGE",
        },
        "review_note_sha256": review_note_sha256,
        "remote_support_direct_write": False,
        "automatic_apply_after_request": False,
        "payment_capture": False,
    }
    seal["approval_sha256"] = stable_sha256(seal)
    return seal
