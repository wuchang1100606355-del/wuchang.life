"""Three-major-scene product candidate.

This module reuses the existing three-organization scene map, TAIJI04
audiovisual service desk, product-system-root reference, and the single Total
Field candidate gateway. It creates isolated candidates only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, MutableSet, Sequence
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

from tools.total_field.wuchang_three_org_container_scene_bridge import (
    build_audiovisual_natural_language_service_candidate,
    build_p4_node_carrier_binding_candidate,
    load_three_org_scene_map,
)
from tools.total_field_candidate_gateway import receive_candidate


AUTHORIZATION_ID = "FOUNDER_THREE_SCENE_PRODUCT_EXPANSION_20260723"
CANONICAL_STATUS = "CANDIDATE_NOT_CANONICAL"
ROOT_PACKET_SHA256 = (
    "a073f824d77e89b024f8f43415af857272e8a59d6f6de8b518ee1aba90971a3d"
)
BASE_RUN_ID = "CANONICAL_BIND_20260723T052820Z"
PRODUCT_CONFIG_KEY = "three_major_scene_product"
DEFAULT_SCHEMA_PATH = Path(
    "schemas/field/w7tp_three_major_scene_packet_candidate_v1.schema.json"
)
DEFAULT_RUNTIME_PARENT = Path("runtime/total_field/three_major_scenes")

ACTIVATION_BINDING_RUN_ID = "THREE_SCENE_PRODUCT_20260723T153901Z"
FUND_AUTHORITY_REF = (
    "authority-ref:local-total-field:community-digital-development-fund:"
    "conservation-1-to-1-to-1:v1"
)
COMMITTEE_BRANCH_CONTRACT_REF = (
    "contract-ref:committee-branch-total-field:caller-supplied:v1"
)
EXPECTED_ACTIVATION_BINDING_BASE = {
    "shared_skill_contract_file_sha256": (
        "1e6143405229d417387c6810b0fafa8f8e746083af16c74318ac0f6e989e9bdc"
    ),
    "packet_sha256": {
        "public_benefit": (
            "04e6d6e8768c5e54e745cb2e58c7630ec617a4acc11e1cde3e5ac9208144985d"
        ),
        "property": (
            "10794ba23e56203659c989ca269e8b6fe0db409fa730c9928f1391bfb4092835"
        ),
        "merchant": (
            "d46fe2eed5832eabe04a348c3e4148c64d8bf25321075a67bbecc023c85b9e19"
        ),
    },
}

ACTIVATION_BINDING_FILES = {
    "fund": "FUND_1_TO_1_TO_1_LOCAL_TOTAL_FIELD_AUTHORITY_CONTRACT.json",
    "statutory": "PROPERTY_STATUTORY_SOURCE_MANIFEST.json",
    "committee": "COMMITTEE_BRANCH_TOTAL_FIELD_REFERENCE_CONTRACT.json",
    "supplement": "THREE_MAJOR_SCENE_ACTIVATION_BINDING_SUPPLEMENT.json",
    "receipt": "TOTAL_FIELD_ACTIVATION_BINDING_RECEIPT.json",
    "checksums": "SHA256SUMS_ACTIVATION_PRECONDITIONS",
}

OFFICIAL_PROPERTY_SOURCE_HOSTS = frozenset(
    {
        "law.moj.gov.tw",
        "www.ly.gov.tw",
        "www.nlma.gov.tw",
        "www.publicwork.ntpc.gov.tw",
    }
)

PROPERTY_STATUTORY_SOURCES = (
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "全國法規資料庫／內政部",
        "document_title": "公寓大廈管理條例",
        "official_url": (
            "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=D0070118"
        ),
        "version_or_effective_date": "修正日期：民國111年05月11日",
        "local_reference_or_hash": (
            "sha256:761f84662a0d19726a857b618c9c26941eead3cc583b19b9d554626b3f350271"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "unit_owner_meeting",
            "committee_formation_and_election",
            "bylaw",
            "public_fund_and_finance",
            "announcement_and_document_access",
            "repair_and_common_facilities",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "全國法規資料庫／內政部",
        "document_title": "公寓大廈管理條例施行細則",
        "official_url": (
            "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=D0070119"
        ),
        "version_or_effective_date": "修正日期：民國94年11月16日",
        "local_reference_or_hash": (
            "sha256:a3f9644b952e37a51b777b4c416d2d48559e4803f5dbf767f74f770ae8aa18d4"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "unit_owner_meeting_notice_attendance_proxy_and_minutes",
            "committee_formation_and_election",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "內政部國土管理署",
        "document_title": "公寓大廈管理報備事項處理原則",
        "official_url": (
            "https://www.nlma.gov.tw/ch/legislation/law%26regusw/180"
        ),
        "version_or_effective_date": "民國104年07月01日生效",
        "local_reference_or_hash": (
            "sha256:cc8751228e9e41c6552e2c1f611c91afe1e8b6cbdc213a723ec7acced1200189"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "committee_formation_election_and_reporting",
            "unit_owner_meeting_records",
            "bylaw_revision_reporting",
            "common_facility_handover",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "內政部國土管理署",
        "document_title": "公寓大廈規約範本",
        "official_url": (
            "https://www.nlma.gov.tw/ch/legislation/regsearch/171"
        ),
        "version_or_effective_date": "民國103年07月01日生效版本",
        "local_reference_or_hash": (
            "sha256:cc8751228e9e41c6552e2c1f611c91afe1e8b6cbdc213a723ec7acced1200189"
        ),
        "applicable_scene": ["property"],
        "coverage": ["bylaw", "bylaw_revision"],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "NEW_TAIPEI_CITY",
        "issuing_authority": "新北市政府工務局",
        "document_title": "公寓大廈管理組織報備相關表格",
        "official_url": (
            "https://www.publicwork.ntpc.gov.tw/home.jsp?"
            "id=20192c6ff61fcc86"
        ),
        "version_or_effective_date": "網頁更新日期：2026-07-13",
        "local_reference_or_hash": (
            "sha256:d908f3e0c47d2ebd21c93f87c56f7e3a6b06fa202b47935fb835bd20ae79f2c1"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "unit_owner_meeting_notice_attendance_proxy_and_minutes",
            "committee_formation_election_and_reporting",
            "bylaw_and_revision",
            "new_taipei_management_forms",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "NEW_TAIPEI_CITY",
        "issuing_authority": "新北市政府工務局",
        "document_title": "公共基金申請撥付相關表格",
        "official_url": (
            "https://www.publicwork.ntpc.gov.tw/home.jsp?"
            "id=2abb71766f9764ee"
        ),
        "version_or_effective_date": "網頁更新日期：2026-01-15",
        "local_reference_or_hash": (
            "sha256:4b17cccdb026e05e834d6f00e5a57ed597cfbfea49db742f614919e6d811fb52"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "public_fund_and_financial_records",
            "common_facility_handover",
            "new_taipei_management_forms",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "NEW_TAIPEI_CITY",
        "issuing_authority": "新北市政府工務局",
        "document_title": "公寓大廈管理科報備事項問答",
        "official_url": (
            "https://www.publicwork.ntpc.gov.tw/home.jsp?"
            "id=8466a2954ea70aee"
        ),
        "version_or_effective_date": "網頁更新日期：2025-07-17",
        "local_reference_or_hash": (
            "sha256:869604ff6e6bf6ca3c04e307f495579eb4dd9558e6a32877317b98c581d9be8e"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "committee_formation_election_and_reporting",
            "unit_owner_meeting_records",
            "bylaw_revision_reporting",
            "new_taipei_management_forms",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "內政部國土管理署",
        "document_title": "公寓大廈管理問答集",
        "official_url": "https://www.nlma.gov.tw/ch/titlelist/areanu/4716",
        "version_or_effective_date": "retrieved-current-official-projection",
        "local_reference_or_hash": (
            "sha256:801231c4a5999cddb2e1183b67319e723dff26f2f3738c33368cd42240ae560f"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "committee_and_management",
            "public_fund_and_finance",
            "resident_document_access",
            "repair_and_common_facilities",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE",
    },
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "全國法規資料庫／個人資料保護委員會籌備處",
        "document_title": "個人資料保護法",
        "official_url": (
            "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=I0050021"
        ),
        "version_or_effective_date": (
            "修正日期：民國114年11月11日；部分修正條文施行日期未定"
        ),
        "local_reference_or_hash": (
            "sha256:a9456ee5d7840423b4b65f3744372cb8c9abe6c4b3193c45cbf2f21d999818e1"
        ),
        "applicable_scene": ["property"],
        "coverage": [
            "announcement_and_document_access",
            "surveillance_personal_data_framework",
        ],
        "verification_status": "VERIFIED_OFFICIAL_SOURCE_EFFECTIVE_STATUS_NOTED",
    },
    {
        "jurisdiction": "TAIWAN",
        "issuing_authority": "立法院法制局",
        "document_title": "公寓大廈內監視錄影法制問題研析",
        "official_url": (
            "https://www.ly.gov.tw/Pages/Detail.aspx?"
            "nodeid=6586&pid=84720"
        ),
        "version_or_effective_date": "民國102年11月01日更新",
        "local_reference_or_hash": (
            "sha256:1964d3a22e73adfce45d0b42941fd7e23e867ee3bffc74633d56eeab55d2c721"
        ),
        "applicable_scene": ["property"],
        "coverage": ["surveillance_access_and_privacy_official_research"],
        "verification_status": (
            "VERIFIED_OFFICIAL_RESEARCH_NOT_BINDING_LEGAL_ADVICE"
        ),
    },
)

PROPERTY_STATUTORY_MISSING = (
    {
        "precondition": (
            "PRIVATE_COMMITTEE_SURVEILLANCE_FOOTAGE_ACCESS_OPERATING_RULE"
        ),
        "verification_status": "PRECONDITION_MISSING",
        "reason": (
            "中央法規及官方研究未提供可直接取代實際社區規約、"
            "區分所有權人會議決議與適用主管機關確認的統一調閱程序"
        ),
        "required_resolution": (
            "由實際適用地總場核對社區規約、會議決議、個資法有效條文"
            "及主管機關或警察機關適用程序"
        ),
        "cloud_fill": "FORBIDDEN",
    },
)

SCENE_FILES = {
    "public_benefit": "COMMUNITY_ASSOCIATION_PUBLIC_BENEFIT_SCENE_PACKET.json",
    "property": "INTEGRATED_PROPERTY_MANAGEMENT_SCENE_PACKET.json",
    "merchant": "COMMUNITY_MERCHANT_MANAGEMENT_SCENE_PACKET.json",
}

SHARED_SKILL_REFS = (
    "skill_ref:personal_xiaoj",
    "skill_ref:personal_calendar",
    "skill_ref:community_wish_tree",
    "skill_ref:community_happiness_coin",
    "skill_ref:line_invoice_reference",
    "skill_ref:community_discussion",
    "skill_ref:personal_qa_document_proposal",
    "skill_ref:meeting_realtime_secretariat",
    "skill_ref:personal_data_boundary",
    "skill_ref:family_and_scene_mount",
)

FUND_PRECONDITIONS = (
    "fund_rule_ref",
    "blood_engine_rule_ref",
    "bank_account_ref",
    "ring_fence_evidence_ref",
    "happiness_coin_issuance_rule_ref",
    "merchant_ticket_limit_rule_ref",
    "reconciliation_formula_ref",
    "audit_rule_ref",
)

FORBIDDEN_DATA_KEYS = frozenset(
    {
        "member_plaintext",
        "member_name",
        "phone_number",
        "wifi_account_plaintext",
        "raw_audio",
        "raw_video",
        "raw_image",
        "secret",
        "password",
        "token",
        "bank_account_number",
        "bank_balance",
        "ring_fence_amount",
        "happiness_coin_actual_limit",
        "merchant_ticket_actual_limit",
    }
)

FORBIDDEN_CLOUD_ZONES = frozenset(
    {
        "fund_rules_or_values",
        "blood_engine_rules",
        "one_to_one_to_one_formula",
        "bank_account_balance_or_ring_fence_data",
        "happiness_coin_or_merchant_ticket_actual_limits",
        "member_plaintext_or_identifying_data",
        "legal_document_content_or_legal_duty",
        "protected_codebook",
        "deploy_restart_db_or_router_authority",
    }
)


class ThreeMajorSceneProductError(ValueError):
    """One stable candidate validation error."""


def canonical_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_object(value: Any) -> str:
    """Return one deterministic SHA-256 for a JSON value."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _p4_scene_validator() -> Draft202012Validator:
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$ref": "#/$defs/p4MemberSceneBinding",
            "$defs": schema["$defs"],
        }
    )


def build_member_sovereign_scene_binding_candidate(
    *,
    p3_request: Mapping[str, Any],
    p3_gate: Mapping[str, Any],
    verified_channel_binding: Mapping[str, Any],
    scene: str,
    capability_ref: str,
    node_ref: str,
    d3_coordinate_ref: str,
    carrier_kind: str,
    carrier_ref: str,
    existing_device_nodes: Mapping[str, str] | None = None,
    carrier_metadata: Mapping[str, Any] | None = None,
    founder_scene: bool = False,
    current_epoch: int,
) -> dict[str, Any]:
    """Derive one scene/node/carrier candidate only from a P3 PASS envelope."""

    hold = {
        "state": "HOLD_P3_SCENE_BINDING_NOT_EVIDENCED",
        "candidate_only": True,
        "runtime_released": False,
    }
    if (
        p3_gate.get("state") != "PASS"
        or p3_request.get("request_mode") != "ACTION_REQUEST"
    ):
        return hold
    if (
        verified_channel_binding.get("verifier_result") != "PASS"
        or verified_channel_binding.get("member_ref")
        != p3_request.get("member_ref")
        or not isinstance(
            verified_channel_binding.get("verified_channel_binding_ref"),
            str,
        )
    ):
        return {
            **hold,
            "state": "HOLD_CROSS_MEMBER_CHANNEL_BINDING",
        }
    gate_material = p3_gate.get("gate_material")
    session = p3_request.get("session")
    p3_scene = p3_request.get("scene")
    action = p3_request.get("action")
    if not all(
        isinstance(value, Mapping)
        for value in (gate_material, session, p3_scene, action)
    ):
        return hold
    expected_gate_ref = (
        "member_action_gate_ref:sha256:"
        + sha256_object(gate_material)
    )
    if p3_gate.get("gate_ref") != expected_gate_ref:
        return {
            **hold,
            "state": "HOLD_P3_GATE_HASH_MISMATCH",
        }
    expected_gate_fields = {
        "identity_root_ref": p3_request.get("identity_root_ref"),
        "root_generation": p3_request.get("root_generation"),
        "revocation_epoch": p3_request.get("revocation_epoch"),
        "session_ref": session.get("session_ref"),
        "scene_ref": p3_scene.get("scene_ref"),
        "action_hash": action.get("action_hash"),
        "scope_refs": action.get("scope_refs"),
        "effect_class": action.get("effect_class"),
    }
    if any(
        gate_material.get(field) != value
        for field, value in expected_gate_fields.items()
    ):
        return {
            **hold,
            "state": "HOLD_P3_GATE_BINDING_MISMATCH",
        }
    scopes = action.get("scope_refs")
    if (
        not isinstance(scopes, list)
        or scopes != sorted(set(scopes))
        or session.get("scope_refs") != scopes
        or p3_scene.get("scope_refs") != scopes
    ):
        return {
            **hold,
            "state": "HOLD_SCOPE_EXPANSION",
        }
    if (
        session.get("effect_class") != action.get("effect_class")
        or p3_scene.get("effect_class") != action.get("effect_class")
    ):
        return {
            **hold,
            "state": "HOLD_EFFECT_CLASS_EXPANSION",
        }
    device_ref = session.get("device_ref")
    if not isinstance(device_ref, str):
        return {
            **hold,
            "state": "HOLD_P3_DEVICE_BINDING_REQUIRED",
        }
    role_seat_snapshot = session.get("role_seat_snapshot")
    if not isinstance(role_seat_snapshot, Mapping):
        return {
            **hold,
            "state": "HOLD_ROLE_SEAT_SNAPSHOT_REQUIRED",
        }
    role_seat_snapshot_ref = (
        "role_seat_snapshot_ref:sha256:"
        + sha256_object(role_seat_snapshot)
    )
    node_binding = build_p4_node_carrier_binding_candidate(
        device_ref=device_ref,
        node_ref=node_ref,
        carrier_kind=carrier_kind,
        carrier_ref=carrier_ref,
        d3_coordinate_ref=d3_coordinate_ref,
        existing_device_nodes=existing_device_nodes,
        carrier_metadata=carrier_metadata,
    )
    if node_binding.get("state") != "PASS_NODE_CARRIER_BINDING_CANDIDATE":
        return {
            **hold,
            "state": node_binding["state"],
        }
    founder_role_seat_lease_ref = None
    if founder_scene:
        leases = role_seat_snapshot.get("seat_leases")
        founder_leases = [
            lease for lease in (leases or [])
            if isinstance(lease, Mapping)
            and lease.get("seat_class") == "FOUNDER_DEVELOPER"
            and lease.get("identity_root_ref")
            == p3_request.get("identity_root_ref")
            and lease.get("root_generation")
            == p3_request.get("root_generation")
            and lease.get("revocation_epoch")
            == p3_request.get("revocation_epoch")
            and isinstance(lease.get("issued_at_epoch"), int)
            and isinstance(lease.get("expires_at_epoch"), int)
            and lease["issued_at_epoch"] <= current_epoch
            < lease["expires_at_epoch"]
        ]
        if len(founder_leases) != 1:
            return {
                **hold,
                "state": "HOLD_FOUNDER_ROLE_SEAT_LEASE_REQUIRED",
            }
        founder_role_seat_lease_ref = (
            "role_seat_lease_ref:sha256:"
            + sha256_object(founder_leases[0])
        )
    material = {
        "schema_version": "w7tp.member-channel-scene-pos-node-binding.v1",
        "state": "PASS_SCENE_BINDING_CANDIDATE",
        "p3_gate_ref": p3_gate.get("gate_ref"),
        "verified_channel_binding_ref": verified_channel_binding.get(
            "verified_channel_binding_ref"
        ),
        "action_hash": action.get("action_hash"),
        "member_ref": p3_request.get("member_ref"),
        "identity_root_ref": p3_request.get("identity_root_ref"),
        "root_generation": p3_request.get("root_generation"),
        "revocation_epoch": p3_request.get("revocation_epoch"),
        "session_ref": session.get("session_ref"),
        "scene_ref": p3_scene.get("scene_ref"),
        "scene": scene,
        "scope_refs": scopes,
        "effect_class": action.get("effect_class"),
        "device_ref": device_ref,
        "channel_ref": session.get("channel_ref"),
        "node_ref": node_ref,
        "capability_ref": capability_ref,
        "d3_coordinate_ref": d3_coordinate_ref,
        "carrier_ref": carrier_ref,
        "carrier_kind": carrier_kind,
        "transport_priority": node_binding["transport_priority"],
        "protocol_role": "CARRIER_ONLY",
        "generative_transmission": (
            "W7TP_PROTOCOL_NATIVE_8D_INTENT_FIELD_PACKET"
        ),
        "node_binding_ref": node_binding["node_binding_ref"],
        "role_seat_snapshot_ref": role_seat_snapshot_ref,
        "founder_role_seat_lease_required": founder_scene,
        "founder_role_seat_lease_ref": founder_role_seat_lease_ref,
        "pos_mode": "DRY_RUN_CANDIDATE_ONLY",
        "formal_pos_write": False,
        "order_created": False,
        "payment_capture": False,
        "inventory_write": False,
        "price_write": False,
        "member_data_write": False,
        "candidate_only": True,
        "runtime_released": False,
    }
    material["binding_ref"] = (
        "scene_binding_ref:sha256:" + sha256_object(material)
    )
    if list(_p4_scene_validator().iter_errors(material)):
        return {
            **hold,
            "state": "HOLD_P4_SCENE_SCHEMA_INVALID",
        }
    return material


def _copy_json(value: Any) -> Any:
    return json.loads(canonical_bytes(value))


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ThreeMajorSceneProductError("INVALID_UTC_TIMESTAMP") from exc
    if parsed.tzinfo is None:
        raise ThreeMajorSceneProductError("UTC_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _find_forbidden_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).casefold()
            child = f"{path}.{key}"
            if normalized in FORBIDDEN_DATA_KEYS:
                return child
            found = _find_forbidden_key(nested, child)
            if found:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _find_forbidden_key(nested, f"{path}[{index}]")
            if found:
                return found
    return None


def load_product_config(
    scene_map_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the product section from the existing scene map."""

    map_data = (
        load_three_org_scene_map(scene_map_path)
        if scene_map_path is not None
        else load_three_org_scene_map()
    )
    product = map_data.get(PRODUCT_CONFIG_KEY)
    if not isinstance(product, dict):
        raise ThreeMajorSceneProductError("PRODUCT_CONFIG_REQUIRED")
    canonical_root = product.get("canonical_product_root") or {}
    if (
        canonical_root.get("base_run_id") != BASE_RUN_ID
        or canonical_root.get("packet_sha256") != ROOT_PACKET_SHA256
        or canonical_root.get("reference_only") is not True
    ):
        raise ThreeMajorSceneProductError("CANONICAL_ROOT_REFERENCE_MISMATCH")
    if set((product.get("scenes") or {})) != set(SCENE_FILES):
        raise ThreeMajorSceneProductError("EXACT_THREE_SCENES_REQUIRED")
    if any(
        product.get(key) is not False
        for key in (
            "runtime_activation",
            "database_write",
            "deploy",
            "restart",
            "router_write",
            "canonical_write",
        )
    ):
        raise ThreeMajorSceneProductError("PRODUCT_SIDE_EFFECT_BOUNDARY_INVALID")
    return _copy_json(product)


def build_shared_sovereign_ai_skill_contract(
    product_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one shared skill contract referenced by all three scenes."""

    product = dict(product_config or load_product_config())
    configured = product["shared_sovereign_ai_skill_contract"]
    if tuple(configured.get("skills") or ()) != SHARED_SKILL_REFS:
        raise ThreeMajorSceneProductError("SHARED_SKILL_CONTRACT_MISMATCH")
    contract = {
        "schema_version": "w7tp.shared-sovereign-ai-skill-contract.v1",
        "contract_ref": configured["contract_ref"],
        "identity_mode": "VERIFIED_8D_INTENT_FIELD_TENSOR_PACKET",
        "central_real_name_identity_graph": False,
        "skills": list(SHARED_SKILL_REFS),
        "resource_access_mode": (
            "SYSTEM_BOUND_IDENTITY_PACKET_CAPABILITY_AND_RESOURCE_REFS_ONLY"
        ),
        "member_plaintext_to_cloud": False,
        "raw_media_to_cloud": False,
        "three_party_collaboration": product["three_party_collaboration"],
        "audiovisual_service_desk_ref": (
            "service_ref:taiji04_existing_audiovisual_natural_language"
        ),
        "runtime_activation": False,
        "canonical_status": CANONICAL_STATUS,
    }
    contract["contract_sha256"] = sha256_object(contract)
    return contract


def build_identity_tensor_packet(
    identity_packet_ref: str,
    *,
    skill_refs: Sequence[str] = SHARED_SKILL_REFS,
    resource_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Build one reference-only verified 8D tensor identity candidate."""

    if not str(identity_packet_ref).startswith("identity-packet-ref:"):
        raise ThreeMajorSceneProductError("IDENTITY_PACKET_REF_REQUIRED")
    packet = {
        "schema_version": "w7tp.verified-8d-identity-tensor.v1",
        "identity_packet_ref": identity_packet_ref,
        "dimensions": {
            f"D{index}": f"identity-dimension-ref:{index}"
            for index in range(1, 9)
        },
        "skill_refs": sorted(set(skill_refs)),
        "resource_refs": sorted(set(resource_refs)),
        "verified": True,
        "central_real_name_identity_graph": False,
        "member_plaintext_embedded": False,
        "resource_access_mode": (
            "SYSTEM_BOUND_IDENTITY_PACKET_CAPABILITY_AND_RESOURCE_REFS_ONLY"
        ),
    }
    packet["packet_sha256"] = sha256_object(packet)
    return packet


def validate_identity_tensor_packet(
    packet: Mapping[str, Any],
    *,
    shared_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate identity tensor shape without reading personal plaintext."""

    contract = dict(shared_contract or build_shared_sovereign_ai_skill_contract())
    expected_dimensions = {f"D{index}" for index in range(1, 9)}
    dimensions = packet.get("dimensions")
    if not isinstance(dimensions, Mapping) or set(dimensions) != expected_dimensions:
        raise ThreeMajorSceneProductError("IDENTITY_EXACT_8D_REQUIRED")
    if any(
        not isinstance(value, str) or not value.startswith("identity-dimension-ref:")
        for value in dimensions.values()
    ):
        raise ThreeMajorSceneProductError("IDENTITY_DIMENSION_REFS_REQUIRED")
    if (
        packet.get("verified") is not True
        or packet.get("central_real_name_identity_graph") is not False
        or packet.get("member_plaintext_embedded") is not False
        or packet.get("resource_access_mode") != contract["resource_access_mode"]
    ):
        raise ThreeMajorSceneProductError("IDENTITY_SOVEREIGNTY_BOUNDARY_INVALID")
    skill_refs = set(packet.get("skill_refs") or ())
    if not set(contract["skills"]).issubset(skill_refs):
        raise ThreeMajorSceneProductError("IDENTITY_SHARED_SKILLS_REQUIRED")
    supplied_hash = packet.get("packet_sha256")
    unhashed = dict(packet)
    unhashed.pop("packet_sha256", None)
    if supplied_hash != sha256_object(unhashed):
        raise ThreeMajorSceneProductError("IDENTITY_PACKET_SHA256_MISMATCH")
    forbidden = _find_forbidden_key(packet)
    if forbidden:
        raise ThreeMajorSceneProductError(f"IDENTITY_PLAINTEXT_FORBIDDEN:{forbidden}")
    return {
        "state": "PASS_VERIFIED_8D_IDENTITY_TENSOR",
        "identity_packet_ref": packet["identity_packet_ref"],
        "packet_sha256": supplied_hash,
    }


def _scene_preconditions(
    scene: str,
    authority_refs: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    if scene in {"public_benefit", "merchant"}:
        missing.extend(
            key for key in FUND_PRECONDITIONS if not authority_refs.get(key)
        )
    if scene in {"public_benefit", "property"} and not authority_refs.get(
        "legal_document_source_refs"
    ):
        missing.append("legal_document_source_refs")
    if scene == "property" and not authority_refs.get(
        "management_committee_branch_total_field_ref"
    ):
        missing.append("management_committee_branch_total_field_ref")
    return sorted(set(missing))


def _unsigned_packet_hash(packet: Mapping[str, Any]) -> str:
    unsigned = _copy_json(packet)
    unsigned["D8"]["integrity"]["packet_sha256"] = None
    return sha256_object(unsigned)


def build_scene_packet(
    scene: str,
    *,
    identity_packet: Mapping[str, Any],
    intent_text: str,
    event_type: str,
    event_refs: Sequence[str],
    authority_refs: Mapping[str, Any] | None = None,
    nonce: str,
    created_at: str,
    ttl_seconds: int = 3600,
    product_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one executable D1-D8 scene packet."""

    product = dict(product_config or load_product_config())
    scenes = product["scenes"]
    if scene not in scenes:
        raise ThreeMajorSceneProductError("SCENE_UNSUPPORTED")
    if not str(intent_text).strip():
        raise ThreeMajorSceneProductError("INTENT_REQUIRED")
    if not str(event_type).strip() or not event_refs:
        raise ThreeMajorSceneProductError("EVENT_AND_REFERENCE_REQUIRED")
    if len(nonce) < 16:
        raise ThreeMajorSceneProductError("NONCE_MINIMUM_LENGTH_REQUIRED")
    if ttl_seconds < 60 or ttl_seconds > 86400:
        raise ThreeMajorSceneProductError("TTL_OUT_OF_RANGE")

    contract = build_shared_sovereign_ai_skill_contract(product)
    identity_receipt = validate_identity_tensor_packet(
        identity_packet, shared_contract=contract
    )
    refs = _copy_json(dict(authority_refs or {}))
    forbidden = _find_forbidden_key(refs)
    if forbidden:
        raise ThreeMajorSceneProductError(
            f"AUTHORITY_REF_PLAINTEXT_FORBIDDEN:{forbidden}"
        )
    missing = _scene_preconditions(scene, refs)
    created = _utc(created_at)
    expires = created + timedelta(seconds=ttl_seconds)
    profile = scenes[scene]

    service_candidate = build_audiovisual_natural_language_service_candidate(
        intent_text=intent_text,
        input_mode="text",
        requested_scene={
            "public_benefit": "association_scene",
            "property": "property_scene",
            "merchant": "business_scene",
        }[scene],
        evidence_refs=list(event_refs),
    )
    if service_candidate["STATE"] != "PASS_CANDIDATE":
        raise ThreeMajorSceneProductError("EXISTING_SERVICE_DESK_NOT_READY")

    state = "PRECONDITION_MISSING" if missing else "CANDIDATE_READY"
    packet = {
        "schema_version": "w7tp.three-major-scene-packet-candidate.v1",
        "packet_type": profile["packet_type"],
        "scene": scene,
        "shared_skill_contract_ref": contract["contract_ref"],
        "shared_skill_contract_sha256": contract["contract_sha256"],
        "D1": {
            "TOTAL_FIELD_DESCRIPTION": profile["product_positioning"],
            "D1_INTENT": intent_text,
            "identity_packet_ref": identity_receipt["identity_packet_ref"],
            "identity_packet_sha256": identity_receipt["packet_sha256"],
        },
        "D2": {
            "state": state,
            "missing_preconditions": missing,
            "candidate_only": True,
            "runtime_enabled": False,
        },
        "D3": {
            "D3_COORDINATE": profile["scene_ref"],
            "branch_total_field_ref": profile["branch_total_field_ref"],
            "canonical_product_root_sha256": ROOT_PACKET_SHA256,
            "canonical_product_root_reference_only": True,
        },
        "D4": {
            "required_skill_refs": list(SHARED_SKILL_REFS),
            "scene_capabilities": profile["required_capabilities"],
            "product_features": profile.get("product_features", {}),
            "event_refs": list(event_refs),
            "authority_refs": refs,
        },
        "D5": {
            "EVENT": {
                "event_type": event_type,
                "event_refs": list(event_refs),
            },
            "STATE_TRANSITION": f"INTENT_RECEIVED->{state}",
            "flow": [
                "TOTAL_FIELD_DESCRIPTION",
                "D1_INTENT",
                "D3_COORDINATE",
                "REQUIRED_SKILL_REFS",
                "EVENT",
                "STATE_TRANSITION",
                "CLOUD_FILLABLE_CODE_ZONE",
                "LOCAL_RECONSTRUCTION",
                "D7_VERIFICATION",
                "D8_RECEIPT",
            ],
        },
        "D6": {
            "CLOUD_FILLABLE_CODE_ZONE": product["cloud_fill_policy"]["allowed"],
            "cloud_fill_forbidden": product["cloud_fill_policy"]["forbidden"],
            "generative_transmission": (
                "PROTOCOL_NATIVE_8D_INTENT_FIELD_PACKET_WITH_"
                "RECONSTRUCTION_AND_VERIFICATION"
            ),
            "ordinary_file_movement": False,
            "cloud_sync": False,
            "backup": False,
            "download_decryption": False,
            "cloud_payload": (
                "INCOMPLETE_DEIDENTIFIED_REFERENCE_ONLY_8D_STATE_PACKET"
            ),
        },
        "D7": {
            "D7_VERIFICATION": (
                "LOCAL_IDENTITY_BOUNDARY_SCENE_RULE_AND_TOTAL_FIELD_REVIEW"
            ),
            "fund_conservation_contract": product["fund_conservation_contract"],
            "precondition_policy": (
                "MISSING_AUTHORITY_INPUT_RETURNS_PRECONDITION_MISSING"
            ),
            "raw_media_to_cloud": False,
            "member_plaintext_to_cloud": False,
            "database_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "canonical_write": False,
        },
        "D8": {
            "D8_RECEIPT": "TOTAL_FIELD_CANDIDATE_RECEIPT_REQUIRED",
            "authorization_id": AUTHORIZATION_ID,
            "nonce": nonce,
            "ttl_seconds": ttl_seconds,
            "created_at": created.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "candidate_only": True,
            "canonical_status": CANONICAL_STATUS,
            "integrity": {
                "algorithm": "sha256",
                "packet_sha256": None,
            },
        },
    }
    packet["D8"]["integrity"]["packet_sha256"] = _unsigned_packet_hash(packet)
    return packet


def build_public_benefit_scene_packet(**kwargs: Any) -> dict[str, Any]:
    return build_scene_packet("public_benefit", **kwargs)


def build_property_scene_packet(**kwargs: Any) -> dict[str, Any]:
    return build_scene_packet("property", **kwargs)


def build_merchant_scene_packet(**kwargs: Any) -> dict[str, Any]:
    return build_scene_packet("merchant", **kwargs)


def apply_scene_workflow_event(
    scene: str,
    workflow: str,
    *,
    current_state: str,
    target_state: str,
    event_ref: str,
    product_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one configured reference-only scene workflow transition."""

    product = dict(product_config or load_product_config())
    try:
        catalog = product["scenes"][scene]["product_features"][
            "workflow_catalog"
        ]
        allowed = catalog[workflow]
    except KeyError as exc:
        raise ThreeMajorSceneProductError("WORKFLOW_UNSUPPORTED") from exc
    transition = f"{current_state}->{target_state}"
    if transition not in allowed:
        raise ThreeMajorSceneProductError("WORKFLOW_TRANSITION_FORBIDDEN")
    if not event_ref or _find_forbidden_key({"event_ref": event_ref}):
        raise ThreeMajorSceneProductError("WORKFLOW_EVENT_REF_REQUIRED")
    result = {
        "schema_version": "w7tp.scene-workflow-transition-candidate.v1",
        "scene": scene,
        "workflow": workflow,
        "event_ref": event_ref,
        "previous_state": current_state,
        "candidate_state": target_state,
        "transition": transition,
        "candidate_only": True,
        "runtime_enabled": False,
        "database_write": False,
        "canonical_write": False,
    }
    result["transition_sha256"] = sha256_object(result)
    return result


def parse_scene_packet(
    value: str | bytes | Mapping[str, Any],
    *,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict[str, Any]:
    """Parse and schema-validate one packet."""

    if isinstance(value, Mapping):
        packet = _copy_json(dict(value))
    else:
        try:
            packet = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ThreeMajorSceneProductError("PACKET_JSON_INVALID") from exc
    if not isinstance(packet, dict):
        raise ThreeMajorSceneProductError("PACKET_OBJECT_REQUIRED")
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(packet),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path)
        raise ThreeMajorSceneProductError(f"PACKET_SCHEMA_INVALID:{path or '$'}")
    return packet


def verify_scene_packet(
    packet_value: str | bytes | Mapping[str, Any],
    *,
    identity_packet: Mapping[str, Any],
    now: str,
    replay_ledger: MutableSet[str] | None = None,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict[str, Any]:
    """Verify integrity, temporal validity, replay, identity, and boundaries."""

    packet = parse_scene_packet(packet_value, schema_path=schema_path)
    supplied_hash = packet["D8"]["integrity"]["packet_sha256"]
    checks = {
        "schema": "PASS",
        "integrity": (
            "PASS" if supplied_hash == _unsigned_packet_hash(packet) else "FAIL"
        ),
        "identity": "PASS",
        "temporal": "PASS",
        "replay": "PASS",
        "privacy_boundary": "PASS",
        "authority_boundary": "PASS",
    }
    identity_receipt = validate_identity_tensor_packet(identity_packet)
    if (
        identity_receipt["identity_packet_ref"]
        != packet["D1"]["identity_packet_ref"]
        or identity_receipt["packet_sha256"]
        != packet["D1"]["identity_packet_sha256"]
    ):
        checks["identity"] = "FAIL"
    current = _utc(now)
    if not (
        _utc(packet["D8"]["created_at"])
        <= current
        <= _utc(packet["D8"]["expires_at"])
    ):
        checks["temporal"] = "FAIL"
    ledger = replay_ledger if replay_ledger is not None else set()
    nonce = packet["D8"]["nonce"]
    if nonce in ledger:
        checks["replay"] = "FAIL"
    forbidden = _find_forbidden_key(packet)
    if forbidden:
        checks["privacy_boundary"] = "FAIL"
    if (
        packet["D7"]["database_write"] is not False
        or packet["D7"]["deploy"] is not False
        or packet["D7"]["restart"] is not False
        or packet["D7"]["router_write"] is not False
        or packet["D7"]["canonical_write"] is not False
        or packet["D8"]["candidate_only"] is not True
    ):
        checks["authority_boundary"] = "FAIL"
    failed = sorted(key for key, status in checks.items() if status != "PASS")
    if not failed:
        ledger.add(nonce)
    decision = (
        "REJECT"
        if failed
        else (
            "PRECONDITION_MISSING"
            if packet["D2"]["missing_preconditions"]
            else "PASS_CANDIDATE"
        )
    )
    receipt = {
        "schema_version": "w7tp.three-major-scene-verification-receipt.v1",
        "scene": packet["scene"],
        "packet_sha256": supplied_hash,
        "decision": decision,
        "checks": checks,
        "failed_checks": failed,
        "missing_preconditions": packet["D2"]["missing_preconditions"],
        "runtime_enabled": False,
        "database_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "canonical_write": False,
    }
    receipt["receipt_sha256"] = sha256_object(receipt)
    return receipt


def reconstruct_scene_intent_field(
    packet: Mapping[str, Any],
    *,
    identity_packet: Mapping[str, Any],
    now: str,
    replay_ledger: MutableSet[str] | None = None,
) -> dict[str, Any]:
    """Locally reconstruct one scene state from its D1-D8 packet."""

    verification = verify_scene_packet(
        packet,
        identity_packet=identity_packet,
        now=now,
        replay_ledger=replay_ledger,
    )
    if verification["decision"] == "REJECT":
        state = "RECONSTRUCTION_REJECTED"
    elif verification["decision"] == "PRECONDITION_MISSING":
        state = "RECONSTRUCTED_PRECONDITION_MISSING"
    else:
        state = "RECONSTRUCTED_CANDIDATE_READY_FOR_TOTAL_FIELD"
    reconstruction = {
        "schema_version": "w7tp.three-major-scene-local-reconstruction.v1",
        "scene": packet["scene"],
        "state": state,
        "flow_projection": {
            "TOTAL_FIELD_DESCRIPTION": packet["D1"]["TOTAL_FIELD_DESCRIPTION"],
            "D1_INTENT": packet["D1"]["D1_INTENT"],
            "D3_COORDINATE": packet["D3"]["D3_COORDINATE"],
            "REQUIRED_SKILL_REFS": packet["D4"]["required_skill_refs"],
            "EVENT": packet["D5"]["EVENT"],
            "STATE_TRANSITION": packet["D5"]["STATE_TRANSITION"],
            "CLOUD_FILLABLE_CODE_ZONE": packet["D6"][
                "CLOUD_FILLABLE_CODE_ZONE"
            ],
            "LOCAL_RECONSTRUCTION": state,
            "D7_VERIFICATION": verification["checks"],
            "D8_RECEIPT": verification["receipt_sha256"],
        },
        "scene_capabilities": packet["D4"]["scene_capabilities"],
        "product_features": packet["D4"]["product_features"],
        "missing_preconditions": verification["missing_preconditions"],
        "verification_receipt": verification,
        "runtime_enabled": False,
        "canonical_status": CANONICAL_STATUS,
    }
    reconstruction["reconstruction_sha256"] = sha256_object(reconstruction)
    return reconstruction


def build_code_gap_manifest(product_config: Mapping[str, Any]) -> dict[str, Any]:
    """Declare cloud-fill boundaries without inventing a provider response."""

    manifest = {
        "schema_version": "w7tp.code-gap-manifest.v1",
        "authorization_id": AUTHORIZATION_ID,
        "gaps": [],
        "allowed_code_zones": product_config["cloud_fill_policy"]["allowed"],
        "forbidden_code_zones": product_config["cloud_fill_policy"]["forbidden"],
        "cloud_fill_required": False,
        "status": "NO_GENERAL_CODE_GAPS_AFTER_LOCAL_IMPLEMENTATION",
        "member_plaintext_included": False,
        "secret_included": False,
        "authority_rules_included": False,
        "canonical_write": False,
    }
    manifest["manifest_sha256"] = sha256_object(manifest)
    return manifest


def validate_cloud_fill_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one future bounded cloud patch candidate."""

    forbidden = _find_forbidden_key(candidate)
    if forbidden:
        raise ThreeMajorSceneProductError(f"CLOUD_PLAINTEXT_FORBIDDEN:{forbidden}")
    zones = set(candidate.get("code_zones") or ())
    if zones & FORBIDDEN_CLOUD_ZONES:
        raise ThreeMajorSceneProductError("CLOUD_AUTHORITY_ZONE_FORBIDDEN")
    if (
        candidate.get("candidate_only") is not True
        or candidate.get("formal_execution_authority") is not False
        or candidate.get("database_write") is not False
        or candidate.get("deploy") is not False
        or candidate.get("restart") is not False
        or candidate.get("router_write") is not False
        or candidate.get("canonical_write") is not False
    ):
        raise ThreeMajorSceneProductError("CLOUD_AUTHORITY_CLAIM_FORBIDDEN")
    return {
        "state": "PASS_BOUNDED_CLOUD_FILL_CANDIDATE",
        "candidate_sha256": sha256_object(candidate),
    }


def build_cloud_fill_request(code_gap_manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deidentified request model, even when no cloud call is needed."""

    request = {
        "schema_version": "w7tp.cloud-fill-request.v1",
        "request_state": (
            "NOT_DISPATCHED_NO_GENERAL_CODE_GAPS"
            if not code_gap_manifest.get("gaps")
            else "CANDIDATE_DISPATCH_REQUIRES_PROVIDER"
        ),
        "code_gap_manifest_ref": (
            f"sha256:{code_gap_manifest['manifest_sha256']}"
        ),
        "allowed_code_zones": code_gap_manifest["allowed_code_zones"],
        "requested_gaps": code_gap_manifest["gaps"],
        "payload_mode": "DEIDENTIFIED_INCOMPLETE_REFERENCE_ONLY",
        "member_plaintext_included": False,
        "secret_included": False,
        "complete_system_data_included": False,
        "authority_rules_included": False,
        "candidate_only": True,
        "formal_execution_authority": False,
        "database_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "canonical_write": False,
    }
    request["request_sha256"] = sha256_object(request)
    return request


def build_cloud_fill_receipt(code_gap_manifest: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "schema_version": "w7tp.cloud-fill-receipt.v1",
        "state": "NOT_REQUESTED_NO_GENERAL_CODE_GAPS",
        "code_gap_manifest_sha256": code_gap_manifest["manifest_sha256"],
        "provider_response_present": False,
        "fake_provider_response": False,
        "member_plaintext_sent": False,
        "secret_sent": False,
        "authority_rule_sent": False,
        "candidate_only": True,
        "formal_execution_authority": False,
        "canonical_write": False,
    }
    receipt["receipt_sha256"] = sha256_object(receipt)
    return receipt


def _gateway_request(
    packet: Mapping[str, Any], run_id: str
) -> tuple[dict[str, Any], str]:
    scene = packet["scene"]
    packet_sha256 = packet["D8"]["integrity"]["packet_sha256"]
    event_ref = f"event:three-major-scenes:{scene}:{run_id}"
    domain_ref = f"observation-domain:three-major-scenes:{scene}:isolated:v1"
    request = {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": event_ref,
            "observation_domain_ref": domain_ref,
            "dimensions": {
                f"D{index}_ref": f"field/tfct/D{index}/v0_1"
                for index in range(1, 9)
            },
            "constraint_hypergraph_ref": "constraints/tfct/runtime-hypergraph/v0_1",
            "convergence_operator_ref": "convergence/tfct/finite-fixed-point/v0_1",
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "source_mode": "TOTAL_FIELD_PULL",
        "event": {
            "event_id": f"event-id:{scene}:{run_id}",
            "event_ref": event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical-time:{run_id}:{scene}",
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": {
            f"D{index}": packet[f"D{index}"] for index in range(1, 9)
        },
        "context": {
            "request_ref": f"request-ref:three-major-scenes:{scene}:{run_id}",
            "packet_sha256": packet_sha256,
            "authorization_ref": AUTHORIZATION_ID,
        },
        "adi_requested": False,
    }
    return request, domain_ref


def build_total_field_candidate_receipt(
    packets: Mapping[str, Mapping[str, Any]],
    *,
    run_id: str,
) -> dict[str, Any]:
    """Call the sole gateway and retain candidate-only evidence."""

    scene_results: dict[str, Any] = {}
    for scene, packet in packets.items():
        request, domain_ref = _gateway_request(packet, run_id)
        result = receive_candidate(
            request,
            previous_state=request["resolved_fields"],
            observation_domains={
                domain_ref: {"configured": True, "observations": {}}
            },
        )
        result_gte = result.get("gte") or {}
        commit_applied = result.get("commit_applied") is True
        scene_results[scene] = {
            "gateway_final_decision": result.get("final_decision"),
            "gateway_lifecycle": result_gte.get("lifecycle"),
            "gateway_commit_applied": commit_applied,
            "source_adoption": (
                "HOLD_GATEWAY_COMMIT_OUT_OF_SCOPE"
                if commit_applied
                else "CANDIDATE_ONLY"
            ),
            "observation_domain_ref": domain_ref,
            "packet_sha256": packet["D8"]["integrity"]["packet_sha256"],
            "gateway_result_sha256": sha256_object(result),
        }
    receipt = {
        "schema_version": "w7tp.three-major-scenes-total-field-receipt.v1",
        "run_id": run_id,
        "receiver_ref": "tools.total_field_candidate_gateway.receive_candidate",
        "scene_results": scene_results,
        "canonical_status": CANONICAL_STATUS,
        "database_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "canonical_write": False,
    }
    receipt["receipt_sha256"] = sha256_object(receipt)
    return receipt


def build_requirements_audit(
    *,
    product: Mapping[str, Any],
    packets: Mapping[str, Mapping[str, Any]],
    reconstructions: Mapping[str, Mapping[str, Any]],
    total_field_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce an evidence-backed source-candidate completion audit."""

    public_features = product["scenes"]["public_benefit"]["product_features"]
    five_units = {
        "dedicated_service_team",
        "commercial_volunteer_team",
        "delivery_service",
        "renyi_cafe_branch",
        "community_digital_development_fund",
    }
    checks = {
        "exact_three_scene_packets": set(packets) == set(SCENE_FILES),
        "one_shared_skill_contract": len(
            {packet["shared_skill_contract_sha256"] for packet in packets.values()}
        )
        == 1,
        "verified_8d_identity_reference": all(
            packet["D1"]["identity_packet_ref"].startswith("identity-packet-ref:")
            for packet in packets.values()
        ),
        "d1_to_d8_present": all(
            all(f"D{index}" in packet for index in range(1, 9))
            for packet in packets.values()
        ),
        "existing_audiovisual_service_desk_reused": (
            product["audiovisual_natural_language_service_desk"][
                "existing_entry_ref"
            ]
            == "entry_ref:taiji04_local_audiovisual_natural_language"
        ),
        "three_party_authority_separated": (
            product["three_party_collaboration"]["xiaoj_cloud_candidate"][
                "total_field_authority"
            ]
            is False
        ),
        "five_wuchang_community_core_units": five_units.issubset(public_features),
        "delivery_system_state_machine": bool(
            public_features["delivery_service"]["states"]
            and public_features["delivery_service"]["transitions"]
        ),
        "workflow_catalogs_all_scenes": all(
            product["scenes"][scene]["product_features"].get("workflow_catalog")
            for scene in SCENE_FILES
        ),
        "fund_111_local_only": (
            product["fund_conservation_contract"]["ratio"] == "1:1:1"
            and product["fund_conservation_contract"]["authority"]
            == "LOCAL_TOTAL_FIELD_ONLY"
            and product["fund_conservation_contract"]["cloud_fill"]
            == "FORBIDDEN"
        ),
        "cloud_boundary_reference_only": all(
            packet["D6"]["cloud_payload"]
            == "INCOMPLETE_DEIDENTIFIED_REFERENCE_ONLY_8D_STATE_PACKET"
            for packet in packets.values()
        ),
        "local_reconstruction_all_scenes": set(reconstructions)
        == set(SCENE_FILES),
        "sole_total_field_gateway": (
            total_field_receipt["receiver_ref"]
            == "tools.total_field_candidate_gateway.receive_candidate"
        ),
        "no_gateway_commit": all(
            result["gateway_commit_applied"] is False
            for result in total_field_receipt["scene_results"].values()
        ),
        "no_runtime_or_canonical_write": all(
            packet["D2"]["runtime_enabled"] is False
            and packet["D7"]["canonical_write"] is False
            for packet in packets.values()
        ),
    }
    missing_preconditions = {
        scene: reconstruction["missing_preconditions"]
        for scene, reconstruction in reconstructions.items()
    }
    audit = {
        "schema_version": "w7tp.three-major-scenes-requirements-audit.v1",
        "source_candidate_completion": (
            "PASS" if all(checks.values()) else "HOLD_REQUIREMENT_GAP"
        ),
        "activation_readiness": "HOLD_PRECONDITION_MISSING",
        "checks": {
            key: "PASS" if value else "FAIL" for key, value in checks.items()
        },
        "missing_authority_preconditions": missing_preconditions,
        "runtime_enabled": False,
        "canonical_status": CANONICAL_STATUS,
    }
    audit["audit_sha256"] = sha256_object(audit)
    return audit


def build_fund_authority_contract(*, created_at: str) -> dict[str, Any]:
    """Build the Founder-instructed local-only symbolic 1:1:1 contract."""

    timestamp = _utc(created_at).isoformat().replace("+00:00", "Z")
    contract = {
        "schema_version": "w7tp.local-fund-conservation-authority.v1",
        "authority_ref": FUND_AUTHORITY_REF,
        "founder_instruction_ref": (
            f"founder-instruction-ref:{AUTHORIZATION_ID}:fund-conservation"
        ),
        "authority": "LOCAL_TOTAL_FIELD_ONLY",
        "canonical_status": "LOCAL_TOTAL_FIELD_AUTHORITY_CANDIDATE_NOT_CANONICAL",
        "conservation_rule_id": "TOTAL_FIELD_FUND_CONSERVATION_1_TO_1_TO_1_V1",
        "ratio": "1:1:1",
        "base_unit": "法幣",
        "symbolic_conservation_rule": (
            "1 consumer_happiness_coin_quota = "
            "1 merchant_ticket_generation_quota = "
            "1 fund_fiat_guarantee_reserve_unit"
        ),
        "consumer_happiness_coin_state_ref": (
            "state-ref:consumer-happiness-coin:caller-supplied:v1"
        ),
        "merchant_ticket_generation_quota_ref": (
            "quota-ref:merchant-ticket-generation:caller-supplied:v1"
        ),
        "fund_fiat_guarantee_reserve_ref": (
            "reserve-ref:fund-fiat-guarantee:caller-supplied:v1"
        ),
        "blood_engine_rule_ref": (
            "rule-ref:community-blood-engine:local-total-field:v1"
        ),
        "bank_account_ref": "bank-account-ref:caller-supplied:opaque:v1",
        "ring_fence_evidence_ref": (
            "evidence-ref:fiat-guarantee-ring-fence:caller-supplied:v1"
        ),
        "audit_rule_ref": "audit-rule-ref:three-way-conservation:local:v1",
        "issuance_gate": {
            "state": "CLOSED_UNTIL_LOCAL_VERIFICATION",
            "requires": [
                "opaque_bank_account_ref",
                "fiat_guarantee_ring_fence_evidence_ref",
                "three_way_reconciliation_pass",
                "founder_or_delegated_local_total_field_authorization",
            ],
        },
        "use_gate": {
            "state": "CLOSED_UNTIL_MATCHED_QUOTA_RESERVED",
            "requires": [
                "consumer_quota_state_ref",
                "merchant_ticket_quota_ref",
                "fiat_reserve_state_ref",
            ],
        },
        "release_or_expiry_gate": {
            "state": "LOCAL_TOTAL_FIELD_DECISION_REQUIRED",
            "requires": [
                "three_way_reconciliation_pass",
                "auditable_release_or_expiry_event_ref",
            ],
        },
        "three_way_reconciliation_contract": {
            "formula_ref": "formula-ref:fund-conservation-1-to-1-to-1:v1",
            "all_three_states_required": True,
            "imbalance_tolerance": "ZERO_IN_BASE_UNIT",
            "actual_amounts_embedded": False,
        },
        "verification_contract": {
            "verifier": "LOCAL_TOTAL_FIELD_ONLY",
            "cloud_fill": "FORBIDDEN",
            "checks": [
                "three_refs_present",
                "ratio_exactly_1_to_1_to_1",
                "base_unit_is_fiat",
                "ring_fence_evidence_verified_locally",
                "reconciliation_pass",
                "no_member_or_bank_plaintext",
            ],
        },
        "failure_states": [
            "PRECONDITION_MISSING",
            "REFERENCE_UNVERIFIED",
            "RING_FENCE_EVIDENCE_MISSING",
            "THREE_WAY_IMBALANCE",
            "ISSUANCE_GATE_CLOSED",
            "USE_GATE_CLOSED",
            "RELEASE_OR_EXPIRY_GATE_CLOSED",
            "PLAINTEXT_BOUNDARY_VIOLATION",
            "CLOUD_FILL_FORBIDDEN",
        ],
        "member_plaintext": False,
        "bank_account_plaintext": False,
        "actual_issuance_quota": False,
        "cloud_fill": "FORBIDDEN",
        "activated": False,
        "D8": {
            "envelope": "LOCAL_TOTAL_FIELD_AUTHORITY_CANDIDATE",
            "authorization_id": AUTHORIZATION_ID,
            "created_at": timestamp,
            "runtime_enabled": False,
            "canonical_write": False,
        },
    }
    contract["contract_sha256"] = sha256_object(contract)
    return contract


def build_property_statutory_source_manifest(
    *, retrieved_at: str
) -> dict[str, Any]:
    """Build one versioned manifest from verified official source projections."""

    timestamp = _utc(retrieved_at).isoformat().replace("+00:00", "Z")
    required_fields = {
        "jurisdiction",
        "issuing_authority",
        "document_title",
        "official_url",
        "version_or_effective_date",
        "local_reference_or_hash",
        "applicable_scene",
        "verification_status",
    }
    sources = _copy_json(PROPERTY_STATUTORY_SOURCES)
    for source in sources:
        if not required_fields.issubset(source):
            raise ThreeMajorSceneProductError("STATUTORY_SOURCE_FIELDS_REQUIRED")
        parsed = urlparse(source["official_url"])
        if (
            parsed.scheme != "https"
            or parsed.hostname not in OFFICIAL_PROPERTY_SOURCE_HOSTS
        ):
            raise ThreeMajorSceneProductError("STATUTORY_SOURCE_NOT_OFFICIAL")
        if not source["local_reference_or_hash"].startswith("sha256:"):
            raise ThreeMajorSceneProductError("STATUTORY_SOURCE_HASH_REQUIRED")
        source["retrieved_at"] = timestamp

    manifest = {
        "schema_version": "w7tp.property-statutory-source-manifest.v1",
        "manifest_ref": (
            "manifest-ref:property-statutory-sources:tw-new-taipei:v1"
        ),
        "jurisdiction_scope": ["TAIWAN", "NEW_TAIPEI_CITY"],
        "sources": sources,
        "source_count": len(sources),
        "missing_preconditions": _copy_json(PROPERTY_STATUTORY_MISSING),
        "verification_status": "VERIFIED_OR_EXACT_MISSING_LIST",
        "legal_effect_boundary": (
            "正式文件內容及實際適用性仍由總場與適用地主管機關確認"
        ),
        "cloud_fill": "FORBIDDEN",
        "generated_content_used": False,
        "member_plaintext": False,
        "activated": False,
        "canonical_status": CANONICAL_STATUS,
        "retrieved_at": timestamp,
    }
    manifest["manifest_sha256"] = sha256_object(manifest)
    return manifest


def build_committee_branch_reference_contract(
    *, created_at: str
) -> dict[str, Any]:
    """Build the one-committee/one-branch caller-supplied reference contract."""

    timestamp = _utc(created_at).isoformat().replace("+00:00", "Z")
    contract = {
        "schema_version": "w7tp.committee-branch-total-field-reference.v1",
        "contract_ref": COMMITTEE_BRANCH_CONTRACT_REF,
        "rule": "ONE_COMMITTEE=ONE_BRANCH_TOTAL_FIELD",
        "committee_branch_total_field_ref": (
            "caller-supplied:committee-branch-total-field-ref"
        ),
        "observation_domain_ref": "caller-supplied:observation-domain-ref",
        "committee_packet_ref": "caller-supplied:committee-packet-ref",
        "family_minimum_organization_field_ref": (
            "caller-supplied:family-minimum-organization-field-ref"
        ),
        "property_scene_packet_ref": (
            "caller-supplied:property-scene-packet-ref"
        ),
        "authority_scope": (
            "REFERENCE_VALIDATION_AND_ISOLATED_CANDIDATE_BINDING_ONLY"
        ),
        "lifecycle": "UNBOUND_CALLER_SUPPLIED_REFERENCE_CONTRACT",
        "effective_at": "caller-supplied:effective-at",
        "expires_at": "caller-supplied:expires-at",
        "verification_contract": {
            "caller_supplied_references_required": True,
            "opaque_references_only": True,
            "one_committee_maps_to_exactly_one_branch_total_field": True,
            "observation_domain_must_be_configured": True,
            "property_scene_packet_integrity_required": True,
            "authority_scope_must_not_exceed_caller_grant": True,
            "effective_window_required": True,
            "total_field_review_required": True,
        },
        "hardcoded_community_identity": False,
        "hardcoded_address": False,
        "member_plaintext": False,
        "runtime_enabled": False,
        "activated": False,
        "canonical_status": CANONICAL_STATUS,
        "D8": {
            "envelope": "CALLER_SUPPLIED_REFERENCE_CONTRACT",
            "authorization_id": AUTHORIZATION_ID,
            "created_at": timestamp,
            "canonical_write": False,
        },
    }
    contract["contract_sha256"] = sha256_object(contract)
    return contract


def _fund_projection(contract: Mapping[str, Any]) -> dict[str, str]:
    return {
        "fund_rule_ref": contract["authority_ref"],
        "blood_engine_rule_ref": contract["blood_engine_rule_ref"],
        "bank_account_ref": contract["bank_account_ref"],
        "ring_fence_evidence_ref": contract["ring_fence_evidence_ref"],
        "happiness_coin_issuance_rule_ref": (
            contract["consumer_happiness_coin_state_ref"]
        ),
        "merchant_ticket_limit_rule_ref": (
            contract["merchant_ticket_generation_quota_ref"]
        ),
        "reconciliation_formula_ref": contract[
            "three_way_reconciliation_contract"
        ]["formula_ref"],
        "audit_rule_ref": contract["audit_rule_ref"],
    }


def build_activation_binding_supplement(
    *,
    run_id: str,
    packet_hashes: Mapping[str, str],
    fund_contract: Mapping[str, Any],
    fund_file_sha256: str,
    statutory_manifest: Mapping[str, Any],
    statutory_file_sha256: str,
    committee_contract: Mapping[str, Any],
    committee_file_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    """Project the three new references onto the immutable scene packets."""

    fund_refs = _fund_projection(fund_contract)
    statutory_ref = statutory_manifest["manifest_ref"]
    committee_ref = committee_contract["contract_ref"]
    projections = {
        "public_benefit": {
            **fund_refs,
            "legal_document_source_refs": [statutory_ref],
        },
        "property": {
            "legal_document_source_refs": [statutory_ref],
            "management_committee_branch_total_field_ref": committee_ref,
        },
        "merchant": dict(fund_refs),
    }
    unresolved = {
        scene: _scene_preconditions(scene, refs)
        for scene, refs in projections.items()
    }
    if any(unresolved.values()):
        raise ThreeMajorSceneProductError("ACTIVATION_REFERENCES_NOT_BOUND")
    timestamp = _utc(created_at).isoformat().replace("+00:00", "Z")
    supplement = {
        "schema_version": "w7tp.three-major-scene-activation-binding.v1",
        "run_id": run_id,
        "base_packets_immutable": True,
        "base_packet_sha256": dict(packet_hashes),
        "reference_contracts": {
            "fund_authority_ref": fund_contract["authority_ref"],
            "fund_contract_file_sha256": fund_file_sha256,
            "property_statutory_source_manifest_ref": statutory_ref,
            "property_statutory_source_manifest_file_sha256": (
                statutory_file_sha256
            ),
            "committee_branch_reference_contract_ref": committee_ref,
            "committee_branch_reference_contract_file_sha256": (
                committee_file_sha256
            ),
        },
        "authority_reference_projection": projections,
        "unresolved_scene_precondition_keys": unresolved,
        "activation_preconditions": "BOUND",
        "statutory_missing": statutory_manifest["missing_preconditions"],
        "cloud_fill_used": False,
        "member_plaintext": False,
        "bank_account_plaintext": False,
        "runtime_enabled": False,
        "activated": False,
        "canonical_status": CANONICAL_STATUS,
        "created_at": timestamp,
    }
    supplement["supplement_sha256"] = sha256_object(supplement)
    return supplement


def _activation_gateway_request(
    supplement: Mapping[str, Any], run_id: str
) -> tuple[dict[str, Any], str]:
    event_ref = f"event:three-major-scenes:activation-binding:{run_id}"
    domain_ref = (
        "observation-domain:three-major-scenes:activation-binding:isolated:v1"
    )
    dimensions = {
        "D1": {
            "intent_ref": "intent-ref:bind-three-activation-preconditions"
        },
        "D2": {"state_ref": "state-ref:activation-preconditions-bound"},
        "D3": {"run_ref": f"run-ref:{run_id}"},
        "D4": {
            "supplement_ref": (
                f"sha256:{supplement['supplement_sha256']}"
            )
        },
        "D5": {"action_ref": "action-ref:reference-binding-only"},
        "D6": {"cloud_fill_ref": "policy-ref:cloud-fill-forbidden"},
        "D7": {"verification_ref": "verification-ref:local-total-field"},
        "D8": {"envelope_ref": "envelope-ref:candidate-not-activated"},
    }
    request = {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": event_ref,
            "observation_domain_ref": domain_ref,
            "dimensions": {
                f"D{index}_ref": f"field/tfct/D{index}/v0_1"
                for index in range(1, 9)
            },
            "constraint_hypergraph_ref": (
                "constraints/tfct/runtime-hypergraph/v0_1"
            ),
            "convergence_operator_ref": (
                "convergence/tfct/finite-fixed-point/v0_1"
            ),
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "source_mode": "TOTAL_FIELD_PULL",
        "event": {
            "event_id": f"event-id:activation-binding:{run_id}",
            "event_ref": event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical-time:{run_id}:activation-binding",
        },
        "rule_set_ref": "rules/tfct/reference-binding_v0_1",
        "resolved_fields": dimensions,
        "context": {
            "request_ref": (
                f"request-ref:three-major-scenes:activation-binding:{run_id}"
            ),
            "supplement_sha256": supplement["supplement_sha256"],
            "authorization_ref": AUTHORIZATION_ID,
        },
        "adi_requested": False,
    }
    return request, domain_ref


def build_total_field_activation_binding_receipt(
    supplement: Mapping[str, Any], *, run_id: str
) -> dict[str, Any]:
    """Submit the reference supplement to the existing candidate gateway."""

    request, domain_ref = _activation_gateway_request(supplement, run_id)
    result = receive_candidate(
        request,
        previous_state=request["resolved_fields"],
        observation_domains={
            domain_ref: {"configured": True, "observations": {}}
        },
    )
    commit_applied = result.get("commit_applied") is True
    if commit_applied:
        raise ThreeMajorSceneProductError("GATEWAY_COMMIT_OUT_OF_SCOPE")
    receipt = {
        "schema_version": "w7tp.total-field-activation-binding-receipt.v1",
        "run_id": run_id,
        "receiver_ref": "tools.total_field_candidate_gateway.receive_candidate",
        "supplement_sha256": supplement["supplement_sha256"],
        "gateway_final_decision": result.get("final_decision"),
        "gateway_lifecycle": (result.get("gte") or {}).get("lifecycle"),
        "gateway_commit_applied": False,
        "binding_state": "PASS_ACTIVATION_PRECONDITIONS_BOUND",
        "activation_ready": "TRUE_REFERENCE_CONTRACTS_BOUND",
        "activated": False,
        "cloud_fill_used": False,
        "member_plaintext": False,
        "bank_account_plaintext": False,
        "canonical_status": CANONICAL_STATUS,
        "gateway_result_sha256": sha256_object(result),
    }
    receipt["receipt_sha256"] = sha256_object(receipt)
    return receipt


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ThreeMajorSceneProductError(f"JSON_READ_FAILED:{path}") from exc
    if not isinstance(value, dict):
        raise ThreeMajorSceneProductError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_activation_precondition_binding(
    *,
    run_id: str,
    output_parent: str | Path = DEFAULT_RUNTIME_PARENT,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Add only reference-binding artifacts to one existing immutable run."""

    if run_id != ACTIVATION_BINDING_RUN_ID:
        raise ThreeMajorSceneProductError("ACTIVATION_BINDING_RUN_ID_MISMATCH")
    output_root = Path(output_parent) / run_id
    if not output_root.is_dir():
        raise ThreeMajorSceneProductError(f"BASE_RUN_NOT_FOUND:{output_root}")
    output_paths = {
        key: output_root / name for key, name in ACTIVATION_BINDING_FILES.items()
    }
    existing_outputs = [path.name for path in output_paths.values() if path.exists()]
    if existing_outputs:
        raise ThreeMajorSceneProductError(
            f"ACTIVATION_BINDING_OUTPUT_EXISTS:{','.join(sorted(existing_outputs))}"
        )

    base_manifest = _read_json(output_root / "MANIFEST.json")
    if base_manifest.get("run_id") != run_id:
        raise ThreeMajorSceneProductError("BASE_MANIFEST_RUN_ID_MISMATCH")
    shared_contract_path = output_root / "SHARED_SOVEREIGN_AI_SKILL_CONTRACT.json"
    if (
        _file_sha256(shared_contract_path)
        != EXPECTED_ACTIVATION_BINDING_BASE["shared_skill_contract_file_sha256"]
    ):
        raise ThreeMajorSceneProductError("SHARED_SKILL_CONTRACT_SHA256_MISMATCH")

    packets: dict[str, dict[str, Any]] = {}
    packet_hashes: dict[str, str] = {}
    for scene, filename in SCENE_FILES.items():
        packet = _read_json(output_root / filename)
        packet_hash = packet.get("D8", {}).get("integrity", {}).get(
            "packet_sha256"
        )
        expected = EXPECTED_ACTIVATION_BINDING_BASE["packet_sha256"][scene]
        if packet_hash != expected or packet_hash != _unsigned_packet_hash(packet):
            raise ThreeMajorSceneProductError(
                f"BASE_PACKET_SHA256_MISMATCH:{scene}"
            )
        packets[scene] = packet
        packet_hashes[scene] = packet_hash

    timestamp = created_at or _now_iso()
    fund_contract = build_fund_authority_contract(created_at=timestamp)
    statutory_manifest = build_property_statutory_source_manifest(
        retrieved_at=timestamp
    )
    committee_contract = build_committee_branch_reference_contract(
        created_at=timestamp
    )
    _write_json(output_paths["fund"], fund_contract)
    _write_json(output_paths["statutory"], statutory_manifest)
    _write_json(output_paths["committee"], committee_contract)

    initial_hashes = {
        key: _file_sha256(output_paths[key])
        for key in ("fund", "statutory", "committee")
    }
    supplement = build_activation_binding_supplement(
        run_id=run_id,
        packet_hashes=packet_hashes,
        fund_contract=fund_contract,
        fund_file_sha256=initial_hashes["fund"],
        statutory_manifest=statutory_manifest,
        statutory_file_sha256=initial_hashes["statutory"],
        committee_contract=committee_contract,
        committee_file_sha256=initial_hashes["committee"],
        created_at=timestamp,
    )
    _write_json(output_paths["supplement"], supplement)
    receipt = build_total_field_activation_binding_receipt(
        supplement, run_id=run_id
    )
    _write_json(output_paths["receipt"], receipt)

    artifact_keys = ("fund", "statutory", "committee", "supplement", "receipt")
    artifact_hashes = {
        key: _file_sha256(output_paths[key]) for key in artifact_keys
    }
    checksum_lines = [
        f"{artifact_hashes[key]}  {output_paths[key].name}"
        for key in artifact_keys
    ]
    output_paths["checksums"].write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )

    return {
        "STATE": "PASS_THREE_SCENE_ACTIVATION_PRECONDITIONS_BOUND",
        "RUN_ID": run_id,
        "FUND_AUTHORITY_REF": fund_contract["authority_ref"],
        "FUND_CONTRACT_SHA256": artifact_hashes["fund"],
        "STATUTORY_SOURCE_MANIFEST": str(output_paths["statutory"]),
        "STATUTORY_SOURCE_COUNT": statutory_manifest["source_count"],
        "STATUTORY_MISSING": [
            item["precondition"]
            for item in statutory_manifest["missing_preconditions"]
        ],
        "COMMITTEE_BRANCH_REFERENCE_CONTRACT": str(output_paths["committee"]),
        "COMMITTEE_REFERENCE_SHA256": artifact_hashes["committee"],
        "BINDING_SUPPLEMENT": str(output_paths["supplement"]),
        "BINDING_SUPPLEMENT_SHA256": artifact_hashes["supplement"],
        "BINDING_RECEIPT": str(output_paths["receipt"]),
        "BINDING_RECEIPT_SHA256": artifact_hashes["receipt"],
        "SHA256_SUPPLEMENT": str(output_paths["checksums"]),
        "CLOUD_FILL_USED": False,
        "ACTIVATION_READY": "TRUE_REFERENCE_CONTRACTS_BOUND",
        "ACTIVATED": False,
        "CANONICAL_STATUS": CANONICAL_STATUS,
        "FILES_CHANGED": [output_paths[key].name for key in ACTIVATION_BINDING_FILES],
    }


def write_candidate_bundle(
    *,
    run_id: str,
    output_parent: str | Path = DEFAULT_RUNTIME_PARENT,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create one immutable isolated runtime candidate bundle."""

    if not run_id or "/" in run_id or ".." in run_id:
        raise ThreeMajorSceneProductError("RUN_ID_INVALID")
    output_root = Path(output_parent) / run_id
    if output_root.exists():
        raise ThreeMajorSceneProductError(f"OUTPUT_EXISTS:{output_root}")
    output_root.mkdir(parents=True)

    product = load_product_config()
    contract = build_shared_sovereign_ai_skill_contract(product)
    identity = build_identity_tensor_packet(
        "identity-packet-ref:isolated-product-candidate",
        resource_refs=(
            "resource-ref:community-scene-candidate",
            "resource-ref:family-scene-candidate",
            "resource-ref:merchant-scene-candidate",
        ),
    )
    timestamp = created_at or _now_iso()
    timestamp_dt = _utc(timestamp)
    now = (timestamp_dt + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    packets: dict[str, dict[str, Any]] = {}
    reconstructions: dict[str, dict[str, Any]] = {}
    ledger: set[str] = set()
    for index, scene in enumerate(SCENE_FILES, start=1):
        nonce = hashlib.sha256(f"{run_id}:{scene}".encode("utf-8")).hexdigest()
        packets[scene] = build_scene_packet(
            scene,
            identity_packet=identity,
            intent_text={
                "public_benefit": (
                    "以專勤隊、商業志工隊、社區外送、仁義分店商業造血與"
                    "幸福幣治理概念支撐五常社區數位發展基金"
                ),
                "property": "建立家庭到管委會分總場的整合式物業服務候選",
                "merchant": "建立商家、菜單、訂單、票券與社區合作之營運候選",
            }[scene],
            event_type="PRODUCT_SCENE_BUILD",
            event_refs=(f"evidence-ref:{run_id}:{scene}",),
            authority_refs={},
            nonce=nonce,
            created_at=timestamp,
            ttl_seconds=3600 + index,
            product_config=product,
        )
        reconstructions[scene] = reconstruct_scene_intent_field(
            packets[scene],
            identity_packet=identity,
            now=now,
            replay_ledger=ledger,
        )

    code_gap_manifest = build_code_gap_manifest(product)
    cloud_request = build_cloud_fill_request(code_gap_manifest)
    cloud_receipt = build_cloud_fill_receipt(code_gap_manifest)
    total_field_receipt = build_total_field_candidate_receipt(
        packets, run_id=run_id
    )
    requirements_audit = build_requirements_audit(
        product=product,
        packets=packets,
        reconstructions=reconstructions,
        total_field_receipt=total_field_receipt,
    )
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))

    outputs: dict[str, Any] = {
        "SHARED_SOVEREIGN_AI_SKILL_CONTRACT.json": contract,
        "VERIFIED_8D_IDENTITY_TENSOR_CANDIDATE.json": identity,
        "THREE_MAJOR_SCENE_PACKET_SCHEMA.json": schema,
        "CODE_GAP_MANIFEST.json": code_gap_manifest,
        "CLOUD_FILL_REQUEST.json": cloud_request,
        "CLOUD_FILL_CANDIDATE_RECEIPT.json": cloud_receipt,
        "LOCAL_RECONSTRUCTION_RECEIPT.json": {
            "schema_version": "w7tp.three-major-scenes-reconstruction-bundle.v1",
            "run_id": run_id,
            "reconstructions": reconstructions,
            "canonical_status": CANONICAL_STATUS,
        },
        "TOTAL_FIELD_CANDIDATE_RECEIPT.json": total_field_receipt,
        "REQUIREMENTS_AUDIT.json": requirements_audit,
    }
    outputs.update(
        {SCENE_FILES[scene]: packet for scene, packet in packets.items()}
    )
    for name, value in outputs.items():
        _write_json(output_root / name, value)

    manifest_entries = []
    for path in sorted(output_root.iterdir()):
        manifest_entries.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "w7tp.three-major-scenes-bundle-manifest.v1",
        "run_id": run_id,
        "authorization_id": AUTHORIZATION_ID,
        "base_run_id": BASE_RUN_ID,
        "root_packet_sha256": ROOT_PACKET_SHA256,
        "outputs": manifest_entries,
        "canonical_status": CANONICAL_STATUS,
        "runtime_enabled": False,
        "database_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "canonical_write": False,
    }
    _write_json(output_root / "MANIFEST.json", manifest)

    checksum_paths = sorted(output_root.iterdir())
    checksum_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in checksum_paths
        if path.name != "SHA256SUMS"
    ]
    (output_root / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return {
        "STATE": "PASS_THREE_MAJOR_SCENE_PRODUCT_CANDIDATE_BUILT",
        "RUN_ID": run_id,
        "OUTPUT_ROOT": str(output_root),
        "PACKETS": {
            scene: packets[scene]["D8"]["integrity"]["packet_sha256"]
            for scene in packets
        },
        "CLOUD_FILL_STATUS": cloud_receipt["state"],
        "TOTAL_FIELD_RECEIPT": total_field_receipt["receipt_sha256"],
        "CANONICAL_STATUS": CANONICAL_STATUS,
        "FILES_CHANGED": sorted(path.name for path in output_root.iterdir()),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build isolated three-major-scene product candidates"
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--output-parent",
        default=str(DEFAULT_RUNTIME_PARENT),
    )
    parser.add_argument("--created-at")
    parser.add_argument(
        "--bind-activation-preconditions",
        action="store_true",
        help="Bind references onto the existing immutable authorized run",
    )
    args = parser.parse_args(argv)
    if args.bind_activation_preconditions:
        result = write_activation_precondition_binding(
            run_id=args.run_id,
            output_parent=args.output_parent,
            created_at=args.created_at,
        )
    else:
        result = write_candidate_bundle(
            run_id=args.run_id,
            output_parent=args.output_parent,
            created_at=args.created_at,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
