#!/usr/bin/env python3
"""W7TP 會員自然人身分錨點與佐證候選。

設計邊界：
1. 自然人身分錨點由本地建立，不由 Google、設備、伺服器或角色產生。
2. Google 是可選外部佐證，不是自然人身分權威。
3. Founder 是位置／席位，不是第二自然人身分。
4. 原始權杖、電子郵件、姓名、電話等明文禁止進入本候選。
5. 任何重要佐證衝突一律 HOLD（暫停），不得自動改人。
6. 本模組只產生候選，不建立正式權威，最後仍需 Total Field（總場）裁決。
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]

FOUNDER_POLICY_PATH = (
    ROOT
    / "manifests/xiaoj_member_bound_developer_seat_candidate_v0_1/policy.json"
)

SCHEMA_VERSION = "W7TP-MEMBER-NATURAL-PERSON-CORROBORATION-CANDIDATE/1.0"

PASS_STATE = "PASS_MEMBER_NATURAL_PERSON_CORROBORATION_CANDIDATE"
HOLD_CONFLICT = "HOLD_IDENTITY_CORROBORATION_CONFLICT"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
MEMBER_REF = re.compile(r"^member_ref:[A-Za-z0-9._:-]+$")
PROJECTION_REF = re.compile(
    r"^identity_projection_ref:sha256:[0-9a-f]{64}$"
)

# 禁止敏感明文或原始憑證進入候選。
FORBIDDEN_KEYS = frozenset(
    {
        "access_token",
        "credential",
        "email",
        "id_token",
        "name",
        "password",
        "phone",
        "raw_subject",
        "refresh_token",
        "secret",
        "token",
    }
)

GOOGLE_FIELDS = frozenset(
    {
        "verification_state",
        "provider_ref",
        "provider_subject_sha256",
        "identity_projection_ref",
        "identity_projection_sha256",
        "issuer_ref",
        "issued_at_epoch",
        "expires_at_epoch",
        "auth_time_epoch",
        "amr",
    }
)

REQUEST_FIELDS = frozenset(
    {
        "member_ref",
        "explicit_human_confirmation",
        "human_confirmation_ref",
        "anchor_nonce_sha256",
        "google_corroboration",
        "existing_google_subject_sha256",
        "current_epoch",
        "fresh_auth_seconds",
    }
)


def canonical_sha256(value: Any) -> str:
    """計算穩定 JSON SHA256（安全雜湊）。"""
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_anchor_nonce_sha256() -> str:
    """建立一次性本地亂數材料，只回傳雜湊，不回傳原始亂數。"""
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()


def _contains_forbidden_key(value: Any) -> bool:
    """遞迴阻擋權杖與敏感明文字段。"""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_key(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _base(state: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "candidate_only": True,
        "formal_authority_created": False,
        "total_field_decision": "NOT_RUN",
        "requires_total_field_verify": True,
        "natural_person_anchor_candidate": None,
        "google_corroboration_receipt_candidate": None,
        "member_binding_candidate": None,
        "founder_position_binding_candidate": None,
        "assurance": {
            "state": "UNVERIFIED",
            "conflict_state": "NONE",
        },
    }


def _hold(state: str) -> dict[str, Any]:
    return _base(state)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _epoch(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _load_founder_policy() -> dict[str, Any]:
    if not FOUNDER_POLICY_PATH.is_file():
        raise RuntimeError(
            "FOUNDER_POSITION_POLICY_MISSING（創辦人位置政策缺失）"
        )
    data = json.loads(FOUNDER_POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(
            "FOUNDER_POSITION_POLICY_INVALID（創辦人位置政策格式錯誤）"
        )
    return data


def build_google_ui_intent() -> dict[str, Any]:
    """建立 UI 主動式 Google 佐證意圖，不建立第二套 OAuth（開放授權）系統。"""
    return {
        "schema_version": "W7TP-GOOGLE-CORROBORATION-UI-INTENT/1.0",
        "action": "START_GOOGLE_CORROBORATION",
        "action_zh": "發起 Google 身分佐證",
        "user_initiated": True,
        "reuse_existing_google_member_login": True,
        "required_post_verification_state":
            "PASS_TRUSTED_IDENTITY_PROJECTION",
        "requested_assurance_claims": [
            "auth_time",
            "amr",
        ],
        "nonce_required": True,
        "account_selection_preferred": True,
        "raw_token_retained": False,
        "google_is_identity_authority": False,
        "google_is_optional_corroboration": True,
        "conflict_effect": HOLD_CONFLICT,
        "requires_total_field_verify": True,
    }


def _verify_google_candidate(
    google: Mapping[str, Any],
    *,
    current_epoch: int,
    existing_subject_sha256: str | None,
    fresh_auth_seconds: int,
) -> tuple[str, dict[str, Any] | None]:
    """驗證已由既有可信邊界產出的 Google 身分投影證據。"""

    if set(google) != GOOGLE_FIELDS:
        return (
            "HOLD_GOOGLE_CORROBORATION_FIELDS_INVALID",
            None,
        )

    if google.get("verification_state") != "PASS_TRUSTED_IDENTITY_PROJECTION":
        return (
            "HOLD_GOOGLE_TRUSTED_IDENTITY_PROJECTION_REQUIRED",
            None,
        )

    if google.get("provider_ref") != "provider_ref:google":
        return (
            "HOLD_GOOGLE_PROVIDER_REF_INVALID",
            None,
        )

    subject_sha = google.get("provider_subject_sha256")
    if not isinstance(subject_sha, str) or SHA256.fullmatch(subject_sha) is None:
        return (
            "HOLD_GOOGLE_SUBJECT_HASH_INVALID",
            None,
        )

    projection_ref = google.get("identity_projection_ref")
    if (
        not isinstance(projection_ref, str)
        or PROJECTION_REF.fullmatch(projection_ref) is None
    ):
        return (
            "HOLD_GOOGLE_IDENTITY_PROJECTION_REF_INVALID",
            None,
        )

    projection_sha = google.get("identity_projection_sha256")
    if (
        not isinstance(projection_sha, str)
        or SHA256.fullmatch(projection_sha) is None
    ):
        return (
            "HOLD_GOOGLE_IDENTITY_PROJECTION_SHA256_INVALID",
            None,
        )

    if not _nonempty(google.get("issuer_ref")):
        return (
            "HOLD_GOOGLE_ISSUER_REF_REQUIRED",
            None,
        )

    issued = google.get("issued_at_epoch")
    expires = google.get("expires_at_epoch")

    if not _epoch(issued) or not _epoch(expires):
        return (
            "HOLD_GOOGLE_PROJECTION_EPOCH_INVALID",
            None,
        )

    if expires <= issued or current_epoch >= expires:
        return (
            "HOLD_GOOGLE_IDENTITY_PROJECTION_EXPIRED",
            None,
        )

    if issued > current_epoch:
        return (
            "HOLD_GOOGLE_IDENTITY_PROJECTION_NOT_YET_VALID",
            None,
        )

    if existing_subject_sha256 is not None:
        if (
            not isinstance(existing_subject_sha256, str)
            or SHA256.fullmatch(existing_subject_sha256) is None
        ):
            return (
                "HOLD_EXISTING_GOOGLE_SUBJECT_HASH_INVALID",
                None,
            )
        if existing_subject_sha256 != subject_sha:
            return HOLD_CONFLICT, None

    auth_time = google.get("auth_time_epoch")
    amr = google.get("amr")

    if auth_time is not None and not _epoch(auth_time):
        return (
            "HOLD_GOOGLE_AUTH_TIME_INVALID",
            None,
        )

    if auth_time is not None and auth_time > current_epoch:
        return (
            "HOLD_GOOGLE_AUTH_TIME_IN_FUTURE",
            None,
        )

    if not isinstance(amr, list) or not all(
        isinstance(item, str) and item for item in amr
    ):
        return (
            "HOLD_GOOGLE_AMR_INVALID",
            None,
        )

    if auth_time is None:
        freshness_state = "NOT_EVIDENCED"
    elif current_epoch - auth_time <= fresh_auth_seconds:
        freshness_state = "FRESH"
    else:
        freshness_state = "STALE"

    receipt_material = {
        "state": "VERIFIED_GOOGLE_CORROBORATION",
        "source_class": "EXTERNAL_IDENTITY_CORROBORATION",
        "provider_ref": "provider_ref:google",
        "provider_subject_sha256": subject_sha,
        "identity_projection_ref": projection_ref,
        "identity_projection_sha256": projection_sha,
        "issuer_ref": google["issuer_ref"],
        "issued_at_epoch": issued,
        "expires_at_epoch": expires,
        "auth_time_epoch": auth_time,
        "amr": sorted(set(amr)),
        "freshness_state": freshness_state,
        "conflict_state": "NONE",
        "raw_token_retained": False,
        "identity_authority": False,
        "requires_total_field_verify": True,
    }

    receipt = dict(receipt_material)
    receipt["receipt_ref"] = (
        "identity_corroboration_receipt_ref:sha256:"
        + canonical_sha256(receipt_material)
    )

    return "PASS", receipt


def evaluate_candidate(
    request: Mapping[str, Any],
    *,
    founder_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """建立自然人錨點、佐證、會員與 Founder 位置的單一候選結果。"""

    if not isinstance(request, Mapping):
        return _hold("HOLD_REQUEST_NOT_OBJECT")

    if set(request) != REQUEST_FIELDS:
        return _hold("HOLD_REQUEST_FIELDS_INVALID")

    if _contains_forbidden_key(request):
        return _hold(
            "HOLD_PLAINTEXT_OR_RAW_CREDENTIAL_FORBIDDEN"
        )

    member_ref = request.get("member_ref")
    if (
        not isinstance(member_ref, str)
        or MEMBER_REF.fullmatch(member_ref) is None
    ):
        return _hold("HOLD_MEMBER_REF_INVALID")

    if request.get("explicit_human_confirmation") is not True:
        return _hold(
            "HOLD_EXPLICIT_HUMAN_IDENTITY_CONFIRMATION_REQUIRED"
        )

    human_confirmation_ref = request.get("human_confirmation_ref")
    if not _nonempty(human_confirmation_ref) or ":" not in human_confirmation_ref:
        return _hold(
            "HOLD_HUMAN_CONFIRMATION_REF_REQUIRED"
        )

    current_epoch = request.get("current_epoch")
    if not _epoch(current_epoch):
        return _hold("HOLD_CURRENT_EPOCH_INVALID")

    fresh_auth_seconds = request.get("fresh_auth_seconds")
    if (
        not isinstance(fresh_auth_seconds, int)
        or isinstance(fresh_auth_seconds, bool)
        or not 60 <= fresh_auth_seconds <= 86400
    ):
        return _hold(
            "HOLD_FRESH_AUTH_SECONDS_INVALID"
        )

    anchor_nonce_sha256 = request.get("anchor_nonce_sha256")
    if anchor_nonce_sha256 is None:
        anchor_nonce_sha256 = generate_anchor_nonce_sha256()

    if (
        not isinstance(anchor_nonce_sha256, str)
        or SHA256.fullmatch(anchor_nonce_sha256) is None
    ):
        return _hold(
            "HOLD_ANCHOR_NONCE_SHA256_INVALID"
        )

    # 自然人錨點只來自本地亂數材料；不使用 Google、設備或角色推導。
    anchor_basis = {
        "domain": "W7TP_LOCAL_NATURAL_PERSON_ANCHOR_V1",
        "anchor_nonce_sha256": anchor_nonce_sha256,
    }
    anchor_ref = (
        "natural_person_identity_anchor_ref:sha256:"
        + canonical_sha256(anchor_basis)
    )

    anchor_candidate = {
        "anchor_ref": anchor_ref,
        "anchor_type": "SELF_DEFINED_LOCAL",
        "subject_type": "NATURAL_PERSON",
        "explicit_human_confirmation": True,
        "human_confirmation_ref": human_confirmation_ref,
        "external_provider_derived": False,
        "device_derived": False,
        "server_derived": False,
        "role_derived": False,
        "plaintext_identity_visible": False,
        "candidate_only": True,
        "formal_authority_created": False,
    }

    google = request.get("google_corroboration")
    google_receipt = None

    if google is not None:
        if not isinstance(google, Mapping):
            return _hold(
                "HOLD_GOOGLE_CORROBORATION_NOT_OBJECT"
            )

        google_state, google_receipt = _verify_google_candidate(
            google,
            current_epoch=current_epoch,
            existing_subject_sha256=request.get(
                "existing_google_subject_sha256"
            ),
            fresh_auth_seconds=fresh_auth_seconds,
        )

        if google_state != "PASS":
            return _hold(google_state)

    member_binding_material = {
        "relation_type": "NATURAL_PERSON_TO_MEMBER",
        "natural_person_anchor_ref": anchor_ref,
        "member_ref": member_ref,
        "state": "CANDIDATE_ONLY",
    }

    member_binding = dict(member_binding_material)
    member_binding["binding_ref"] = (
        "natural_person_member_binding_ref:sha256:"
        + canonical_sha256(member_binding_material)
    )

    policy = (
        dict(founder_policy)
        if founder_policy is not None
        else _load_founder_policy()
    )

    founder_seat = policy.get("founder_developer_seat")
    founder_binding = None

    if isinstance(founder_seat, Mapping):
        principal_ref = founder_seat.get("principal_ref")
        role_ref = founder_seat.get("role_ref")

        # Founder 只是位置。只有會員引用符合既有 principal_ref 才建立位置候選。
        if member_ref == principal_ref:
            founder_material = {
                "relation_type": "MEMBER_TO_POSITION",
                "member_ref": member_ref,
                "principal_ref": principal_ref,
                "role_ref": role_ref,
                "max_seats": founder_seat.get("max_seats"),
                "exclusive": founder_seat.get("exclusive"),
                "transferable": founder_seat.get("transferable"),
                "subdelegation": founder_seat.get("subdelegation"),
                "state": "CANDIDATE_ONLY",
                "founder_is_position_not_identity": True,
            }
            founder_binding = dict(founder_material)
            founder_binding["binding_ref"] = (
                "member_position_binding_ref:sha256:"
                + canonical_sha256(founder_material)
            )

    if google_receipt is None:
        assurance_state = "BASE_LOCAL_HUMAN_CONFIRMED"
    else:
        freshness = google_receipt["freshness_state"]
        if freshness == "FRESH":
            assurance_state = "GOOGLE_CORROBORATED_FRESH_AUTH"
        elif freshness == "STALE":
            assurance_state = "GOOGLE_CORROBORATED_STALE_AUTH"
        else:
            assurance_state = (
                "GOOGLE_CORROBORATED_AUTH_TIME_NOT_EVIDENCED"
            )

    result = _base(PASS_STATE)
    result["natural_person_anchor_candidate"] = anchor_candidate
    result["google_corroboration_receipt_candidate"] = google_receipt
    result["member_binding_candidate"] = member_binding
    result["founder_position_binding_candidate"] = founder_binding
    result["assurance"] = {
        "state": assurance_state,
        "conflict_state": "NONE",
        "external_corroboration_required": False,
        "corroboration_may_increase_assurance": True,
        "conflict_must_hold": True,
    }

    result["ui_verification_intent"] = build_google_ui_intent()

    result["result_sha256"] = canonical_sha256(result)
    return result


def main() -> int:
    """從標準輸入接收 JSON（結構化資料）並輸出候選結果。"""
    try:
        request = json.load(sys.stdin)
        result = evaluate_candidate(request)
    except Exception as exc:
        result = _hold("HOLD_CANDIDATE_RUNTIME_ERROR")
        result["error_class"] = type(exc).__name__

    sys.stdout.write(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
