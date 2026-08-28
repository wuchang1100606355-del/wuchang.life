"""Deterministic XiaoJ core-supply and field-projection planning.

This module is intentionally side-effect free.  It describes the immutable
system-supplied XiaoJ core, field-local projections, and QuickClick-equivalent
merchant capabilities in Odoo terms.  It does not read member plaintext or
local trade-secret bytes, write Odoo, capture payments, or grant authority.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping


CATALOG_SCHEMA = "WUCHANG_MERCHANT_CAPABILITY_CATALOG_V1"
PLAN_SCHEMA = "WUCHANG_MERCHANT_ACTION_CANDIDATE_V1"
CORE_SUPPLY_SCHEMA = "W7TP_XIAOJ_CORE_SUPPLY_CONTRACT_CANDIDATE_V1"
FIELD_PROJECTION_SCHEMA = "W7TP_XIAOJ_FIELD_PROJECTION_CANDIDATE_V1"
LOCAL_SECRET_REQUEST_SCHEMA = "W7TP_LOCAL_TRADE_SECRET_REQUEST_CANDIDATE_V1"
DEVICE_ADMISSION_SCHEMA = "W7TP_DISTRIBUTED_COMPUTE_DEVICE_ADMISSION_CANDIDATE_V1"
TEMPLATE_APPLICATION_SCHEMA = "W7TP_FOUNDER_BASE_DEVICE_TEMPLATE_APPLICATION_CANDIDATE_V1"
GROUP_MEMBER_APPLICATION_SCHEMA = "W7TP_GROUP_MEMBER_TOTAL_FIELD_APPLICATION_CANDIDATE_V1"
GROUP_MEMBER_QUESTIONNAIRE_SCHEMA = "W7TP_GROUP_MEMBER_INTENT_FIELD_QUESTIONNAIRE_CANDIDATE_V1"
GROUP_MEMBER_PRODUCT_SCHEMA = "W7TP_GROUP_MEMBER_TOTAL_FIELD_PRODUCT_LANDING_CANDIDATE_V1"
SOVEREIGN_AI_ACCOUNT_BINDING_SCHEMA = "W7TP_SOVEREIGN_AI_MULTI_ACCOUNT_BINDING_CANDIDATE_V1"
SOVEREIGN_AI_ACCOUNT_GOVERNANCE_SCHEMA = "W7TP_SOVEREIGN_AI_MULTI_ACCOUNT_GOVERNANCE_CANDIDATE_V1"
GROUP_MEMBER_APPLICATION_ENTRY_PATH = "/wuchang/xiaoj/group-member-field-application"
GROUP_MEMBER_APPLICATION_CANDIDATE_API_PATH = "/wuchang/xiaoj/api/group-member-field-application-candidate"
GROUP_MEMBER_QUESTIONNAIRE_API_PATH = "/wuchang/xiaoj/api/group-member-intent-field-questionnaire"
SOVEREIGN_AI_ACCOUNT_BINDING_API_PATH = "/wuchang/xiaoj/api/sovereign-ai-account-binding-candidate"
SOVEREIGN_AI_ACCOUNT_GOVERNANCE_API_PATH = "/wuchang/xiaoj/api/sovereign-ai-account-governance-candidate"

REQUIRED_FOUNDER_ACCOUNT_LOGIN_SHA256 = (
    "7769a6c5044484d5d5699db34ac0bd3010a217ea6ab8371d72097aaa02785bb6"
)
ALLOWED_ACCOUNT_BINDING_TYPES = (
    "linux_user",
    "domain_admin_email",
    "chatgpt_user_email",
    "windows_user_hint",
    "vpn_node_name",
    "vpn_node_ip",
    "odoo_partner_id_after_sync",
    "line_user_id_hash_after_consent",
    "google_email_after_consent",
)
EXTERNAL_ACCOUNT_BINDING_TYPES = {
    "chatgpt_user_email",
    "line_user_id_hash_after_consent",
    "google_email_after_consent",
}

XIAOJ_CORE_SUPPLY_CONTRACT = {
    "contract_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
    "supplier": "THIS_SYSTEM_TOTAL_FIELD",
    "core_identity_immutable": True,
    "projection_kinds": {
        "merchant": {
            "domain_refs": ["U06_MERCHANT_POS_CAFE_DELIVERY", "ODOO", "POS"],
            "consumer_label": "商家",
            "projection_role": "商家櫃台點餐服務員",
            "role_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
            "establishment_class": "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD",
        },
        "committee": {
            "domain_refs": ["U07_PROPERTY_COMMITTEE_SOCIAL_HOUSING", "ODOO"],
            "consumer_label": "管委會",
            "projection_role": "大廳服務台服務員",
            "role_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
            "establishment_class": "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD",
        },
        "association": {
            "domain_refs": ["U05_COMMUNITY_MEMBER_SERVICE", "ODOO"],
            "consumer_label": "本會",
            "projection_role": "AI副總幹事",
            "role_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
            "establishment_class": "ASSOCIATION_INTERNAL_PROJECTION",
        },
        "nonprofit_association": {
            "domain_refs": ["U05_COMMUNITY_MEMBER_SERVICE", "ODOO"],
            "consumer_label": "非營利組織協會",
            "projection_role": "XIAOJ_ROLE_PROFILE_REQUIRED",
            "role_state": "UNKNOWN_UNVERIFIED",
            "establishment_class": "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD",
        },
        "other": {
            "domain_refs": ["GENERIC_TOTAL_FIELD", "ODOO"],
            "consumer_label": "其他類型",
            "projection_role": "XIAOJ_ROLE_PROFILE_REQUIRED",
            "role_state": "UNKNOWN_UNVERIFIED",
            "establishment_class": "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD",
        },
        "founder": {
            "domain_refs": ["U01_IDENTITY_ROLE_FOUNDER", "U11_XIAOJ_AI_AGENT"],
            "consumer_label": "創辦人",
            "projection_role": "AI開發助手",
            "role_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
            "establishment_class": "FOUNDER_LOCAL_PROJECTION",
        },
    },
    "core_capabilities": {
        "audiovisual_service": {
            "capability_ref": "W7TP_AUDIOVISUAL_DOMAIN_PROFILE",
            "evidence_state": "CANONICAL_DOMAIN_PROFILE",
        },
        "hexagram_state_encoding": {
            "capability_ref": "WUCHANG_64_HEXAGRAM_STATE_PROTOCOL_SAFE_REFERENCE",
            "scope": "64_HEXAGRAM_STATE_CODES",
            "evidence_state": "SAFE_PUBLIC_REFERENCE_NOT_CURRENT_8D_CANONICAL_CORE",
            "private_mapping_exposed": False,
            "numeric_contract_inferred": False,
        },
        "heavenly_stem_time_index": {
            "capability_ref": "HEAVENLY_STEM_TIME_INDEX",
            "evidence_state": "VERSIONED_DESIGN_EVIDENCE",
            "numeric_contract_inferred": False,
        },
        "earthly_branch_domain_index": {
            "capability_ref": "EARTHLY_BRANCH_DOMAIN_INDEX",
            "evidence_state": "VERSIONED_DESIGN_EVIDENCE",
            "numeric_contract_inferred": False,
        },
        "hash_evidence_binding": {
            "capability_ref": "SHA256_EVIDENCE_AND_REFERENCE_BINDING",
            "evidence_state": "CANONICAL_VERIFICATION_PRIMITIVE",
            "raw_secret_material_in_hash_input": False,
        },
    },
    "mode_application_authority": "THIS_SYSTEM_TOTAL_FIELD_ONLY",
    "service_agent_can_apply_mode": False,
    "model_can_apply_mode": False,
    "consumer_projection_can_apply_mode": False,
    "cross_total_field_implicit_mode_reuse": False,
    "missing_mode_authority_state": "HOLD_TOTAL_FIELD_MODE_AUTHORITY_UNVERIFIED",
    "appearance_is_field_projection": True,
    "membership_alignment": {
        "scope": "ALL_ORGANIZATIONAL_MEMBERS",
        "odoo_usage": "ALIGNMENT_RELATION_REFERENCE_ONLY",
        "odoo_is_formal_member_registry": False,
        "formal_member_authority": "ASSOCIATION_GOVERNED_SOURCE_SEPARATE",
        "member_plaintext_in_projection": False,
    },
    "field_projection_identity": {
        "packet_manager": "THIS_SYSTEM_TOTAL_FIELD",
        "approval_authority": "ASSOCIATION_GOVERNANCE",
        "issuance_authority": "UNKNOWN_UNVERIFIED",
        "identity_mode": "8D_IDENTITY_PACKET_REFERENCE_ONLY",
        "association_approval_required": True,
        "identity_packet_schema_ref": "W7TP_FIELD_ATLAS/schemas/8d_identity_packet.schema.yaml",
        "identity_packet_schema_state": "DRAFT_REFERENCE_ONLY",
        "field_projection_can_manage_or_approve_packet": False,
        "management_does_not_equal_approval_authority": True,
        "member_plaintext_copied": False,
    },
    "sovereign_ai_packet_account_governance": {
        "packet_class": "NATURAL_PERSON_SOVEREIGN_AI_8D_PACKET",
        "packet_manager": "THIS_SYSTEM_TOTAL_FIELD",
        "identity_seat_position": "D8_ENVELOPE_PREREQUISITE_NOT_D1_INTENT",
        "natural_identity_alignment_required_per_account": True,
        "multiple_accounts_allowed": True,
        "multiple_domain_permissions_allowed": True,
        "each_active_aligned_account_may_be_packet_entry": True,
        "entry_requires_account_binding_and_domain_permission": True,
        "multi_account_merge_requires_all_account_login_verification": True,
        "new_account_login_verification_required": True,
        "existing_account_reverification_required_on_merge": True,
        "natural_identity_relation_verification_required_per_account": True,
        "single_account_may_not_merge_or_link_other_accounts": True,
        "merge_decision_condition": "ALL_EXISTING_AND_NEW_ACCOUNT_EVIDENCE_VERIFIED",
        "verification_may_be_asynchronous_but_must_be_evidence_complete": True,
        "account_binding_policy_ref": "configs/member_account_binding_policy.yaml",
        "allowed_account_binding_types": list(ALLOWED_ACCOUNT_BINDING_TYPES),
        "external_account_consent_required": True,
        "gateway_required": True,
        "sealed_account_identifier_claim_in_packet": True,
        "sealed_identifier_scope": "LOCAL_SOVEREIGN_PACKET_PROTECTED_CLAIM_ONLY",
        "account_plaintext_in_projection_or_api": False,
        "account_plaintext_in_odoo_alignment": False,
        "credential_or_token_in_packet": False,
        "credential_or_token_in_model_or_report": False,
        "api_output": "OPAQUE_REF_OR_SHA256_ONLY",
        "permission_model": "EXPLICIT_ACCOUNT_DOMAIN_ROLE_BINDINGS",
        "permission_coordination_authority": "THIS_SYSTEM_TOTAL_FIELD_PACKET_POLICY",
        "permission_coordination_mode": "DENY_PRECEDENCE_LEAST_PRIVILEGE",
        "permission_union_across_accounts_allowed": False,
        "cross_account_implicit_permission_inheritance": False,
        "account_switch_may_elevate_permission": False,
        "account_merge_may_elevate_permission": False,
        "explicit_delegation_requires_separate_evidence": True,
        "conflict_requires_governed_decision": True,
        "account_binding_alone_authorizes_founder_ratification": False,
        "required_founder_account_binding": {
            "account_ref": "FOUNDER_PERSONAL_ACCOUNT_USER_DECLARED_20260822",
            "account_type": "google_email_after_consent",
            "normalized_login_sha256": REQUIRED_FOUNDER_ACCOUNT_LOGIN_SHA256,
            "sealed_identifier_claim_required": True,
            "natural_identity_alignment_required": True,
            "binding_verified": False,
            "evidence_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
        },
    },
    "ownership_and_admin_separation": {
        "association_projection_super_admin_account": "admin@wuchang.life",
        "account_role_state": "USER_DECLARED_BINDING_WITH_REPOSITORY_ADMIN_REFERENCES",
        "represents_association_identity_projection": True,
        "represents_legal_person_system_ownership": True,
        "represents_technical_ownership": False,
        "may_substitute_for_founder_ratification": False,
        "may_transfer_or_license_technical_rights_by_admin_role": False,
        "technical_ownership_authority": "SEPARATE_FORMAL_TITLE_OR_LICENSE_EVIDENCE_REQUIRED",
        "legal_person_system_ownership_does_not_imply_technical_ownership": True,
    },
    "xiaoj_addon_capabilities": {
        "group_member_total_field_application": {
            "capability_class": "XIAOJ_ADDON",
            "is_immutable_core_capability": False,
            "core_identity_mutated": False,
            "application_entry_surface": "PERSONAL_SOVEREIGN_IDENTITY_PACKET",
            "application_entry_visible_link": GROUP_MEMBER_APPLICATION_ENTRY_PATH,
            "link_contains_credential_or_packet_ref": False,
            "activation_authority": "THIS_SYSTEM_TOTAL_FIELD_POLICY",
            "addon_self_activation_allowed": False,
        },
    },
    "xiaoj_function_category_separation": {
        "general_market_user_categories": {
            "life_assistance": {
                "label": "生活輔助",
                "capability_refs": ["schedule_and_reminder", "daily_information", "personal_routine"],
            },
            "work_collaboration": {
                "label": "工作協作",
                "capability_refs": ["task_coordination", "meeting_and_document", "team_handoff"],
            },
            "personal_entertainment": {
                "label": "個人娛樂",
                "capability_refs": ["audiovisual_interaction", "interest_exploration", "leisure_companion"],
            },
            "account_binding": {
                "label": "帳號綁定",
                "capability_refs": ["multi_account_login", "natural_identity_relation", "domain_permission_entry"],
            },
        },
        "field_service_categories": {
            "committee_building": {
                "label": "管委會大樓功能",
                "capability_refs": ["resident_service", "visitor_and_notice", "repair_and_facility"],
                "required_projection_kind": "committee",
            },
            "merchant_membership": {
                "label": "商家會員功能",
                "capability_refs": ["member_service", "catalog_and_order", "promotion_and_operation"],
                "required_projection_kind": "merchant",
            },
        },
        "role_gated_management_backend": {
            "operations_dashboard": "營運總覽",
            "people_and_roles": "人員與角色",
            "service_configuration": "服務配置",
            "review_and_reports": "審核與報表",
            "verified_field_management_role_binding_required": True,
            "management_role_does_not_grant_founder_authority": True,
            "management_role_does_not_become_member_identity_authority": True,
            "odoo_role_binding_reference_only": True,
        },
        "founder_exclusive_control_categories": {
            "sovereign_packet_governance": "主權封包治理",
            "total_field_establishment_ratification": "總場成立核定",
            "distributed_device_and_compute": "設備與分散式算力",
            "founder_base_template_application": "創辦人基礎設備範本套用",
            "local_trade_secret_control": "本機營業秘密控制",
            "canonical_evidence_and_authority": "正典、證據與權威治理",
        },
        "general_market_ui_may_expose_founder_controls": False,
        "field_service_requires_matching_group_member_projection": True,
        "management_backend_requires_matching_total_field_and_role": True,
        "founder_console_requires_verified_founder_seat": True,
        "founder_console_requires_bound_founder_account": True,
        "association_super_admin_is_not_founder_console_authority": True,
        "category_visibility_verified": False,
        "evidence_state": "USER_DECLARED_CANDIDATE_REQUIREMENT",
    },
    "group_member_total_field_establishment": {
        "eligible_establishment_class": "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD",
        "allowed_types": ["merchant", "committee", "nonprofit_association", "other"],
        "association_group_member_approval_required": True,
        "application_addon_ref": "group_member_total_field_application",
        "application_submission_authority": "ASSOCIATION_ACTIVE_SOVEREIGN_IDENTITY_PACKET",
        "identity_packet_manager": "THIS_SYSTEM_TOTAL_FIELD",
        "identity_packet_active_evidence_required": True,
        "founder_final_ratification_required": True,
        "application_submission_establishes_total_field": False,
        "founder_ratification_is_final_gate": True,
        "founder_ratification_alone_is_sufficient": False,
        "establishment_condition": "ALL_REQUIRED_GATES_VERIFIED",
        "required_gate_order": [
            "ASSOCIATION_GROUP_MEMBER_APPROVED",
            "SYSTEM_MANAGED_IDENTITY_PACKET_ASSOCIATION_EFFECTIVE",
            "ODOO_RELATIONSHIP_ALIGNED",
            "QUESTIONNAIRE_VERIFIED_OR_OTHER_VISIT_DESIGNED",
            "APPLICATION_VERIFIED",
            "FOUNDER_ACCOUNT_BOUND_TO_NATURAL_IDENTITY_IN_SOVEREIGN_AI_PACKET",
            "FOUNDER_PERSONALLY_RATIFIED",
        ],
        "automatic_establishment_allowed": False,
        "odoo_relationship_is_reference_only": True,
        "preconstruction_questionnaire": {
            "required_types": ["merchant", "committee", "nonprofit_association"],
            "exempt_types": ["other"],
            "required_before_founder_ratification": True,
            "real_world_usable_evidence_required": True,
            "raw_member_plaintext_allowed": False,
        },
        "other_type_exception": {
            "preconstruction_questionnaire_required": False,
            "founder_personal_ratification_required": True,
            "founder_personal_visit_design_required": True,
            "generic_template_substitution_allowed": False,
            "remote_design_auto_completion_allowed": False,
        },
    },
    "local_trade_secret_policy": {
        "control_authority": "LOCAL_SYSTEM",
        "storage_locus": "LOCAL_EXTERNAL_DRIVE_ONLY",
        "current_unsealed_state": "USER_DECLARED_UNVERIFIED",
        "approved_device_may_request": True,
        "automatic_total_field_approval_eligible": True,
        "device_request_alone_is_sufficient": False,
        "required_verified_bindings": [
            "approved_device",
            "total_field_request_policy",
            "purpose_and_scope",
            "time_window",
        ],
        "raw_secret_in_odoo": False,
        "raw_secret_in_packet": False,
        "opaque_reference_or_hash_only": True,
    },
    "distributed_compute_governance": {
        "topology": "DISTRIBUTED_COMPUTE_DEVICE_FEDERATION",
        "device_establishment_authority": "FOUNDER_EXPLICIT_APPROVAL_ONLY",
        "device_self_enrollment": False,
        "existing_node_may_establish_another_node": False,
        "approved_node_may_override_governance": False,
        "template_application_authority": "THIS_LOCAL_FOUNDER_BASE_DEVICE_ONLY",
        "founder_base_device_ref_required": True,
        "remote_node_can_apply_template": False,
        "consumer_projection_can_apply_template": False,
        "template_copy_or_delegation_allowed": False,
        "template_application_requires_total_field_binding": True,
    },
    "evidence_refs": [
        "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md",
        "manifests/ollama_xiaoj_total_field_v0_1/voice_pronunciation_routing_contract.json",
        "W7TP_FIELD_ATLAS/sub_universe_registry_v1.yaml",
        "Wuchang_Hexagram_State_Protocol_Open_20260523_194932/README.md",
        "Wuchang_Hexagram_State_Protocol_Open_20260523_194932/docs/01_hexagram_state_code.md",
        "docs/patent/taiwan_patent_claims_v1.md",
        "docs/design/W7TP_XIAOJ_DEVICE_FEDERATION_TOPOLOGY.md",
        "docs/taiji_hub_architecture_completion_board_zh.md",
        "docs/landing/W7TP_SYSTEM_INTENT_FIELD_DETERMINISTIC_CORE_SHADOW_V1_CANDIDATE.md",
    ],
}

GROUP_MEMBER_QUESTIONNAIRE_COMMON_SECTIONS = (
    {
        "code": "identity_authority_prerequisite",
        "label": "身分與權威前置",
        "prompt": "請確認本會團體會員核准、個人主權身分封包生效及 Odoo 照準關係證據。",
        "fields": [
            "group_member_ref",
            "association_approval_evidence_ref",
            "personal_sovereign_identity_packet_ref",
            "identity_packet_active_evidence_ref",
            "sovereign_ai_account_entry_binding_ref",
            "account_domain_permission_ref",
            "founder_account_packet_binding_evidence_ref",
            "odoo_relationship_ref",
            "legal_person_system_owner_ref",
            "technical_owner_or_license_ref",
        ],
    },
    {
        "code": "d1_intent",
        "label": "D1 服務意圖與可觀測成果",
        "prompt": "這個總場要為哪些人完成什麼服務，現實世界如何判定結果已達成？",
        "fields": ["primary_service_intent", "service_population_ref", "observable_outcome_refs"],
    },
    {
        "code": "d2_state",
        "label": "D2 現實營運狀態",
        "prompt": "目前如何營運、何時服務、哪些情況必須交由人員接手？",
        "fields": ["current_operation_state", "operating_hours_ref", "human_handoff_roles"],
    },
    {
        "code": "d3_coordinate",
        "label": "D3 場所、設備與 Odoo 座標",
        "prompt": "服務發生在哪裡、使用哪些已核准設備、對應哪一個 Odoo 組織單位？",
        "fields": ["service_location_refs", "approved_device_refs", "odoo_company_or_unit_ref"],
    },
    {
        "code": "d4_evidence",
        "label": "D4 合法、合規與驗收證據",
        "prompt": "成立、營運、合規與產品驗收分別由哪些可驗證引用證明？",
        "fields": ["registration_or_eligibility_refs", "policy_refs", "acceptance_evidence_refs"],
    },
    {
        "code": "d5_execution_policy",
        "label": "D5 工作流程與人為放行",
        "prompt": "小J可做到哪一步、哪些動作一定要由哪個人類角色放行？",
        "fields": ["service_workflow_refs", "release_role_refs", "prohibited_effects"],
    },
    {
        "code": "d6_generative_transmission",
        "label": "D6 影音小J與生成式傳輸",
        "prompt": "影音小J在此場域呈現什麼角色、使用哪些語言與渠道、如何轉交真人？",
        "fields": ["xiaoj_projection_role_ref", "language_channel_refs", "handoff_message_contract_ref"],
    },
    {
        "code": "d7_risk_quarantine",
        "label": "D7 風險、隱私、隔離與營運持續",
        "prompt": "資料如何分級、秘密留在哪裡、異常時如何隔離並維持最低服務？",
        "fields": ["data_classification_ref", "secret_boundary_ref", "quarantine_and_continuity_ref"],
    },
    {
        "code": "d8_envelope_authority",
        "label": "D8 封套、權威、期限與撤銷",
        "prompt": "誰能核准、何時生效失效、如何撤銷，以及稽核證據保存在哪個引用？",
        "fields": ["authority_envelope_ref", "effective_window_ref", "revocation_and_audit_ref"],
    },
)

GROUP_MEMBER_QUESTIONNAIRE_TYPE_SECTIONS = {
    "merchant": {
        "label": "商家現實營運",
        "prompt": "請完整描述可實際點餐、報價、付款、履約及櫃台交接的來源與流程。",
        "fields": [
            "menu_or_service_catalog_ref",
            "pricing_source_ref",
            "pos_payment_fulfillment_refs",
            "store_counter_and_staff_role_refs",
        ],
    },
    "committee": {
        "label": "管委會大廳與物業服務",
        "prompt": "請完整描述大廳服務、設施、訪客、事件及管委會人為放行流程。",
        "fields": [
            "property_or_community_scope_ref",
            "lobby_service_desk_workflow_ref",
            "facility_visitor_incident_workflow_refs",
            "committee_release_role_refs",
        ],
    },
    "nonprofit_association": {
        "label": "非營利組織協會治理與服務",
        "prompt": "請完整描述章程、理監事與秘書處、方案志工、財務及報告邊界。",
        "fields": [
            "charter_and_registration_refs",
            "board_secretariat_role_refs",
            "program_volunteer_service_refs",
            "funding_accounting_reporting_boundary_refs",
        ],
    },
}

# Backward-compatible projection view for the merchant catalog.  Authority and
# core ownership live in XIAOJ_CORE_SUPPLY_CONTRACT above.
XIAOJ_AUDIOVISUAL_PROJECTION_CONTRACT = {
    "contract_state": XIAOJ_CORE_SUPPLY_CONTRACT["contract_state"],
    "audiovisual_core_ref": "W7TP_AUDIOVISUAL_DOMAIN_PROFILE",
    "core_identity_immutable": XIAOJ_CORE_SUPPLY_CONTRACT["core_identity_immutable"],
    "appearance_is_field_projection": XIAOJ_CORE_SUPPLY_CONTRACT["appearance_is_field_projection"],
    "mode_application_authority": XIAOJ_CORE_SUPPLY_CONTRACT["mode_application_authority"],
    "service_agent_can_apply_mode": XIAOJ_CORE_SUPPLY_CONTRACT["service_agent_can_apply_mode"],
    "model_can_apply_mode": XIAOJ_CORE_SUPPLY_CONTRACT["model_can_apply_mode"],
    "cross_total_field_implicit_mode_reuse": XIAOJ_CORE_SUPPLY_CONTRACT[
        "cross_total_field_implicit_mode_reuse"
    ],
    "missing_mode_authority_state": XIAOJ_CORE_SUPPLY_CONTRACT["missing_mode_authority_state"],
    "evidence_refs": deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT["evidence_refs"]),
}

SAFETY_FLAGS = {
    "MEMBER_PLAINTEXT_READ": False,
    "SECRET_READ": False,
    "ODOO_DB_WRITE": False,
    "POS_ORDER_CREATED": False,
    "PAYMENT_CAPTURE": False,
    "REFUND_EXECUTED": False,
    "PROMOTION_ACTIVATED": False,
    "ACCOUNT_ROLE_CHANGED": False,
    "EXTERNAL_API_CALL": False,
}

PROTECTED_PARAMETER_PARTS = {
    "member",
    "customer",
    "phone",
    "email",
    "address",
    "password",
    "token",
    "secret",
    "credential",
    "api_key",
    "raw_audio",
}


CAPABILITIES = (
    {
        "code": "operations.summary",
        "label": "營業概況",
        "quickclick": {"feature": "總覽", "path": "/summary/stat"},
        "odoo": {"models": ["pos.order", "pos.payment", "pos.session"], "service": None},
        "mode": "read_only",
        "risk": "low",
        "implementation_state": "BINDING_REQUIRED",
        "release_roles": ["cashier", "manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "date_from", "date_to", "timezone"],
        "outputs": ["turnover", "order_count", "payment_mix", "pickup_mix", "trend"],
    },
    {
        "code": "operations.orders",
        "label": "訂單列表",
        "quickclick": {"feature": "訂單列表", "path": "/summary/orders"},
        "odoo": {"models": ["pos.order", "pos.order.line"], "service": None},
        "mode": "read_only",
        "risk": "medium",
        "implementation_state": "BINDING_REQUIRED",
        "release_roles": ["cashier", "manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "date_from", "date_to", "state", "limit"],
        "outputs": ["order_ref", "order_state", "amount", "sale_mode"],
    },
    {
        "code": "operations.shop_report",
        "label": "店家報表",
        "quickclick": {"feature": "店家報表", "path": "/summary/shop-stat"},
        "odoo": {"models": ["pos.order", "pos.session"], "service": None},
        "mode": "read_only",
        "risk": "low",
        "implementation_state": "BINDING_REQUIRED",
        "release_roles": ["manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "date_from", "date_to", "dimensions"],
        "outputs": ["aggregates", "ranking", "trend"],
    },
    {
        "code": "merchant.store_profile",
        "label": "商店管理",
        "quickclick": {"feature": "商店管理", "path": "/eaa/business/shop-management"},
        "odoo": {"models": ["pos.config", "res.company", "stock.warehouse"], "service": None},
        "mode": "human_release",
        "risk": "high",
        "implementation_state": "DESIGN_ONLY",
        "release_roles": ["owner", "admin"],
        "allowed_parameters": ["store_ref", "change_set_ref", "effective_at"],
        "outputs": ["store_profile_candidate", "diff", "review_requirement"],
    },
    {
        "code": "catalog.menu",
        "label": "菜單查詢",
        "quickclick": {"feature": "菜單管理", "path": "/menu-management"},
        "odoo": {
            "models": ["wuchang.menu.item", "wuchang.cafe.option.group", "product.template"],
            "service": "wuchang.cafe.readonly.menu.mapping.service",
            "route": "/wuchang/api/cafe/menu/v1",
        },
        "mode": "read_only",
        "risk": "low",
        "implementation_state": "AVAILABLE_READ_ONLY",
        "release_roles": ["service_agent", "cashier", "manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "category_ref", "query", "limit"],
        "outputs": ["categories", "items", "option_groups", "mapping_sha256"],
    },
    {
        "code": "catalog.option_quote",
        "label": "選項組合與報價",
        "quickclick": {"feature": "菜單管理", "path": "/menu-management"},
        "odoo": {
            "models": ["wuchang.menu.item", "wuchang.cafe.option.item"],
            "service": None,
        },
        "mode": "candidate_only",
        "risk": "medium",
        "implementation_state": "BINDING_REQUIRED",
        "release_roles": ["service_agent", "cashier", "manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "item_ref", "selection_refs", "quantity"],
        "outputs": ["quote_candidate", "price_source_refs", "validation_errors"],
    },
    {
        "code": "sales.query",
        "label": "銷售查詢",
        "quickclick": {"feature": "銷售查詢", "path": "/sales/query"},
        "odoo": {"models": ["pos.order", "pos.order.line", "pos.payment"], "service": None},
        "mode": "read_only",
        "risk": "medium",
        "implementation_state": "BINDING_REQUIRED",
        "release_roles": ["manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "date_from", "date_to", "sale_mode", "payment_mode", "limit"],
        "outputs": ["aggregated_sales", "order_refs", "payment_totals"],
    },
    {
        "code": "customer.blocklist",
        "label": "封鎖名單",
        "quickclick": {"feature": "封鎖名單", "path": "/sales/banned-list"},
        "odoo": {"models": ["res.partner"], "service": None},
        "mode": "human_release",
        "risk": "critical",
        "implementation_state": "DESIGN_ONLY",
        "release_roles": ["owner", "admin"],
        "allowed_parameters": ["subject_ref", "reason_code", "evidence_ref", "expires_at"],
        "outputs": ["block_candidate", "due_process_requirement", "review_requirement"],
    },
    {
        "code": "operations.report_360",
        "label": "360營業報告",
        "quickclick": {"feature": "360營業報告", "path": "/report/360-stats"},
        "odoo": {"models": ["pos.order", "pos.payment", "product.product"], "service": None},
        "mode": "read_only",
        "risk": "low",
        "implementation_state": "BINDING_REQUIRED",
        "release_roles": ["manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "date_from", "date_to", "dimensions"],
        "outputs": ["turnover", "order_count", "product_mix", "pickup_mix", "trend", "ranking"],
    },
    {
        "code": "identity.account_manage",
        "label": "帳戶管理",
        "quickclick": {"feature": "帳戶管理", "path": "/eaa-account"},
        "odoo": {"models": ["res.users", "res.groups"], "service": None},
        "mode": "human_release",
        "risk": "critical",
        "implementation_state": "DESIGN_ONLY",
        "release_roles": ["admin"],
        "allowed_parameters": ["account_ref", "role_ref", "change_set_ref", "effective_at"],
        "outputs": ["account_change_candidate", "authority_check", "review_requirement"],
    },
    {
        "code": "marketing.promotions",
        "label": "行銷活動",
        "quickclick": {"feature": "行銷活動總覽", "path": "/eaa/business/promotions"},
        "odoo": {"models": ["loyalty.program", "loyalty.rule", "loyalty.reward"], "service": None},
        "mode": "human_release",
        "risk": "high",
        "implementation_state": "DESIGN_ONLY",
        "release_roles": ["manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "program_ref", "change_set_ref", "date_from", "date_to"],
        "outputs": ["promotion_candidate", "pricing_impact", "review_requirement"],
    },
    {
        "code": "orders.candidate",
        "label": "小J組單候選",
        "quickclick": {"feature": "訂單流程", "path": "/summary/orders"},
        "odoo": {"models": ["pos.order", "pos.order.line"], "service": "wuchang_cafe_ai_gateway"},
        "mode": "candidate_only",
        "risk": "medium",
        "implementation_state": "CANDIDATE_SHELL_ONLY",
        "release_roles": ["cashier", "manager", "owner", "admin"],
        "allowed_parameters": ["store_ref", "cart_ref", "sale_mode", "requested_at"],
        "outputs": ["order_candidate", "canonical_quote_required", "human_release_required"],
    },
)


KEYWORD_RULES = (
    ("customer.blocklist", ("封鎖名單", "黑名單", "blocklist")),
    ("identity.account_manage", ("帳戶管理", "角色權限", "account management")),
    ("marketing.promotions", ("行銷活動", "促銷", "優惠活動", "promotion")),
    ("operations.report_360", ("360營業", "360 報告", "360 report")),
    ("operations.shop_report", ("店家報表", "商店報表", "shop report")),
    ("sales.query", ("銷售查詢", "sales query")),
    ("operations.orders", ("訂單列表", "查訂單", "order list")),
    ("catalog.option_quote", ("選項報價", "加料報價", "組合價格", "option quote")),
    ("orders.candidate", ("幫我組單", "建立訂單候選", "order candidate")),
    ("catalog.menu", ("菜單", "品項", "menu")),
    ("merchant.store_profile", ("商店管理", "店家設定", "store profile")),
    ("operations.summary", ("營業概況", "今日營業額", "訂單數", "business summary")),
)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _opaque_ref(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    return {
        "present": bool(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
        "verified": False,
    }


def _normalized_sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        return None
    return text


def plan_sovereign_ai_multi_account_binding(
    *,
    sovereign_ai_packet_ref: Any = None,
    natural_identity_ref: Any = None,
    account_bindings: Any = None,
    permission_coordination_policy_ref: Any = None,
) -> dict[str, Any]:
    """Plan a no-write multi-account merge with per-account login proof."""
    governance = XIAOJ_CORE_SUPPLY_CONTRACT["sovereign_ai_packet_account_governance"]
    packet_ref = _opaque_ref(sovereign_ai_packet_ref)
    identity_ref = _opaque_ref(natural_identity_ref)
    policy_ref = _opaque_ref(permission_coordination_policy_ref)
    source_bindings = list(account_bindings) if isinstance(account_bindings, (list, tuple)) else []
    normalized_bindings = []
    binding_errors: list[str] = []
    seen_login_hashes: set[str] = set()
    founder_binding_present = False
    existing_count = 0
    new_count = 0

    for index, source in enumerate(source_bindings):
        prefix = f"account_bindings[{index}]"
        if not isinstance(source, Mapping):
            binding_errors.append(f"{prefix}:mapping_required")
            continue
        binding_state = str(source.get("binding_state") or "").strip().lower()
        account_type = str(source.get("account_type") or "").strip().lower()
        login_hash = _normalized_sha256(source.get("account_login_sha256"))
        domain_sources = source.get("domain_permission_refs")
        domain_sources = list(domain_sources) if isinstance(domain_sources, (list, tuple)) else []
        domain_permission_refs = [_opaque_ref(item) for item in domain_sources]
        refs = {
            "account_ref": _opaque_ref(source.get("account_ref")),
            "account_login_verification_evidence_ref": _opaque_ref(
                source.get("account_login_verification_evidence_ref")
            ),
            "natural_identity_relation_evidence_ref": _opaque_ref(
                source.get("natural_identity_relation_evidence_ref")
            ),
            "account_binding_evidence_ref": _opaque_ref(
                source.get("account_binding_evidence_ref")
            ),
            "existing_binding_reverification_evidence_ref": _opaque_ref(
                source.get("existing_binding_reverification_evidence_ref")
            ),
            "external_account_consent_evidence_ref": _opaque_ref(
                source.get("external_account_consent_evidence_ref")
            ),
        }
        missing = []
        if binding_state not in {"existing", "new"}:
            missing.append("binding_state_existing_or_new")
        elif binding_state == "existing":
            existing_count += 1
        else:
            new_count += 1
        if account_type not in ALLOWED_ACCOUNT_BINDING_TYPES:
            missing.append("allowed_account_type")
        if login_hash is None:
            missing.append("valid_account_login_sha256")
        elif login_hash in seen_login_hashes:
            missing.append("unique_account_login_sha256")
        else:
            seen_login_hashes.add(login_hash)
        for key in (
            "account_ref",
            "account_login_verification_evidence_ref",
            "natural_identity_relation_evidence_ref",
            "account_binding_evidence_ref",
        ):
            if not refs[key]["present"]:
                missing.append(key)
        if binding_state == "existing" and not refs[
            "existing_binding_reverification_evidence_ref"
        ]["present"]:
            missing.append("existing_binding_reverification_evidence_ref")
        if account_type in EXTERNAL_ACCOUNT_BINDING_TYPES and not refs[
            "external_account_consent_evidence_ref"
        ]["present"]:
            missing.append("external_account_consent_evidence_ref")
        if not domain_permission_refs or any(not item["present"] for item in domain_permission_refs):
            missing.append("domain_permission_refs")

        is_required_founder_binding = bool(
            login_hash == REQUIRED_FOUNDER_ACCOUNT_LOGIN_SHA256
            and account_type == governance["required_founder_account_binding"]["account_type"]
        )
        founder_binding_present = founder_binding_present or is_required_founder_binding
        normalized_bindings.append({
            "index": index,
            "binding_state": binding_state or None,
            "account_type": account_type or None,
            "account_login_sha256": login_hash,
            "is_required_founder_account_binding": is_required_founder_binding,
            "refs": refs,
            "domain_permission_refs": domain_permission_refs,
            "missing_evidence": missing,
            "login_verified": False,
            "natural_identity_relation_verified": False,
            "existing_binding_reverified": False,
            "domain_permissions_verified": False,
            "packet_entry_authorized": False,
        })
        binding_errors.extend(f"{prefix}:{item}" for item in missing)

    missing_prerequisites = []
    if not packet_ref["present"]:
        missing_prerequisites.append("sovereign_ai_packet_ref")
    if not identity_ref["present"]:
        missing_prerequisites.append("natural_identity_ref")
    if not policy_ref["present"]:
        missing_prerequisites.append("permission_coordination_policy_ref")
    if len(source_bindings) < 2:
        missing_prerequisites.append("at_least_two_account_bindings")
    if existing_count < 1:
        missing_prerequisites.append("existing_account_binding")
    if new_count < 1:
        missing_prerequisites.append("new_account_binding")
    if not founder_binding_present:
        missing_prerequisites.append("required_founder_account_binding")
    missing_prerequisites.extend(binding_errors)
    candidate_ready = not missing_prerequisites
    payload = {
        "schema": SOVEREIGN_AI_ACCOUNT_BINDING_SCHEMA,
        "state": "CANDIDATE_MULTI_ACCOUNT_MERGE_PENDING_VERIFICATION"
        if candidate_ready
        else "HOLD_MULTI_ACCOUNT_LOGIN_OR_RELATION_EVIDENCE_REQUIRED",
        "governance": deepcopy(governance),
        "sovereign_ai_packet_ref": packet_ref,
        "natural_identity_ref": identity_ref,
        "permission_coordination_policy_ref": policy_ref,
        "account_bindings": normalized_bindings,
        "account_count": len(normalized_bindings),
        "existing_account_count": existing_count,
        "new_account_count": new_count,
        "required_founder_account_binding_present": founder_binding_present,
        "all_existing_and_new_account_evidence_present": candidate_ready,
        "all_account_logins_verified": False,
        "all_natural_identity_relations_verified": False,
        "permission_coordination": {
            "mode": governance["permission_coordination_mode"],
            "deny_precedence": True,
            "least_privilege": True,
            "permission_union_allowed": False,
            "implicit_cross_account_inheritance": False,
            "conflict_decision_verified": False,
            "coordination_activated": False,
        },
        "packet_mutated": False,
        "account_bindings_persisted": False,
        "account_entries_activated": False,
        "permissions_granted_or_elevated": False,
        "founder_ratification_authorized": False,
        "odoo_write": False,
        "missing_prerequisites": missing_prerequisites,
        "execution_authority": False,
        "safety_flags": deepcopy(SAFETY_FLAGS),
        "next": "VERIFY_ALL_EXISTING_AND_NEW_ACCOUNT_LOGINS_AND_NATURAL_IDENTITY_RELATIONS"
        if candidate_ready
        else "SUPPLY_COMPLETE_MULTI_ACCOUNT_LOGIN_RELATION_AND_DOMAIN_PERMISSION_EVIDENCE_REFS",
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def build_sovereign_ai_multi_account_governance_candidate() -> dict[str, Any]:
    """Return red-team gaps and purple-team completion-rule candidates."""
    gaps = [
        {
            "id": "G001_MERGE_TRANSACTION_AND_QUORUM_UNDEFINED",
            "risk": "PARTIAL_ACCOUNT_LINK_OR_SINGLE_ACCOUNT_TAKEOVER",
            "missing_rule": "ATOMIC_MERGE_PROPOSAL_WITH_ALL_EXISTING_AND_NEW_ACCOUNT_PROOFS",
        },
        {
            "id": "G002_LOGIN_PROOF_FRESHNESS_AND_ANTI_REPLAY_UNDEFINED",
            "risk": "STALE_OR_REPLAYED_LOGIN_EVIDENCE",
            "missing_rule": "BOUNDED_CHALLENGE_NONCE_EXPIRY_AND_ONE_TIME_RECEIPT",
        },
        {
            "id": "G003_NATURAL_IDENTITY_RELATION_AUTHORITY_UNDEFINED",
            "risk": "UNRELATED_ACCOUNTS_BOUND_TO_ONE_PACKET",
            "missing_rule": "VERIFIED_NATURAL_IDENTITY_AUTHORITY_AND_RELATION_EVIDENCE",
        },
        {
            "id": "G004_DOMAIN_PERMISSION_COORDINATION_UNDEFINED",
            "risk": "PERMISSION_UNION_OR_CROSS_ACCOUNT_PRIVILEGE_ESCALATION",
            "missing_rule": "EXPLICIT_DOMAIN_ROLE_BINDINGS_DENY_PRECEDENCE_AND_DELEGATION_EVIDENCE",
        },
        {
            "id": "G005_ACCOUNT_LIFECYCLE_AND_RECOVERY_UNDEFINED",
            "risk": "LOCKOUT_OR_UNGOVERNED_RECOVERY_BYPASS",
            "missing_rule": "ADD_SUSPEND_REVOKE_ROTATE_RECOVER_AND_CONSENT_WITHDRAWAL_STATES",
        },
        {
            "id": "G006_APPEND_ONLY_LINEAGE_AND_PRIVACY_UNDEFINED",
            "risk": "SILENT_REWRITE_OR_ACCOUNT_PLAINTEXT_LEAK",
            "missing_rule": "APPEND_ONLY_HASH_RECEIPTS_WITH_SEALED_IDENTIFIER_RETENTION_POLICY",
        },
        {
            "id": "G007_PACKET_ENTRY_RUNTIME_ENFORCEMENT_UNBOUND",
            "risk": "BOUND_ACCOUNT_BYPASSES_DOMAIN_OR_SESSION_GATE",
            "missing_rule": "GATEWAY_SESSION_BINDING_DOMAIN_CHECK_REVOCATION_AND_DEAD_LETTER",
        },
        {
            "id": "G008_ODOO_AND_ASSOCIATION_AUTHORITY_BOUNDARY_UNSEALED",
            "risk": "SERVICE_ROLE_OR_ADMIN_ACCOUNT_PROMOTED_TO_IDENTITY_AUTHORITY",
            "missing_rule": "REFERENCE_ONLY_ROLE_PROJECTION_WITH_SEPARATE_ASSOCIATION_AND_FOUNDER_GATES",
        },
        {
            "id": "G009_FOUNDER_ACCOUNT_BINDING_AND_RATIFICATION_NOT_SEPARATELY_RECEIPTED",
            "risk": "ACCOUNT_POSSESSION_MISREAD_AS_FOUNDER_APPROVAL",
            "missing_rule": "DISTINCT_ACCOUNT_BINDING_AND_FOUNDER_RATIFICATION_RECEIPTS",
        },
    ]
    completion_rules = [
        {
            "rule": "R001_ATOMIC_MULTI_ACCOUNT_MERGE_PROPOSAL",
            "closes": ["G001_MERGE_TRANSACTION_AND_QUORUM_UNDEFINED"],
            "candidate_condition": "ALL_EXISTING_AND_NEW_ACCOUNTS_INCLUDED_AND_NO_PARTIAL_COMMIT",
        },
        {
            "rule": "R002_PER_ACCOUNT_FRESH_LOGIN_AND_RELATION_PROOF",
            "closes": [
                "G002_LOGIN_PROOF_FRESHNESS_AND_ANTI_REPLAY_UNDEFINED",
                "G003_NATURAL_IDENTITY_RELATION_AUTHORITY_UNDEFINED",
            ],
            "candidate_condition": "EACH_ACCOUNT_HAS_LOGIN_CHALLENGE_AND_SAME_NATURAL_IDENTITY_RELATION_RECEIPT",
        },
        {
            "rule": "R003_DENY_FIRST_DOMAIN_PERMISSION_COORDINATION",
            "closes": ["G004_DOMAIN_PERMISSION_COORDINATION_UNDEFINED"],
            "candidate_condition": "NO_PERMISSION_UNION_NO_IMPLICIT_INHERITANCE_AND_EXPLICIT_DELEGATION_ONLY",
        },
        {
            "rule": "R004_ACCOUNT_LIFECYCLE_STATE_MACHINE",
            "closes": ["G005_ACCOUNT_LIFECYCLE_AND_RECOVERY_UNDEFINED"],
            "candidate_condition": "PROPOSED_BOUND_ACTIVE_SUSPENDED_REVOKED_RECOVERY_HOLD",
        },
        {
            "rule": "R005_APPEND_ONLY_PRIVACY_PRESERVING_RECEIPTS",
            "closes": ["G006_APPEND_ONLY_LINEAGE_AND_PRIVACY_UNDEFINED"],
            "candidate_condition": "SEALED_IDENTIFIER_LOCAL_ONLY_AND_REF_HASH_RECEIPTS_OUTSIDE_PACKET",
        },
        {
            "rule": "R006_GATEWAY_ENTRY_AND_REVOCATION_ENFORCEMENT",
            "closes": ["G007_PACKET_ENTRY_RUNTIME_ENFORCEMENT_UNBOUND"],
            "candidate_condition": "EVERY_ENTRY_CHECKS_ACTIVE_BINDING_SESSION_AND_REQUESTED_DOMAIN",
        },
        {
            "rule": "R007_AUTHORITY_AND_RATIFICATION_SEPARATION",
            "closes": [
                "G008_ODOO_AND_ASSOCIATION_AUTHORITY_BOUNDARY_UNSEALED",
                "G009_FOUNDER_ACCOUNT_BINDING_AND_RATIFICATION_NOT_SEPARATELY_RECEIPTED",
            ],
            "candidate_condition": "ODOO_REFERENCE_ONLY_AND_ACCOUNT_BINDING_NEVER_EQUALS_FOUNDER_RATIFICATION",
        },
    ]
    payload = {
        "schema": SOVEREIGN_AI_ACCOUNT_GOVERNANCE_SCHEMA,
        "state": "HOLD_GOVERNANCE_RULE_GAPS",
        "method": "RED_TEAM_GAP_REVIEW_THEN_PURPLE_TEAM_PRODUCT_CANDIDATE",
        "existing_policy_ref": "configs/member_account_binding_policy.yaml",
        "observed_existing_policy_coverage": [
            "ALLOWED_ACCOUNT_BINDING_TYPES",
            "EXTERNAL_ACCOUNT_CONSENT_REQUIRED",
            "GATEWAY_REQUIRED",
            "SECRET_STORAGE_FORBIDDEN",
            "HIGH_RISK_TO_DEAD_LETTER",
        ],
        "existing_policy_effect_verified": False,
        "red_team_gaps": gaps,
        "purple_team_completion_rules": completion_rules,
        "unresolved_governance_decisions": [
            "NATURAL_IDENTITY_RELATION_APPROVAL_AUTHORITY",
            "LOGIN_ASSURANCE_AND_MULTI_FACTOR_PROFILE",
            "LOGIN_CHALLENGE_AND_RECEIPT_FORMAT_AND_EXPIRY",
            "RECOVERY_WHEN_AN_EXISTING_ACCOUNT_IS_UNAVAILABLE",
            "DOMAIN_PERMISSION_CONFLICT_ARBITER",
            "SEALED_IDENTIFIER_AND_RECEIPT_RETENTION_PERIOD",
        ],
        "rules_promoted_or_activated": False,
        "canonical_mutation": False,
        "runtime_effect": False,
        "next": "RATIFY_UNRESOLVED_GOVERNANCE_DECISIONS_THEN_BIND_READ_ONLY_VERIFIERS",
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def build_xiaoj_core_supply_contract() -> dict[str, Any]:
    """Return the deterministic system-core and projection contract."""
    payload = {
        "schema": CORE_SUPPLY_SCHEMA,
        "state": "CANDIDATE_CORE_SUPPLY_CONTRACT",
        **deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT),
        "safety_flags": deepcopy(SAFETY_FLAGS),
    }
    payload["contract_sha256"] = _sha256(payload)
    return payload


def build_group_member_intent_field_questionnaire(*, field_type: Any = None) -> dict[str, Any]:
    """Return a non-persisting, real-world-operation questionnaire candidate."""
    normalized_type = str(field_type or "").strip().lower()
    allowed = set(
        XIAOJ_CORE_SUPPLY_CONTRACT["group_member_total_field_establishment"]["allowed_types"]
    )
    required_types = set(
        XIAOJ_CORE_SUPPLY_CONTRACT["group_member_total_field_establishment"]
        ["preconstruction_questionnaire"]["required_types"]
    )
    if normalized_type not in allowed:
        state = "HOLD_UNKNOWN_GROUP_MEMBER_FIELD_TYPE"
        required = False
        sections = []
        next_action = "SELECT_MERCHANT_COMMITTEE_NONPROFIT_ASSOCIATION_OR_OTHER"
    elif normalized_type == "other":
        state = "NOT_REQUIRED_FOR_OTHER_TYPE"
        required = False
        sections = []
        next_action = "REQUEST_FOUNDER_RATIFICATION_AND_PERSONAL_VISIT_DESIGN"
    else:
        state = "CANDIDATE_REAL_WORLD_USABLE_QUESTIONNAIRE"
        required = normalized_type in required_types
        sections = [deepcopy(item) for item in GROUP_MEMBER_QUESTIONNAIRE_COMMON_SECTIONS]
        type_section = deepcopy(GROUP_MEMBER_QUESTIONNAIRE_TYPE_SECTIONS[normalized_type])
        sections.append({"code": f"type_{normalized_type}", **type_section})
        next_action = "COMPLETE_WITH_OPAQUE_REFS_AND_VERIFY_REAL_WORLD_USABILITY"
    payload = {
        "schema": GROUP_MEMBER_QUESTIONNAIRE_SCHEMA,
        "state": state,
        "field_type": normalized_type or None,
        "questionnaire_required": required,
        "answer_contract": "OPAQUE_REF_ENUM_OR_BOUNDED_NON_PII_TEXT",
        "member_plaintext_allowed": False,
        "secret_value_allowed": False,
        "odoo_write": False,
        "sections": sections,
        "questionnaire_persisted": False,
        "real_world_usability_verified": False,
        "execution_authority": False,
        "next": next_action,
    }
    payload["questionnaire_sha256"] = _sha256(payload)
    return payload


def build_group_member_total_field_product_candidate() -> dict[str, Any]:
    """Return the human-facing XiaoJ add-on landing candidate."""
    projections = XIAOJ_CORE_SUPPLY_CONTRACT["projection_kinds"]
    type_options = []
    for code in ("merchant", "committee", "nonprofit_association", "other"):
        projection = projections[code]
        questionnaire_required = code != "other"
        type_options.append({
            "code": code,
            "label": projection["consumer_label"],
            "xiaoj_role": projection["projection_role"],
            "questionnaire_required": questionnaire_required,
            "founder_personal_visit_design_required": code == "other",
            "call_to_action": "準備意圖場建構問卷"
            if questionnaire_required
            else "申請創辦人核定與親訪設計",
        })
    payload = {
        "schema": GROUP_MEMBER_PRODUCT_SCHEMA,
        "state": "CANDIDATE_PRODUCT_LANDING_NO_EFFECT",
        "title": "小J 分身總場團體會員申請",
        "summary": "由已完成登入與自然身分關連驗證的任一封包帳號進入，逐步確認領域權限、本會核准、封包生效、現實營運準備與創辦人最終核定。",
        "audience": "ASSOCIATION_APPROVED_GROUP_MEMBER_APPLICANT",
        "xiaoj_capability_class": "XIAOJ_ADDON",
        "authority_separation": deepcopy(
            XIAOJ_CORE_SUPPLY_CONTRACT["ownership_and_admin_separation"]
        ),
        "function_category_separation": deepcopy(
            XIAOJ_CORE_SUPPLY_CONTRACT["xiaoj_function_category_separation"]
        ),
        "account_entry_governance": deepcopy(
            XIAOJ_CORE_SUPPLY_CONTRACT["sovereign_ai_packet_account_governance"]
        ),
        "entry_path": GROUP_MEMBER_APPLICATION_ENTRY_PATH,
        "type_options": type_options,
        "journey": [
            {"step": 1, "code": "VERIFY_ACCOUNT_PACKET_ENTRY", "label": "以已驗證登入、自然身分關連及領域權限的封包帳號進入"},
            {"step": 2, "code": "OPEN_FROM_PERSONAL_IDENTITY_PACKET", "label": "由個人主權 AI 8D 封包開啟小J申請功能"},
            {"step": 3, "code": "VERIFY_ASSOCIATION_MEMBERSHIP", "label": "確認本會已核准團體會員"},
            {"step": 4, "code": "VERIFY_PACKET_EFFECTIVE", "label": "確認本系統管理的主權身分封包已由本會生效"},
            {"step": 5, "code": "ALIGN_ODOO_RELATION", "label": "確認 Odoo 團體會員照準關係"},
            {"step": 6, "code": "PREPARE_REAL_WORLD_DESIGN", "label": "完成現實可用問卷，或由創辦人親訪設計其他類型"},
            {"step": 7, "code": "REVIEW_APPLICATION", "label": "預覽全部引用、缺口與不得執行事項"},
            {"step": 8, "code": "FOUNDER_RATIFICATION", "label": "確認創辦人帳號綁定證據後等待本人另行最終核定"},
            {"step": 9, "code": "ESTABLISHMENT_EVIDENCE", "label": "核對成立、範本與總場效果證據"},
        ],
        "status_labels": {
            "DRAFT": "尚未完成",
            "HOLD": "缺少必要證據",
            "PENDING_FOUNDER_RATIFICATION": "等待創辦人核定",
            "PERSONAL_VISIT_DESIGN_REQUIRED": "等待創辦人親訪設計",
            "CANDIDATE": "候選已備妥但尚未成立",
            "ESTABLISHED": "僅在全部權威與效果證據閉合後顯示",
        },
        "trust_copy": [
            "此功能不會因點擊連結或送出資料而自動成立總場。",
            "Odoo 只保存照準關係引用，不保存正式會員身分權威。",
            "協會投影超級管理員代表法人系統管理與所有權，不代表技術所有權人。",
            "同一自然人可綁多帳號；新增及原帳號都須完成登入與關連驗證。",
            "帳號合併不合併權限；各帳號只開通明示領域權限，衝突時拒絕優先。",
            "本人帳號納入封包只建立身分入口，不等於本人已核定任何總場成立。",
            "請勿輸入會員明文、金鑰、密碼或營業秘密原文。",
            "你可以先預覽缺口；正式成立前仍需創辦人本人核定。",
        ],
        "api_refs": {
            "questionnaire": GROUP_MEMBER_QUESTIONNAIRE_API_PATH,
            "application_candidate": GROUP_MEMBER_APPLICATION_CANDIDATE_API_PATH,
            "multi_account_binding_candidate": SOVEREIGN_AI_ACCOUNT_BINDING_API_PATH,
            "multi_account_governance_candidate": SOVEREIGN_AI_ACCOUNT_GOVERNANCE_API_PATH,
        },
        "accessibility": {
            "language": "zh-Hant",
            "plain_language_required": True,
            "keyboard_navigation_required": True,
            "status_not_color_only": True,
        },
        "effects": {
            "odoo_write": False,
            "identity_packet_mutation": False,
            "account_binding_persisted": False,
            "account_entry_activated": False,
            "domain_permission_granted_or_coordinated": False,
            "founder_control_exposed_or_executed": False,
            "application_persisted": False,
            "founder_ratification_recorded": False,
            "total_field_established": False,
            "template_applied": False,
            "deployment": False,
        },
        "landing_gaps": [
            "PERSONAL_IDENTITY_PACKET_RENDERER_BINDING_UNVERIFIED",
            "MULTI_ACCOUNT_LOGIN_AND_NATURAL_IDENTITY_RELATION_VERIFIERS_UNBOUND",
            "FOUNDER_PERSONAL_ACCOUNT_PACKET_BINDING_VERIFIER_UNBOUND",
            "DOMAIN_PERMISSION_COORDINATION_POLICY_UNRATIFIED",
            "FOUNDER_EXCLUSIVE_CONSOLE_SEAT_GATE_UNBOUND",
            "ASSOCIATION_MEMBERSHIP_AND_PACKET_EFFECT_VERIFIERS_UNBOUND",
            "ODOO_RELATIONSHIP_VERIFIER_UNBOUND",
            "FOUNDER_RATIFICATION_RECEIPT_UNBOUND",
            "TOTAL_FIELD_ESTABLISHMENT_EFFECT_UNBOUND",
        ],
        "next": "BIND_READ_ONLY_VERIFIERS_BEFORE_ANY_PERSISTENCE_OR_ESTABLISHMENT",
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def build_group_member_field_application_entry(
    *,
    personal_identity_packet_ref: Any = None,
    account_entry_binding_ref: Any = None,
    account_domain_permission_ref: Any = None,
) -> dict[str, Any]:
    """Expose an opaque, credential-free XiaoJ add-on application link."""
    packet_ref = _opaque_ref(personal_identity_packet_ref)
    entry_binding_ref = _opaque_ref(account_entry_binding_ref)
    domain_permission_ref = _opaque_ref(account_domain_permission_ref)
    entry_refs_present = all(
        item["present"] for item in (packet_ref, entry_binding_ref, domain_permission_ref)
    )
    addon = deepcopy(
        XIAOJ_CORE_SUPPLY_CONTRACT["xiaoj_addon_capabilities"][
            "group_member_total_field_application"
        ]
    )
    payload = {
        "state": "CANDIDATE_VISIBLE_APPLICATION_LINK"
        if entry_refs_present
        else "HOLD_PACKET_ACCOUNT_ENTRY_AND_DOMAIN_PERMISSION_REFS_REQUIRED",
        "addon": addon,
        "personal_identity_packet_ref": packet_ref,
        "account_entry_binding_ref": entry_binding_ref,
        "account_domain_permission_ref": domain_permission_ref,
        "link_visible": entry_refs_present,
        "application_entry_path": GROUP_MEMBER_APPLICATION_ENTRY_PATH,
        "packet_active_verified": False,
        "account_login_verified": False,
        "natural_identity_relation_verified": False,
        "account_entry_binding_verified": False,
        "account_domain_permission_verified": False,
        "application_submitted": False,
        "total_field_established": False,
        "execution_authority": False,
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def plan_group_member_total_field_application(
    *,
    projection_kind: Any = None,
    group_member_ref: Any = None,
    personal_identity_packet_ref: Any = None,
    identity_packet_active_evidence_ref: Any = None,
    account_entry_binding_ref: Any = None,
    account_domain_permission_ref: Any = None,
    association_group_member_approval_evidence_ref: Any = None,
    odoo_relationship_ref: Any = None,
    requested_total_field_ref: Any = None,
    intent_field_questionnaire_ref: Any = None,
    questionnaire_real_world_usability_evidence_ref: Any = None,
) -> dict[str, Any]:
    """Build an application candidate that still requires founder ratification."""
    kind = str(projection_kind or "").strip().lower()
    projection = XIAOJ_CORE_SUPPLY_CONTRACT["projection_kinds"].get(kind)
    refs = {
        "group_member_ref": _opaque_ref(group_member_ref),
        "personal_identity_packet_ref": _opaque_ref(personal_identity_packet_ref),
        "identity_packet_active_evidence_ref": _opaque_ref(identity_packet_active_evidence_ref),
        "account_entry_binding_ref": _opaque_ref(account_entry_binding_ref),
        "account_domain_permission_ref": _opaque_ref(account_domain_permission_ref),
        "association_group_member_approval_evidence_ref": _opaque_ref(
            association_group_member_approval_evidence_ref
        ),
        "odoo_relationship_ref": _opaque_ref(odoo_relationship_ref),
        "requested_total_field_ref": _opaque_ref(requested_total_field_ref),
        "intent_field_questionnaire_ref": _opaque_ref(intent_field_questionnaire_ref),
        "questionnaire_real_world_usability_evidence_ref": _opaque_ref(
            questionnaire_real_world_usability_evidence_ref
        ),
    }
    questionnaire_required = kind in {"merchant", "committee", "nonprofit_association"}
    always_required = (
        "group_member_ref",
        "personal_identity_packet_ref",
        "identity_packet_active_evidence_ref",
        "account_entry_binding_ref",
        "account_domain_permission_ref",
        "association_group_member_approval_evidence_ref",
        "odoo_relationship_ref",
        "requested_total_field_ref",
    )
    questionnaire_refs = (
        "intent_field_questionnaire_ref",
        "questionnaire_real_world_usability_evidence_ref",
    )
    required_refs = always_required + questionnaire_refs if questionnaire_required else always_required
    missing = [key for key in required_refs if not refs[key]["present"]]
    eligible_class = bool(
        projection
        and projection.get("establishment_class") == "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD"
    )
    if projection is None:
        state = "HOLD_UNKNOWN_PROJECTION_KIND"
        next_action = "SELECT_GOVERNED_GROUP_MEMBER_PROJECTION_KIND"
    elif not eligible_class:
        state = "HOLD_NOT_GROUP_MEMBER_TOTAL_FIELD_PROJECTION"
        next_action = "USE_NON_GROUP_MEMBER_PROJECTION_GOVERNANCE"
    elif missing:
        state = "HOLD_GROUP_MEMBER_APPLICATION_PREREQUISITES"
        next_action = "SUPPLY_ACTIVE_PACKET_ASSOCIATION_APPROVAL_ODOO_AND_FIELD_REFS"
    elif kind == "other":
        state = "CANDIDATE_PENDING_FOUNDER_RATIFICATION_AND_PERSONAL_VISIT_DESIGN"
        next_action = "REQUEST_FOUNDER_RATIFICATION_AND_PERSONAL_VISIT_DESIGN"
    else:
        state = "CANDIDATE_PENDING_FOUNDER_RATIFICATION"
        next_action = "VERIFY_APPLICATION_CHAIN_AND_REQUEST_FOUNDER_RATIFICATION"
    payload = {
        "schema": GROUP_MEMBER_APPLICATION_SCHEMA,
        "state": state,
        "projection_kind": kind or None,
        "projection": deepcopy(projection),
        "addon": deepcopy(
            XIAOJ_CORE_SUPPLY_CONTRACT["xiaoj_addon_capabilities"][
                "group_member_total_field_application"
            ]
        ),
        "establishment_policy": deepcopy(
            XIAOJ_CORE_SUPPLY_CONTRACT["group_member_total_field_establishment"]
        ),
        "refs": refs,
        "missing_prerequisites": missing,
        "questionnaire_required": questionnaire_required,
        "questionnaire_real_world_usability_verified": False,
        "founder_personal_visit_design_required": kind == "other",
        "founder_personal_visit_design_verified": False,
        "association_group_member_approval_verified": False,
        "identity_packet_active_verified": False,
        "identity_packet_management_verified": False,
        "account_entry_binding_verified": False,
        "account_domain_permission_verified": False,
        "odoo_relationship_verified": False,
        "application_persisted": False,
        "application_submitted": False,
        "founder_ratification_verified": False,
        "total_field_established": False,
        "projection_activated": False,
        "execution_authority": False,
        "safety_flags": deepcopy(SAFETY_FLAGS),
        "next": next_action,
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def plan_xiaoj_field_projection(
    *,
    projection_kind: Any,
    total_field_ref: Any = None,
    mode_ref: Any = None,
    appearance_profile_ref: Any = None,
    odoo_relationship_ref: Any = None,
    group_member_application_ref: Any = None,
    personal_identity_packet_ref: Any = None,
    identity_packet_active_evidence_ref: Any = None,
    association_group_member_approval_evidence_ref: Any = None,
    founder_establishment_approval_evidence_ref: Any = None,
    founder_account_packet_binding_evidence_ref: Any = None,
    founder_personal_visit_design_evidence_ref: Any = None,
    intent_field_questionnaire_ref: Any = None,
    questionnaire_real_world_usability_evidence_ref: Any = None,
) -> dict[str, Any]:
    """Build a non-activating governed XiaoJ field projection candidate."""
    kind = str(projection_kind or "").strip().lower()
    projection = XIAOJ_CORE_SUPPLY_CONTRACT["projection_kinds"].get(kind)
    refs = {
        "total_field_ref": _opaque_ref(total_field_ref),
        "mode_ref": _opaque_ref(mode_ref),
        "appearance_profile_ref": _opaque_ref(appearance_profile_ref),
        "odoo_relationship_ref": _opaque_ref(odoo_relationship_ref),
        "group_member_application_ref": _opaque_ref(group_member_application_ref),
        "personal_identity_packet_ref": _opaque_ref(personal_identity_packet_ref),
        "identity_packet_active_evidence_ref": _opaque_ref(identity_packet_active_evidence_ref),
        "association_group_member_approval_evidence_ref": _opaque_ref(
            association_group_member_approval_evidence_ref
        ),
        "founder_establishment_approval_evidence_ref": _opaque_ref(
            founder_establishment_approval_evidence_ref
        ),
        "founder_account_packet_binding_evidence_ref": _opaque_ref(
            founder_account_packet_binding_evidence_ref
        ),
        "founder_personal_visit_design_evidence_ref": _opaque_ref(
            founder_personal_visit_design_evidence_ref
        ),
        "intent_field_questionnaire_ref": _opaque_ref(intent_field_questionnaire_ref),
        "questionnaire_real_world_usability_evidence_ref": _opaque_ref(
            questionnaire_real_world_usability_evidence_ref
        ),
    }
    common_missing = [
        key
        for key in ("total_field_ref", "mode_ref")
        if not refs[key]["present"]
    ]
    group_member_projection = bool(
        projection
        and projection.get("establishment_class") == "ASSOCIATION_GROUP_MEMBER_TOTAL_FIELD"
    )
    group_member_required = (
        "odoo_relationship_ref",
        "group_member_application_ref",
        "personal_identity_packet_ref",
        "identity_packet_active_evidence_ref",
        "association_group_member_approval_evidence_ref",
        "founder_account_packet_binding_evidence_ref",
        "founder_establishment_approval_evidence_ref",
    )
    if kind == "other":
        group_member_required += ("founder_personal_visit_design_evidence_ref",)
    elif kind in {"merchant", "committee", "nonprofit_association"}:
        group_member_required += (
            "intent_field_questionnaire_ref",
            "questionnaire_real_world_usability_evidence_ref",
        )
    group_member_missing = [
        key for key in group_member_required if group_member_projection and not refs[key]["present"]
    ]
    missing = common_missing + group_member_missing
    if projection is None:
        state = "HOLD_UNKNOWN_PROJECTION_KIND"
        next_action = "SELECT_GOVERNED_PROJECTION_KIND"
    elif missing:
        state = "HOLD_FIELD_PROJECTION_BINDING_REQUIRED"
        next_action = "SUPPLY_COMPLETE_GROUP_MEMBER_ESTABLISHMENT_CHAIN_REFS"
    else:
        state = "CANDIDATE_FIELD_PROJECTION"
        next_action = "VERIFY_FIELD_MODE_AND_ESTABLISHMENT_AUTHORITY_BINDINGS"

    payload = {
        "schema": FIELD_PROJECTION_SCHEMA,
        "state": state,
        "projection_kind": kind or None,
        "projection": deepcopy(projection),
        "core_supplier": XIAOJ_CORE_SUPPLY_CONTRACT["supplier"],
        "core_identity_immutable": True,
        "core_identity_mutated": False,
        "core_capabilities": sorted(XIAOJ_CORE_SUPPLY_CONTRACT["core_capabilities"]),
        "mode_application_authority": XIAOJ_CORE_SUPPLY_CONTRACT["mode_application_authority"],
        "mode_applied": False,
        "projection_activated": False,
        "membership_alignment": deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT["membership_alignment"]),
        "field_projection_identity": deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT["field_projection_identity"]),
        "association_identity_approval_verified": False,
        "group_member_application_verified": False,
        "identity_packet_active_verified": False,
        "founder_account_packet_binding_verified": False,
        "founder_establishment_approval_verified": False,
        "founder_personal_visit_design_verified": False,
        "questionnaire_real_world_usability_verified": False,
        "projection_established": False,
        "refs": refs,
        "missing_bindings": missing,
        "execution_authority": False,
        "safety_flags": deepcopy(SAFETY_FLAGS),
        "next": next_action,
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def plan_local_trade_secret_request(
    *,
    approved_device_ref: Any = None,
    device_approval_evidence_ref: Any = None,
    total_field_ref: Any = None,
    request_policy_ref: Any = None,
    purpose_scope_ref: Any = None,
    time_window_ref: Any = None,
    secret_scope_ref: Any = None,
) -> dict[str, Any]:
    """Build a request candidate without reading or releasing secret bytes."""
    refs = {
        "approved_device_ref": _opaque_ref(approved_device_ref),
        "device_approval_evidence_ref": _opaque_ref(device_approval_evidence_ref),
        "total_field_ref": _opaque_ref(total_field_ref),
        "request_policy_ref": _opaque_ref(request_policy_ref),
        "purpose_scope_ref": _opaque_ref(purpose_scope_ref),
        "time_window_ref": _opaque_ref(time_window_ref),
        "secret_scope_ref": _opaque_ref(secret_scope_ref),
    }
    required = tuple(refs)
    missing = [key for key in required if not refs[key]["present"]]
    eligible_candidate = not missing
    state = (
        "CANDIDATE_AUTOMATIC_TOTAL_FIELD_DECISION"
        if eligible_candidate
        else "HOLD_AUTOMATIC_APPROVAL_PREREQUISITES"
    )
    payload = {
        "schema": LOCAL_SECRET_REQUEST_SCHEMA,
        "state": state,
        "policy": deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT["local_trade_secret_policy"]),
        "refs": refs,
        "missing_prerequisites": missing,
        "automatic_approval_eligible_candidate": eligible_candidate,
        "device_approval_verified": False,
        "request_policy_verified": False,
        "purpose_scope_verified": False,
        "time_window_verified": False,
        "total_field_decision_verified": False,
        "external_drive_runtime_state_verified": False,
        "automatic_approval_decision": False,
        "secret_released": False,
        "external_drive_read": False,
        "odoo_write": False,
        "execution_authority": False,
        "next": "VERIFY_ALL_BINDINGS_IN_THIS_SYSTEM_TOTAL_FIELD",
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def plan_distributed_device_admission(
    *,
    device_ref: Any = None,
    device_capability_manifest_ref: Any = None,
    total_field_ref: Any = None,
    founder_approval_evidence_ref: Any = None,
    association_approved_identity_packet_ref: Any = None,
) -> dict[str, Any]:
    """Build a founder-gated device admission candidate without enrollment."""
    refs = {
        "device_ref": _opaque_ref(device_ref),
        "device_capability_manifest_ref": _opaque_ref(device_capability_manifest_ref),
        "total_field_ref": _opaque_ref(total_field_ref),
        "founder_approval_evidence_ref": _opaque_ref(founder_approval_evidence_ref),
        "association_approved_identity_packet_ref": _opaque_ref(
            association_approved_identity_packet_ref
        ),
    }
    missing = [key for key, value in refs.items() if not value["present"]]
    state = "CANDIDATE_FOUNDER_ADMISSION_DECISION" if not missing else "HOLD_DEVICE_ADMISSION_PREREQUISITES"
    payload = {
        "schema": DEVICE_ADMISSION_SCHEMA,
        "state": state,
        "governance": deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT["distributed_compute_governance"]),
        "refs": refs,
        "missing_prerequisites": missing,
        "founder_approval_verified": False,
        "association_identity_approval_verified": False,
        "identity_packet_management_verified": False,
        "total_field_binding_verified": False,
        "device_established": False,
        "device_enrolled": False,
        "role_elevated": False,
        "execution_authority": False,
        "next": "VERIFY_FOUNDER_APPROVAL_AND_TOTAL_FIELD_BINDING",
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def plan_founder_base_template_application(
    *,
    requesting_device_ref: Any = None,
    founder_base_device_ref: Any = None,
    founder_base_device_authority_evidence_ref: Any = None,
    total_field_ref: Any = None,
    mode_ref: Any = None,
    template_ref: Any = None,
    target_projection_ref: Any = None,
    target_identity_packet_ref: Any = None,
    target_field_type: Any = None,
    template_origin: Any = None,
    founder_personal_visit_design_evidence_ref: Any = None,
) -> dict[str, Any]:
    """Build a local-founder-device-only template application candidate."""
    requester_text = str(requesting_device_ref or "").strip()
    founder_device_text = str(founder_base_device_ref or "").strip()
    target_type = str(target_field_type or "").strip().lower()
    origin = str(template_origin or "").strip().lower()
    refs = {
        "requesting_device_ref": _opaque_ref(requester_text),
        "founder_base_device_ref": _opaque_ref(founder_device_text),
        "founder_base_device_authority_evidence_ref": _opaque_ref(
            founder_base_device_authority_evidence_ref
        ),
        "total_field_ref": _opaque_ref(total_field_ref),
        "mode_ref": _opaque_ref(mode_ref),
        "template_ref": _opaque_ref(template_ref),
        "target_projection_ref": _opaque_ref(target_projection_ref),
        "target_identity_packet_ref": _opaque_ref(target_identity_packet_ref),
        "founder_personal_visit_design_evidence_ref": _opaque_ref(
            founder_personal_visit_design_evidence_ref
        ),
    }
    required_ref_keys = tuple(key for key in refs if key != "founder_personal_visit_design_evidence_ref")
    if target_type == "other":
        required_ref_keys += ("founder_personal_visit_design_evidence_ref",)
    missing = [key for key in required_ref_keys if not refs[key]["present"]]
    if not target_type:
        missing.append("target_field_type")
    if not origin:
        missing.append("template_origin")
    requester_claim_matches = bool(requester_text and requester_text == founder_device_text)
    allowed_target_types = set(XIAOJ_CORE_SUPPLY_CONTRACT["projection_kinds"])
    if target_type and target_type not in allowed_target_types:
        state = "HOLD_UNKNOWN_TEMPLATE_TARGET_FIELD_TYPE"
        next_action = "SELECT_GOVERNED_TEMPLATE_TARGET_FIELD_TYPE"
    elif target_type == "other" and origin and origin != "founder_personal_visit_design":
        state = "HOLD_OTHER_TYPE_GENERIC_TEMPLATE_PROHIBITED"
        next_action = "USE_FOUNDER_PERSONAL_VISIT_DESIGN_ORIGIN"
    elif missing:
        state = "HOLD_TEMPLATE_APPLICATION_PREREQUISITES"
        next_action = "SUPPLY_FOUNDER_DEVICE_TOTAL_FIELD_MODE_AND_TEMPLATE_REFS"
    elif not requester_claim_matches:
        state = "HOLD_TEMPLATE_APPLICATION_DEVICE_BOUNDARY"
        next_action = "ROUTE_TO_THIS_LOCAL_FOUNDER_BASE_DEVICE"
    else:
        state = "CANDIDATE_FOUNDER_BASE_TEMPLATE_APPLICATION"
        next_action = "VERIFY_FOUNDER_BASE_DEVICE_AND_TOTAL_FIELD_BINDINGS"
    payload = {
        "schema": TEMPLATE_APPLICATION_SCHEMA,
        "state": state,
        "target_field_type": target_type or None,
        "template_origin": origin or None,
        "governance": deepcopy(XIAOJ_CORE_SUPPLY_CONTRACT["distributed_compute_governance"]),
        "refs": refs,
        "missing_prerequisites": missing,
        "requester_claim_matches_founder_base_ref": requester_claim_matches,
        "founder_base_device_verified": False,
        "total_field_binding_verified": False,
        "mode_binding_verified": False,
        "template_authority_verified": False,
        "target_identity_packet_verified": False,
        "founder_personal_visit_design_verified": False,
        "generic_template_blocked_for_other": target_type == "other",
        "template_applied": False,
        "template_copied": False,
        "template_delegated": False,
        "projection_activated": False,
        "execution_authority": False,
        "next": next_action,
    }
    payload["candidate_sha256"] = _sha256(payload)
    return payload


def _capability_index() -> dict[str, dict[str, Any]]:
    return {str(item["code"]): deepcopy(item) for item in CAPABILITIES}


def build_merchant_capability_catalog() -> dict[str, Any]:
    """Return a deterministic, candidate-only equivalence catalog."""
    capabilities = [deepcopy(item) for item in CAPABILITIES]
    payload = {
        "schema": CATALOG_SCHEMA,
        "state": "CANDIDATE_FUNCTIONAL_EQUIVALENCE",
        "source_product": "QuickClick",
        "target_system": "Odoo 18",
        "service_agent": "XiaoJ merchant service agent",
        "authority": "ODOO_ROLE_BINDING_AND_HUMAN_RELEASE",
        "xiaoj_core_supply": build_xiaoj_core_supply_contract(),
        "xiaoj_audiovisual_projection": deepcopy(XIAOJ_AUDIOVISUAL_PROJECTION_CONTRACT),
        "capabilities": capabilities,
        "safety_flags": deepcopy(SAFETY_FLAGS),
    }
    payload["catalog_sha256"] = _sha256(payload)
    return payload


def detect_merchant_capability(text: Any) -> str | None:
    normalized = str(text or "").strip().lower()
    for code, keywords in KEYWORD_RULES:
        if any(keyword.lower() in normalized for keyword in keywords):
            return code
    return None


def _parameter_key_is_protected(key: Any) -> bool:
    normalized = str(key or "").strip().lower().replace("-", "_")
    return any(part in normalized for part in PROTECTED_PARAMETER_PARTS)


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value.strip()[:256]
    if isinstance(value, (list, tuple)):
        rows = []
        for item in value[:20]:
            if isinstance(item, (dict, list, tuple, set)):
                raise ValueError("nested_parameter_values_are_not_supported")
            rows.append(_safe_value(item))
        return rows
    raise ValueError("unsupported_parameter_value_type")


def _sanitize_parameters(parameters: Any, allowed: set[str]) -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    if not isinstance(parameters, Mapping):
        return {}, [], [], ["parameters"] if parameters not in (None, "") else []
    accepted: dict[str, Any] = {}
    unsupported: list[str] = []
    protected: list[str] = []
    invalid: list[str] = []
    for raw_key, value in parameters.items():
        key = str(raw_key or "").strip()
        if _parameter_key_is_protected(key):
            protected.append(key)
            continue
        if key not in allowed:
            unsupported.append(key)
            continue
        try:
            accepted[key] = _safe_value(value)
        except ValueError:
            invalid.append(key)
    return accepted, sorted(unsupported), sorted(protected), sorted(invalid)


def plan_merchant_action(
    *,
    capability_code: Any = None,
    text: Any = None,
    actor_ref: Any = None,
    actor_role: Any = "service_agent",
    total_field_ref: Any = None,
    mode_ref: Any = None,
    appearance_profile_ref: Any = None,
    parameters: Any = None,
) -> dict[str, Any]:
    """Build a non-executing XiaoJ merchant action candidate."""
    explicit_code = str(capability_code or "").strip()
    detected_code = detect_merchant_capability(text)
    selected_code = explicit_code or detected_code or ""
    capability = _capability_index().get(selected_code)
    actor_ref_text = str(actor_ref or "").strip()
    total_field_ref_text = str(total_field_ref or "").strip()
    mode_ref_text = str(mode_ref or "").strip()
    appearance_profile_ref_text = str(appearance_profile_ref or "").strip()
    claimed_role = str(actor_role or "service_agent").strip().lower()

    base = {
        "schema": PLAN_SCHEMA,
        "capability_code": selected_code or None,
        "detected_from_text": bool(not explicit_code and detected_code),
        "actor_ref_present": bool(actor_ref_text),
        "actor_ref_sha256": hashlib.sha256(actor_ref_text.encode("utf-8")).hexdigest() if actor_ref_text else None,
        "claimed_role": claimed_role,
        "role_binding_verified": False,
        "execution_authority": False,
        "xiaoj_audiovisual_projection": {
            **deepcopy(XIAOJ_AUDIOVISUAL_PROJECTION_CONTRACT),
            "total_field_ref_present": bool(total_field_ref_text),
            "total_field_ref_sha256": hashlib.sha256(total_field_ref_text.encode("utf-8")).hexdigest()
            if total_field_ref_text
            else None,
            "mode_ref_present": bool(mode_ref_text),
            "mode_ref_sha256": hashlib.sha256(mode_ref_text.encode("utf-8")).hexdigest() if mode_ref_text else None,
            "appearance_profile_ref_present": bool(appearance_profile_ref_text),
            "appearance_profile_ref_sha256": hashlib.sha256(appearance_profile_ref_text.encode("utf-8")).hexdigest()
            if appearance_profile_ref_text
            else None,
            "total_field_binding_verified": False,
            "mode_binding_verified": False,
            "appearance_projection_verified": False,
            "mode_applied": False,
        },
        "safety_flags": deepcopy(SAFETY_FLAGS),
    }

    if capability is None:
        return {
            **base,
            "state": "HOLD_UNKNOWN_CAPABILITY",
            "capability": None,
            "accepted_parameters": {},
            "conflicts": [],
            "unknowns": ["capability_code", "total_field_mode_binding"],
            "next": "SELECT_CAPABILITY_FROM_CATALOG",
        }

    allowed = set(capability["allowed_parameters"])
    accepted, unsupported, protected, invalid = _sanitize_parameters(parameters, allowed)
    conflicts = []
    if protected:
        conflicts.append("PROTECTED_PARAMETER_REJECTED")
    if unsupported:
        conflicts.append("UNSUPPORTED_PARAMETER_REJECTED")
    if invalid:
        conflicts.append("INVALID_PARAMETER_VALUE_REJECTED")

    if conflicts:
        state = "HOLD_PARAMETER_BOUNDARY"
        next_action = "REMOVE_REJECTED_PARAMETERS"
    elif capability["implementation_state"] in {"DESIGN_ONLY", "BINDING_REQUIRED"}:
        state = "HOLD_RUNTIME_BINDING_REQUIRED"
        next_action = "IMPLEMENT_AND_VERIFY_ODOO_CAPABILITY_BINDING"
    elif capability["mode"] == "human_release":
        state = "HOLD_HUMAN_RELEASE_REQUIRED"
        next_action = "VERIFY_ROLE_BINDING_AND_REQUEST_HUMAN_RELEASE"
    elif capability["mode"] == "candidate_only":
        state = "PASS_CANDIDATE"
        next_action = "VERIFY_CANONICAL_SOURCE_BEFORE_EXECUTION"
    else:
        state = "READY_READ_ONLY_PLAN"
        next_action = "CALL_VERIFIED_READ_ONLY_SERVICE"

    return {
        **base,
        "state": state,
        "capability": capability,
        "accepted_parameters": accepted,
        "rejected_parameters": {
            "unsupported": unsupported,
            "protected": protected,
            "invalid": invalid,
        },
        "requires_human_release": capability["mode"] == "human_release",
        "release_roles": capability["release_roles"],
        "conflicts": conflicts,
        "unknowns": ["live_role_binding", "total_field_mode_binding", "runtime_effect"]
        if not conflicts
        else ["live_role_binding", "total_field_mode_binding"],
        "next": next_action,
        "candidate_sha256": _sha256({
            "capability_code": selected_code,
            "accepted_parameters": accepted,
            "claimed_role": claimed_role,
            "state": state,
        }),
    }
