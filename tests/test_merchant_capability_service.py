from __future__ import annotations

import importlib.util
import os
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(
    ROOT,
    "Taiji_Odoo",
    "addons",
    "wuchang_cafe_ai_gateway",
    "services",
    "merchant_capability_service.py",
)
CONTROLLER_PATH = os.path.join(
    ROOT,
    "Taiji_Odoo",
    "addons",
    "wuchang_cafe_ai_gateway",
    "controllers",
    "main.py",
)

spec = importlib.util.spec_from_file_location("merchant_capability_service_under_test", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

build_catalog = module.build_merchant_capability_catalog
build_core_contract = module.build_xiaoj_core_supply_contract
build_application_entry = module.build_group_member_field_application_entry
build_questionnaire = module.build_group_member_intent_field_questionnaire
build_product_candidate = module.build_group_member_total_field_product_candidate
build_account_governance_candidate = module.build_sovereign_ai_multi_account_governance_candidate
detect_capability = module.detect_merchant_capability
plan_field_projection = module.plan_xiaoj_field_projection
plan_group_member_application = module.plan_group_member_total_field_application
plan_device_admission = module.plan_distributed_device_admission
plan_template_application = module.plan_founder_base_template_application
plan_secret_request = module.plan_local_trade_secret_request
plan_account_binding = module.plan_sovereign_ai_multi_account_binding
plan_action = module.plan_merchant_action


class MerchantCapabilityServiceTests(unittest.TestCase):
    def test_catalog_covers_observed_quickclick_backoffice_functions(self):
        catalog = build_catalog()
        codes = {item["code"] for item in catalog["capabilities"]}
        self.assertTrue({
            "operations.summary",
            "operations.orders",
            "operations.shop_report",
            "merchant.store_profile",
            "catalog.menu",
            "sales.query",
            "customer.blocklist",
            "operations.report_360",
            "identity.account_manage",
            "marketing.promotions",
        }.issubset(codes))
        self.assertEqual(catalog["state"], "CANDIDATE_FUNCTIONAL_EQUIVALENCE")
        self.assertFalse(catalog["safety_flags"]["ODOO_DB_WRITE"])
        projection = catalog["xiaoj_audiovisual_projection"]
        self.assertTrue(projection["core_identity_immutable"])
        self.assertTrue(projection["appearance_is_field_projection"])
        self.assertEqual(projection["mode_application_authority"], "THIS_SYSTEM_TOTAL_FIELD_ONLY")
        self.assertFalse(projection["service_agent_can_apply_mode"])
        self.assertFalse(projection["cross_total_field_implicit_mode_reuse"])

    def test_core_is_system_supplied_and_roles_are_field_projections(self):
        contract = build_core_contract()
        self.assertEqual(contract["supplier"], "THIS_SYSTEM_TOTAL_FIELD")
        self.assertTrue(contract["core_identity_immutable"])
        projections = contract["projection_kinds"]
        self.assertEqual(projections["merchant"]["projection_role"], "商家櫃台點餐服務員")
        self.assertEqual(projections["committee"]["projection_role"], "大廳服務台服務員")
        self.assertEqual(projections["association"]["projection_role"], "AI副總幹事")
        self.assertEqual(projections["nonprofit_association"]["consumer_label"], "非營利組織協會")
        self.assertEqual(projections["other"]["consumer_label"], "其他類型")
        self.assertEqual(projections["founder"]["projection_role"], "AI開發助手")
        self.assertFalse(contract["consumer_projection_can_apply_mode"])
        governance = contract["distributed_compute_governance"]
        self.assertEqual(governance["topology"], "DISTRIBUTED_COMPUTE_DEVICE_FEDERATION")
        self.assertEqual(governance["device_establishment_authority"], "FOUNDER_EXPLICIT_APPROVAL_ONLY")
        self.assertEqual(
            governance["template_application_authority"],
            "THIS_LOCAL_FOUNDER_BASE_DEVICE_ONLY",
        )
        self.assertFalse(governance["device_self_enrollment"])
        self.assertFalse(governance["remote_node_can_apply_template"])
        addon = contract["xiaoj_addon_capabilities"]["group_member_total_field_application"]
        self.assertEqual(addon["capability_class"], "XIAOJ_ADDON")
        self.assertFalse(addon["is_immutable_core_capability"])
        self.assertFalse(addon["core_identity_mutated"])

    def test_core_capabilities_include_governed_hexagram_stems_branches_and_hash(self):
        contract = build_core_contract()
        capabilities = contract["core_capabilities"]
        hexagram = capabilities["hexagram_state_encoding"]
        self.assertEqual(hexagram["scope"], "64_HEXAGRAM_STATE_CODES")
        self.assertEqual(
            hexagram["evidence_state"],
            "SAFE_PUBLIC_REFERENCE_NOT_CURRENT_8D_CANONICAL_CORE",
        )
        self.assertFalse(hexagram["private_mapping_exposed"])
        self.assertFalse(hexagram["numeric_contract_inferred"])
        self.assertIn("heavenly_stem_time_index", capabilities)
        self.assertIn("earthly_branch_domain_index", capabilities)
        self.assertIn("hash_evidence_binding", capabilities)
        self.assertNotIn("group_member_total_field_application", capabilities)

    def test_membership_is_odoo_alignment_reference_not_formal_registry(self):
        contract = build_core_contract()
        alignment = contract["membership_alignment"]
        self.assertEqual(alignment["scope"], "ALL_ORGANIZATIONAL_MEMBERS")
        self.assertEqual(alignment["odoo_usage"], "ALIGNMENT_RELATION_REFERENCE_ONLY")
        self.assertFalse(alignment["odoo_is_formal_member_registry"])
        self.assertFalse(alignment["member_plaintext_in_projection"])
        identity = contract["field_projection_identity"]
        self.assertEqual(identity["packet_manager"], "THIS_SYSTEM_TOTAL_FIELD")
        self.assertEqual(identity["approval_authority"], "ASSOCIATION_GOVERNANCE")
        self.assertTrue(identity["association_approval_required"])
        self.assertFalse(identity["field_projection_can_manage_or_approve_packet"])
        separation = contract["ownership_and_admin_separation"]
        self.assertEqual(
            separation["association_projection_super_admin_account"],
            "admin@wuchang.life",
        )
        self.assertTrue(separation["represents_legal_person_system_ownership"])
        self.assertFalse(separation["represents_technical_ownership"])
        self.assertFalse(separation["may_substitute_for_founder_ratification"])

    def test_sovereign_ai_packet_supports_multi_account_domain_entries_without_plaintext(self):
        governance = build_core_contract()["sovereign_ai_packet_account_governance"]
        self.assertEqual(
            governance["identity_seat_position"],
            "D8_ENVELOPE_PREREQUISITE_NOT_D1_INTENT",
        )
        self.assertTrue(governance["multiple_accounts_allowed"])
        self.assertTrue(governance["multiple_domain_permissions_allowed"])
        self.assertTrue(governance["each_active_aligned_account_may_be_packet_entry"])
        self.assertTrue(governance["multi_account_merge_requires_all_account_login_verification"])
        self.assertTrue(governance["existing_account_reverification_required_on_merge"])
        self.assertFalse(governance["permission_union_across_accounts_allowed"])
        self.assertFalse(governance["account_merge_may_elevate_permission"])
        self.assertFalse(governance["account_plaintext_in_projection_or_api"])
        founder = governance["required_founder_account_binding"]
        self.assertEqual(len(founder["normalized_login_sha256"]), 64)
        self.assertNotIn("account_login", founder)
        self.assertFalse(governance["account_binding_alone_authorizes_founder_ratification"])

    def test_market_user_field_management_and_founder_categories_are_separated(self):
        separation = build_core_contract()["xiaoj_function_category_separation"]
        general = separation["general_market_user_categories"]
        self.assertEqual(
            {item["label"] for item in general.values()},
            {"生活輔助", "工作協作", "個人娛樂", "帳號綁定"},
        )
        field_services = separation["field_service_categories"]
        self.assertEqual(
            {item["label"] for item in field_services.values()},
            {"管委會大樓功能", "商家會員功能"},
        )
        management = separation["role_gated_management_backend"]
        self.assertTrue(management["verified_field_management_role_binding_required"])
        self.assertTrue(management["management_role_does_not_grant_founder_authority"])
        self.assertTrue(management["management_role_does_not_become_member_identity_authority"])
        self.assertFalse(separation["general_market_ui_may_expose_founder_controls"])
        self.assertTrue(separation["founder_console_requires_verified_founder_seat"])

    def test_multi_account_merge_requires_login_and_relation_proof_for_existing_and_new(self):
        result = plan_account_binding(
            sovereign_ai_packet_ref="packet:founder",
            natural_identity_ref="natural-person:founder",
            permission_coordination_policy_ref="policy:deny-first",
            account_bindings=[
                {
                    "binding_state": "existing",
                    "account_type": "google_email_after_consent",
                    "account_login_sha256": module.REQUIRED_FOUNDER_ACCOUNT_LOGIN_SHA256,
                    "account_ref": "account:founder-required",
                    "account_login_verification_evidence_ref": "login-proof:existing",
                    "natural_identity_relation_evidence_ref": "relation-proof:existing",
                    "account_binding_evidence_ref": "binding-proof:existing",
                    "existing_binding_reverification_evidence_ref": "reverify:existing",
                    "external_account_consent_evidence_ref": "consent:existing",
                    "domain_permission_refs": ["domain:founder-development"],
                },
                {
                    "binding_state": "new",
                    "account_type": "chatgpt_user_email",
                    "account_login_sha256": "a" * 64,
                    "account_ref": "account:new",
                    "account_login_verification_evidence_ref": "login-proof:new",
                    "natural_identity_relation_evidence_ref": "relation-proof:new",
                    "account_binding_evidence_ref": "binding-proof:new",
                    "external_account_consent_evidence_ref": "consent:new",
                    "domain_permission_refs": ["domain:xiaoj-development"],
                },
            ],
        )
        self.assertEqual(
            result["state"],
            "CANDIDATE_MULTI_ACCOUNT_MERGE_PENDING_VERIFICATION",
        )
        self.assertTrue(result["required_founder_account_binding_present"])
        self.assertTrue(result["all_existing_and_new_account_evidence_present"])
        self.assertFalse(result["all_account_logins_verified"])
        self.assertFalse(result["all_natural_identity_relations_verified"])
        self.assertFalse(result["account_entries_activated"])
        self.assertFalse(result["permissions_granted_or_elevated"])
        self.assertFalse(result["founder_ratification_authorized"])
        self.assertNotIn("account:founder-required", str(result))
        self.assertNotIn("domain:xiaoj-development", str(result))

    def test_multi_account_merge_holds_if_original_account_is_not_reverified(self):
        result = plan_account_binding(
            sovereign_ai_packet_ref="packet:founder",
            natural_identity_ref="natural-person:founder",
            permission_coordination_policy_ref="policy:deny-first",
            account_bindings=[
                {
                    "binding_state": "existing",
                    "account_type": "google_email_after_consent",
                    "account_login_sha256": module.REQUIRED_FOUNDER_ACCOUNT_LOGIN_SHA256,
                    "account_ref": "account:existing",
                    "account_login_verification_evidence_ref": "login-proof:existing",
                    "natural_identity_relation_evidence_ref": "relation-proof:existing",
                    "account_binding_evidence_ref": "binding-proof:existing",
                    "external_account_consent_evidence_ref": "consent:existing",
                    "domain_permission_refs": ["domain:founder"],
                },
                {
                    "binding_state": "new",
                    "account_type": "linux_user",
                    "account_login_sha256": "b" * 64,
                    "account_ref": "account:new",
                    "account_login_verification_evidence_ref": "login-proof:new",
                    "natural_identity_relation_evidence_ref": "relation-proof:new",
                    "account_binding_evidence_ref": "binding-proof:new",
                    "domain_permission_refs": ["domain:local"],
                },
            ],
        )
        self.assertEqual(
            result["state"],
            "HOLD_MULTI_ACCOUNT_LOGIN_OR_RELATION_EVIDENCE_REQUIRED",
        )
        self.assertTrue(any(
            "existing_binding_reverification_evidence_ref" in item
            for item in result["missing_prerequisites"]
        ))
        self.assertFalse(result["packet_mutated"])

    def test_multi_account_governance_gap_candidate_keeps_unratified_rules_on_hold(self):
        candidate = build_account_governance_candidate()
        self.assertEqual(candidate["state"], "HOLD_GOVERNANCE_RULE_GAPS")
        gap_ids = {item["id"] for item in candidate["red_team_gaps"]}
        self.assertIn("G001_MERGE_TRANSACTION_AND_QUORUM_UNDEFINED", gap_ids)
        self.assertIn("G009_FOUNDER_ACCOUNT_BINDING_AND_RATIFICATION_NOT_SEPARATELY_RECEIPTED", gap_ids)
        self.assertGreaterEqual(len(candidate["purple_team_completion_rules"]), 7)
        self.assertIn(
            "RECOVERY_WHEN_AN_EXISTING_ACCOUNT_IS_UNAVAILABLE",
            candidate["unresolved_governance_decisions"],
        )
        self.assertFalse(candidate["rules_promoted_or_activated"])
        self.assertFalse(candidate["runtime_effect"])

    def test_projection_candidate_never_mutates_core_or_applies_mode(self):
        for kind in (
            "merchant",
            "committee",
            "nonprofit_association",
            "other",
            "association",
            "founder",
        ):
            kwargs = {
                "projection_kind": kind,
                "total_field_ref": f"total-field:{kind}",
                "mode_ref": f"mode:{kind}",
                "appearance_profile_ref": f"appearance:{kind}",
            }
            if kind in {"merchant", "committee", "nonprofit_association", "other"}:
                kwargs.update({
                    "odoo_relationship_ref": f"odoo-relation:{kind}",
                    "group_member_application_ref": f"application:{kind}",
                    "personal_identity_packet_ref": f"identity-packet:{kind}",
                    "identity_packet_active_evidence_ref": f"active-evidence:{kind}",
                    "association_group_member_approval_evidence_ref": f"association-approval:{kind}",
                    "founder_account_packet_binding_evidence_ref": f"founder-account-binding:{kind}",
                    "founder_establishment_approval_evidence_ref": f"founder-approval:{kind}",
                })
                if kind == "other":
                    kwargs["founder_personal_visit_design_evidence_ref"] = f"visit-design:{kind}"
                else:
                    kwargs["intent_field_questionnaire_ref"] = f"questionnaire:{kind}"
                    kwargs["questionnaire_real_world_usability_evidence_ref"] = (
                        f"questionnaire-evidence:{kind}"
                    )
            result = plan_field_projection(**kwargs)
            self.assertEqual(result["state"], "CANDIDATE_FIELD_PROJECTION")
            self.assertFalse(result["core_identity_mutated"])
            self.assertFalse(result["mode_applied"])
            self.assertFalse(result["projection_activated"])
            self.assertFalse(result["projection_established"])
            self.assertFalse(result["association_identity_approval_verified"])
            self.assertNotIn(f"total-field:{kind}", str(result))
            if kind in {"merchant", "committee", "nonprofit_association", "other"}:
                self.assertNotIn(f"odoo-relation:{kind}", str(result))
                self.assertNotIn(f"identity-packet:{kind}", str(result))

    def test_real_world_questionnaire_is_required_for_three_predefined_types(self):
        for field_type in ("merchant", "committee", "nonprofit_association"):
            result = build_questionnaire(field_type=field_type)
            self.assertEqual(result["state"], "CANDIDATE_REAL_WORLD_USABLE_QUESTIONNAIRE")
            self.assertTrue(result["questionnaire_required"])
            self.assertGreaterEqual(len(result["sections"]), 10)
            self.assertTrue(all(section.get("prompt") for section in result["sections"]))
            self.assertFalse(result["member_plaintext_allowed"])
            self.assertFalse(result["secret_value_allowed"])
            self.assertFalse(result["real_world_usability_verified"])

    def test_other_type_skips_template_questionnaire_but_requires_personal_visit_design(self):
        questionnaire = build_questionnaire(field_type="other")
        self.assertEqual(questionnaire["state"], "NOT_REQUIRED_FOR_OTHER_TYPE")
        self.assertFalse(questionnaire["questionnaire_required"])
        policy = build_core_contract()["group_member_total_field_establishment"][
            "other_type_exception"
        ]
        self.assertTrue(policy["founder_personal_visit_design_required"])
        self.assertFalse(policy["generic_template_substitution_allowed"])
        application = plan_group_member_application(
            projection_kind="other",
            group_member_ref="group-member:other-1",
            personal_identity_packet_ref="identity-packet:other-1",
            identity_packet_active_evidence_ref="active-evidence:other-1",
            account_entry_binding_ref="account-entry:other-1",
            account_domain_permission_ref="domain-permission:application",
            association_group_member_approval_evidence_ref="association-approval:other-1",
            odoo_relationship_ref="odoo-relation:other-1",
            requested_total_field_ref="total-field:other-1",
        )
        self.assertEqual(
            application["state"],
            "CANDIDATE_PENDING_FOUNDER_RATIFICATION_AND_PERSONAL_VISIT_DESIGN",
        )
        self.assertTrue(application["founder_personal_visit_design_required"])
        self.assertFalse(application["total_field_established"])

    def test_personal_identity_packet_exposes_credential_free_xiaoj_addon_link(self):
        result = build_application_entry(
            personal_identity_packet_ref="identity-packet:personal-1",
            account_entry_binding_ref="account-entry:personal-1",
            account_domain_permission_ref="domain-permission:application",
        )
        self.assertEqual(result["state"], "CANDIDATE_VISIBLE_APPLICATION_LINK")
        self.assertTrue(result["link_visible"])
        self.assertEqual(result["addon"]["capability_class"], "XIAOJ_ADDON")
        self.assertFalse(result["addon"]["link_contains_credential_or_packet_ref"])
        self.assertFalse(result["account_login_verified"])
        self.assertFalse(result["account_domain_permission_verified"])
        self.assertFalse(result["application_submitted"])
        self.assertFalse(result["total_field_established"])
        self.assertNotIn("identity-packet:personal-1", str(result))

    def test_product_candidate_is_human_readable_and_has_no_effect(self):
        product = build_product_candidate()
        self.assertEqual(product["state"], "CANDIDATE_PRODUCT_LANDING_NO_EFFECT")
        self.assertEqual(
            {item["code"] for item in product["type_options"]},
            {"merchant", "committee", "nonprofit_association", "other"},
        )
        self.assertEqual(len(product["journey"]), 9)
        self.assertFalse(product["authority_separation"]["represents_technical_ownership"])
        self.assertFalse(product["effects"]["odoo_write"])
        self.assertFalse(product["effects"]["application_persisted"])
        self.assertFalse(product["effects"]["total_field_established"])
        self.assertFalse(product["effects"]["account_entry_activated"])
        self.assertFalse(product["effects"]["domain_permission_granted_or_coordinated"])
        self.assertFalse(product["effects"]["founder_control_exposed_or_executed"])
        self.assertIn("FOUNDER_RATIFICATION_RECEIPT_UNBOUND", product["landing_gaps"])
        self.assertIn(
            "MULTI_ACCOUNT_LOGIN_AND_NATURAL_IDENTITY_RELATION_VERIFIERS_UNBOUND",
            product["landing_gaps"],
        )

    def test_product_landing_and_application_routes_require_authenticated_user(self):
        with open(CONTROLLER_PATH, encoding="utf-8") as handle:
            controller = handle.read()
        self.assertIn(
            '@http.route("/wuchang/xiaoj/group-member-field-application", type="http", auth="user")',
            controller,
        )
        self.assertIn(
            '@http.route("/wuchang/xiaoj/api/group-member-field-application-candidate", type="json", auth="user"',
            controller,
        )
        self.assertIn(
            '@http.route("/wuchang/xiaoj/api/sovereign-ai-account-binding-candidate", type="json", auth="user"',
            controller,
        )
        self.assertIn(
            '@http.route("/wuchang/xiaoj/api/sovereign-ai-account-governance-candidate", type="json", auth="user"',
            controller,
        )
        self.assertNotIn(
            '@http.route("/wuchang/xiaoj/group-member-field-application", type="http", auth="public")',
            controller,
        )

    def test_product_ui_uses_market_workspaces_and_keeps_founder_controls_out(self):
        with open(CONTROLLER_PATH, encoding="utf-8") as handle:
            controller = handle.read()
        for label in (
            "生活輔助",
            "工作協作",
            "個人娛樂",
            "帳號綁定",
            "管委會大樓",
            "商家會員",
            "管理職位",
        ):
            self.assertIn(label, controller)
        self.assertIn('data-space="personal"', controller)
        self.assertIn('data-space="field"', controller)
        self.assertIn('data-space="management"', controller)
        self.assertIn("verified_field_management_role_binding_required", str(
            build_core_contract()["xiaoj_function_category_separation"]
        ))
        self.assertNotIn('data-function="sovereign_packet_governance"', controller)
        self.assertNotIn('data-function="distributed_device_and_compute"', controller)

    def test_group_member_application_waits_for_founder_ratification(self):
        result = plan_group_member_application(
            projection_kind="merchant",
            group_member_ref="group-member:merchant-1",
            personal_identity_packet_ref="identity-packet:personal-1",
            identity_packet_active_evidence_ref="active-evidence:packet-1",
            account_entry_binding_ref="account-entry:merchant-1",
            account_domain_permission_ref="domain-permission:application",
            association_group_member_approval_evidence_ref="association-approval:merchant-1",
            odoo_relationship_ref="odoo-relation:merchant-1",
            requested_total_field_ref="total-field:merchant-1",
            intent_field_questionnaire_ref="questionnaire:merchant-1",
            questionnaire_real_world_usability_evidence_ref="questionnaire-evidence:merchant-1",
        )
        self.assertEqual(result["state"], "CANDIDATE_PENDING_FOUNDER_RATIFICATION")
        self.assertFalse(result["founder_ratification_verified"])
        self.assertFalse(result["application_submitted"])
        self.assertFalse(result["total_field_established"])
        self.assertFalse(result["projection_activated"])
        self.assertNotIn("group-member:merchant-1", str(result))

    def test_predefined_group_member_type_holds_without_questionnaire_evidence(self):
        result = plan_group_member_application(
            projection_kind="committee",
            group_member_ref="group-member:committee-1",
            personal_identity_packet_ref="identity-packet:committee-1",
            identity_packet_active_evidence_ref="active-evidence:committee-1",
            association_group_member_approval_evidence_ref="association-approval:committee-1",
            odoo_relationship_ref="odoo-relation:committee-1",
            requested_total_field_ref="total-field:committee-1",
        )
        self.assertEqual(result["state"], "HOLD_GROUP_MEMBER_APPLICATION_PREREQUISITES")
        self.assertIn("intent_field_questionnaire_ref", result["missing_prerequisites"])
        self.assertIn(
            "questionnaire_real_world_usability_evidence_ref",
            result["missing_prerequisites"],
        )
        self.assertFalse(result["total_field_established"])

    def test_other_field_projection_holds_without_founder_visit_design_evidence(self):
        result = plan_field_projection(
            projection_kind="other",
            total_field_ref="total-field:other-1",
            mode_ref="mode:other-1",
            odoo_relationship_ref="odoo-relation:other-1",
            group_member_application_ref="application:other-1",
            personal_identity_packet_ref="identity-packet:other-1",
            identity_packet_active_evidence_ref="active-evidence:other-1",
            association_group_member_approval_evidence_ref="association-approval:other-1",
            founder_account_packet_binding_evidence_ref="founder-account-binding:other-1",
            founder_establishment_approval_evidence_ref="founder-approval:other-1",
        )
        self.assertEqual(result["state"], "HOLD_FIELD_PROJECTION_BINDING_REQUIRED")
        self.assertIn(
            "founder_personal_visit_design_evidence_ref",
            result["missing_bindings"],
        )
        self.assertFalse(result["projection_established"])

    def test_group_member_projection_holds_without_founder_account_packet_binding(self):
        result = plan_field_projection(
            projection_kind="merchant",
            total_field_ref="total-field:merchant-1",
            mode_ref="mode:merchant-1",
            odoo_relationship_ref="odoo-relation:merchant-1",
            group_member_application_ref="application:merchant-1",
            personal_identity_packet_ref="identity-packet:merchant-1",
            identity_packet_active_evidence_ref="active-evidence:merchant-1",
            association_group_member_approval_evidence_ref="association-approval:merchant-1",
            founder_establishment_approval_evidence_ref="founder-approval:merchant-1",
            intent_field_questionnaire_ref="questionnaire:merchant-1",
            questionnaire_real_world_usability_evidence_ref="questionnaire-evidence:merchant-1",
        )
        self.assertEqual(result["state"], "HOLD_FIELD_PROJECTION_BINDING_REQUIRED")
        self.assertIn(
            "founder_account_packet_binding_evidence_ref",
            result["missing_bindings"],
        )
        self.assertFalse(result["founder_account_packet_binding_verified"])
        self.assertFalse(result["founder_establishment_approval_verified"])

    def test_non_group_member_projection_cannot_use_group_member_application_addon(self):
        result = plan_group_member_application(
            projection_kind="founder",
            group_member_ref="group-member:founder",
            personal_identity_packet_ref="identity-packet:founder",
            identity_packet_active_evidence_ref="active-evidence:founder",
            association_group_member_approval_evidence_ref="association-approval:founder",
            odoo_relationship_ref="odoo-relation:founder",
            requested_total_field_ref="total-field:founder",
        )
        self.assertEqual(result["state"], "HOLD_NOT_GROUP_MEMBER_TOTAL_FIELD_PROJECTION")
        self.assertFalse(result["total_field_established"])

    def test_distributed_device_admission_requires_founder_and_association_evidence(self):
        result = plan_device_admission(
            device_ref="device:node-1",
            device_capability_manifest_ref="manifest:node-1",
            total_field_ref="total-field:system",
            founder_approval_evidence_ref="approval:founder-1",
            association_approved_identity_packet_ref="identity-packet:node-1",
        )
        self.assertEqual(result["state"], "CANDIDATE_FOUNDER_ADMISSION_DECISION")
        self.assertFalse(result["founder_approval_verified"])
        self.assertFalse(result["association_identity_approval_verified"])
        self.assertFalse(result["device_established"])
        self.assertFalse(result["device_enrolled"])
        self.assertNotIn("device:node-1", str(result))

    def test_only_founder_base_device_can_form_template_application_candidate(self):
        common = {
            "founder_base_device_ref": "device:founder-base",
            "founder_base_device_authority_evidence_ref": "evidence:founder-base",
            "total_field_ref": "total-field:system",
            "mode_ref": "mode:projection",
            "template_ref": "template:governed",
            "target_projection_ref": "projection:merchant-1",
            "target_identity_packet_ref": "identity-packet:merchant-1",
            "target_field_type": "merchant",
            "template_origin": "governed_system_template",
        }
        remote = plan_template_application(
            requesting_device_ref="device:remote-node",
            **common,
        )
        self.assertEqual(remote["state"], "HOLD_TEMPLATE_APPLICATION_DEVICE_BOUNDARY")
        self.assertFalse(remote["template_applied"])
        local = plan_template_application(
            requesting_device_ref="device:founder-base",
            **common,
        )
        self.assertEqual(local["state"], "CANDIDATE_FOUNDER_BASE_TEMPLATE_APPLICATION")
        self.assertFalse(local["template_applied"])
        self.assertFalse(local["template_copied"])
        self.assertFalse(local["template_delegated"])

    def test_other_type_rejects_generic_template_application(self):
        common = {
            "requesting_device_ref": "device:founder-base",
            "founder_base_device_ref": "device:founder-base",
            "founder_base_device_authority_evidence_ref": "evidence:founder-base",
            "total_field_ref": "total-field:other-1",
            "mode_ref": "mode:other-1",
            "template_ref": "template:generic",
            "target_projection_ref": "projection:other-1",
            "target_identity_packet_ref": "identity-packet:other-1",
            "target_field_type": "other",
        }
        rejected = plan_template_application(
            template_origin="governed_system_template",
            founder_personal_visit_design_evidence_ref="visit-design:other-1",
            **common,
        )
        self.assertEqual(rejected["state"], "HOLD_OTHER_TYPE_GENERIC_TEMPLATE_PROHIBITED")
        accepted_candidate = plan_template_application(
            template_origin="founder_personal_visit_design",
            founder_personal_visit_design_evidence_ref="visit-design:other-1",
            **common,
        )
        self.assertEqual(
            accepted_candidate["state"],
            "CANDIDATE_FOUNDER_BASE_TEMPLATE_APPLICATION",
        )
        self.assertFalse(accepted_candidate["template_applied"])

    def test_founder_ratification_is_final_gate_not_sufficient_by_itself(self):
        policy = build_core_contract()["group_member_total_field_establishment"]
        self.assertTrue(policy["founder_ratification_is_final_gate"])
        self.assertFalse(policy["founder_ratification_alone_is_sufficient"])
        self.assertEqual(policy["establishment_condition"], "ALL_REQUIRED_GATES_VERIFIED")

    def test_local_trade_secret_request_requires_verified_total_field_decision(self):
        result = plan_secret_request(
            approved_device_ref="device:approved-1",
            device_approval_evidence_ref="evidence:device-1",
            total_field_ref="total-field:local",
            request_policy_ref="policy:local-secret-v1",
            purpose_scope_ref="purpose:bounded",
            time_window_ref="window:short",
            secret_scope_ref="secret-scope:opaque",
        )
        self.assertEqual(result["state"], "CANDIDATE_AUTOMATIC_TOTAL_FIELD_DECISION")
        self.assertTrue(result["automatic_approval_eligible_candidate"])
        self.assertFalse(result["automatic_approval_decision"])
        self.assertFalse(result["secret_released"])
        self.assertFalse(result["external_drive_read"])
        self.assertFalse(result["odoo_write"])
        self.assertNotIn("secret-scope:opaque", str(result))

    def test_incomplete_secret_request_holds(self):
        result = plan_secret_request(approved_device_ref="device:approved-1")
        self.assertEqual(result["state"], "HOLD_AUTOMATIC_APPROVAL_PREREQUISITES")
        self.assertFalse(result["automatic_approval_eligible_candidate"])
        self.assertIn("device_approval_evidence_ref", result["missing_prerequisites"])

    def test_catalog_is_deterministic(self):
        self.assertEqual(build_catalog(), build_catalog())
        self.assertEqual(len(build_catalog()["catalog_sha256"]), 64)

    def test_natural_language_can_select_capability(self):
        self.assertEqual(detect_capability("請查今天營業額與訂單數"), "operations.summary")
        self.assertEqual(detect_capability("我要建立促銷活動候選"), "marketing.promotions")
        self.assertEqual(detect_capability("客人想看菜單"), "catalog.menu")

    def test_menu_lookup_produces_read_only_plan(self):
        result = plan_action(
            text="客人想看菜單",
            actor_ref="service_agent_ref:xiaoj",
            actor_role="service_agent",
            total_field_ref="total_field_ref:merchant-a",
            mode_ref="mode_ref:cafe-service",
            appearance_profile_ref="appearance_ref:cafe-audiovisual",
            parameters={"store_ref": "store_ref:liaoguo", "limit": 20},
        )
        self.assertEqual(result["state"], "READY_READ_ONLY_PLAN")
        self.assertEqual(result["capability_code"], "catalog.menu")
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["safety_flags"]["ODOO_DB_WRITE"])
        self.assertNotIn("service_agent_ref:xiaoj", str(result))
        self.assertNotIn("mode_ref:cafe-service", str(result))
        projection = result["xiaoj_audiovisual_projection"]
        self.assertFalse(projection["mode_binding_verified"])
        self.assertFalse(projection["mode_applied"])
        self.assertFalse(projection["service_agent_can_apply_mode"])

    def test_high_risk_function_never_executes(self):
        result = plan_action(
            capability_code="marketing.promotions",
            actor_ref="service_agent_ref:xiaoj",
            actor_role="service_agent",
            parameters={"store_ref": "store_ref:liaoguo", "change_set_ref": "change_ref:promo-1"},
        )
        self.assertEqual(result["state"], "HOLD_RUNTIME_BINDING_REQUIRED")
        self.assertTrue(result["requires_human_release"])
        self.assertFalse(result["safety_flags"]["PROMOTION_ACTIVATED"])

    def test_protected_and_unknown_parameters_fail_closed(self):
        result = plan_action(
            capability_code="operations.orders",
            parameters={"customer_phone": "redacted", "unexpected": "value"},
        )
        self.assertEqual(result["state"], "HOLD_PARAMETER_BOUNDARY")
        self.assertIn("PROTECTED_PARAMETER_REJECTED", result["conflicts"])
        self.assertIn("UNSUPPORTED_PARAMETER_REJECTED", result["conflicts"])
        self.assertEqual(result["accepted_parameters"], {})

    def test_unknown_capability_holds(self):
        result = plan_action(capability_code="merchant.magic")
        self.assertEqual(result["state"], "HOLD_UNKNOWN_CAPABILITY")
        self.assertFalse(result["execution_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
