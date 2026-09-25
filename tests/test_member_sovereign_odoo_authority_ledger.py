import ast
import csv
import io
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / (
    "Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py"
)
LEGACY_PATH = REPO_ROOT / (
    "Taiji_Odoo/addons/wuchang_core/models/member_registration.py"
)
ACL_PATH = REPO_ROOT / (
    "Taiji_Odoo/addons/wuchang_member_registration/security/ir.model.access.csv"
)
GROUPS_PATH = REPO_ROOT / (
    "Taiji_Odoo/addons/wuchang_member_registration/security/"
    "wuchang_member_groups.xml"
)

MODEL_SOURCE = MODEL_PATH.read_text(encoding="utf-8")
LEGACY_SOURCE = LEGACY_PATH.read_text(encoding="utf-8")
MODEL_TREE = ast.parse(MODEL_SOURCE, filename=str(MODEL_PATH))
LEGACY_TREE = ast.parse(LEGACY_SOURCE, filename=str(LEGACY_PATH))

AUTHORITY_MODEL = {
    "member_consent_authority": "member",
    "safety_and_landing_authority": "total_field_verifier",
    "process_authority": "odoo",
    "candidate_authority": "none",
}
LEDGER_CLASSES = {
    "WuchangMemberConsentLedger",
    "WuchangMemberSovereignRootLedger",
    "WuchangMemberSovereignRevocationLedger",
    "WuchangMemberSovereignRecoveryLedger",
    "WuchangMemberSovereignInvalidationCandidate",
}


def _class_node(name):
    return next(
        node
        for node in MODEL_TREE.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


def _source(node, source=MODEL_SOURCE):
    return ast.get_source_segment(source, node)


def _assigned_literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                if (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "frozenset"
                ):
                    return frozenset(ast.literal_eval(node.value.args[0]))
                return ast.literal_eval(node.value)
    raise AssertionError(f"assignment not found: {name}")


def _model_names(tree):
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "_name"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, ast.Constant):
            names.append(node.value.value)
    return names


def _recovery_hold_function():
    function = next(
        node
        for node in MODEL_TREE.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "recovery_transition_hold_code"
    )
    namespace = {}
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(MODEL_PATH), "exec"), namespace)
    return namespace["recovery_transition_hold_code"]


def _acl_rows():
    return {
        row["id"]: row
        for row in csv.DictReader(io.StringIO(ACL_PATH.read_text(encoding="utf-8")))
    }


def _xml_records():
    root = ElementTree.parse(GROUPS_PATH).getroot()
    return {
        record.attrib["id"]: record
        for record in root.findall("record")
    }


def _field(record, name):
    return next(
        field for field in record.findall("field") if field.attrib["name"] == name
    )


def test_persistent_registration_is_the_only_authoritative_model():
    declarations = _model_names(MODEL_TREE) + _model_names(LEGACY_TREE)
    assert declarations.count("wuchang.member.registration") == 1
    registration = _class_node("WuchangMemberRegistration")
    assert ast.unparse(registration.bases[0]) == "models.Model"


def test_legacy_transient_conflict_is_retired_without_a_parallel_model():
    assert "models.TransientModel" not in LEGACY_SOURCE
    assert "wuchang.member.registration" not in _model_names(LEGACY_TREE)
    assert "RETIRED_NOT_REGISTERED" in LEGACY_SOURCE


def test_fixed_authority_model_is_exact_and_candidate_has_no_authority():
    assert _assigned_literal(MODEL_TREE, "SOVEREIGN_AUTHORITY_MODEL") == AUTHORITY_MODEL
    for class_name in LEDGER_CLASSES:
        class_source = _source(_class_node(class_name))
        for field_name, value in AUTHORITY_MODEL.items():
            assert field_name in class_source
            assert f'default="{value}"' in class_source


def test_p0_action_basis_is_hash_bound_without_changing_the_p0_contract():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    required = {
        "action_hash",
        "purpose_ref",
        "scope_refs",
        "effect_class",
        "amount_currency_hash",
        "identity_root_ref",
        "root_packet_ref",
        "root_generation",
        "revocation_epoch",
        "member_proof_ref",
        "p1_evidence_ref",
    }
    assert required <= set(registration_source.split('"'))
    assert "_normalize_scope_refs(scope_refs)" in registration_source
    assert "sorted(set(scope_refs))" in MODEL_SOURCE


def test_consent_scope_serialization_rejects_noncanonical_order_or_duplicates():
    consent_source = _source(_class_node("WuchangMemberConsentLedger"))
    assert "HOLD_SCOPE_REFS_NOT_CANONICAL" in consent_source
    assert "_normalize_scope_refs(scope_refs) != scope_refs" in consent_source


def test_one_root_generation_and_lineage_are_cas_guarded():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    root_source = _source(_class_node("WuchangMemberSovereignRootLedger"))
    assert "HOLD_DOUBLE_ACTIVE_ROOT" in registration_source
    assert "unique(registration_id, root_generation)" in root_source
    assert "registration.sovereign_root_generation + 1" in root_source
    assert "HOLD_ROOT_LINEAGE_MISMATCH" in root_source


def test_registration_authority_head_is_not_ordinary_writable():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    assert "SOVEREIGN_HEAD_FIELDS & set(vals)" in registration_source
    assert "Sovereign authority head fields are CAS-managed." in registration_source


def test_cas_sql_binds_generation_epoch_state_and_rowcount():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    assert "COALESCE(sovereign_root_generation, 0) = %s" in registration_source
    assert "COALESCE(sovereign_revocation_epoch, 0) = %s" in registration_source
    assert "sovereign_root_state = %s" in registration_source
    assert "self.env.cr.rowcount != 1" in registration_source
    assert "HOLD_RECOVERY_STALE_CAS" in registration_source


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "current_generation": 4,
                "current_epoch": 9,
                "expected_generation": 3,
                "expected_epoch": 9,
            },
            "HOLD_RECOVERY_STALE_CAS",
        ),
        (
            {
                "current_generation": 4,
                "current_epoch": 9,
                "expected_generation": 4,
                "expected_epoch": 8,
            },
            "HOLD_RECOVERY_STALE_CAS",
        ),
        (
            {
                "current_generation": 4,
                "current_epoch": 9,
                "expected_generation": 4,
                "expected_epoch": 9,
                "completion_seen": True,
            },
            "HOLD_RECOVERY_ALREADY_COMPLETED",
        ),
        (
            {
                "current_generation": 4,
                "current_epoch": 9,
                "expected_generation": 4,
                "expected_epoch": 9,
                "cooldown_active": True,
            },
            "HOLD_RECOVERY_COOLDOWN_ACTIVE",
        ),
    ],
)
def test_recovery_negative_transition_codes(kwargs, expected):
    assert _recovery_hold_function()(**kwargs) == expected


def test_recovery_matching_cas_without_other_holds_can_continue():
    assert _recovery_hold_function()(7, 11, 7, 11) is None


def test_recovery_is_append_only_cas_bound_single_completion_with_cooldown():
    recovery_source = _source(_class_node("WuchangMemberSovereignRecoveryLedger"))
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    assert "unique(completion_guard_key)" in recovery_source
    assert "unique(recovery_cas_ref, event_type)" in recovery_source
    assert "HOLD_RECOVERY_COMPLETION_GUARD_MISMATCH" in recovery_source
    assert "HOLD_RECOVERY_COOLDOWN_ACTIVE" in registration_source
    assert "expected_generation" in recovery_source
    assert "expected_epoch" in recovery_source


def test_revocation_epoch_is_strictly_monotonic():
    source = _source(_class_node("WuchangMemberSovereignRevocationLedger"))
    assert "previous_revocation_epoch\", -1) + 1" in source
    assert "registration.sovereign_revocation_epoch" in source
    assert "unique(registration_id, new_revocation_epoch)" in source
    assert "HOLD_REVOCATION_EPOCH_STALE" in source


@pytest.mark.parametrize("class_name", sorted(LEDGER_CLASSES))
def test_authority_ledgers_reject_overwrite_and_delete(class_name):
    source = _source(_class_node(class_name))
    assert "HOLD_APPEND_ONLY_LEDGER_OVERWRITE" in source
    assert "HOLD_APPEND_ONLY_LEDGER_DELETE" in source


def test_cross_member_forged_consent_and_sudo_bypass_are_holds():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    consent_source = _source(_class_node("WuchangMemberConsentLedger"))
    assert "HOLD_CROSS_MEMBER_AUTHORITY" in registration_source
    assert "HOLD_SUDO_MEMBER_AUTHORITY_BYPASS" in registration_source
    assert "self.env.su" in consent_source
    assert "HOLD_FORGED_MEMBER_CONSENT" in consent_source
    assert "registration.create_uid != self.env.user" in consent_source


def test_provider_can_supply_only_hashed_identity_and_verified_binding_evidence():
    external_source = _source(_class_node("WuchangMemberExternalAuth"))
    assert "provider_subject_hash" in external_source
    assert "verified_channel_binding_ref" in external_source
    assert "HOLD_VERIFIED_CHANNEL_NOT_EVIDENCED" in external_source
    assert "HOLD_PROVIDER_AUTHORITY_ESCALATION" in external_source
    assert '"consent_ref",' not in external_source.split("def write", 1)[1].split(
        "def hash_subject", 1
    )[0]
    forbidden = _assigned_literal(MODEL_TREE, "PROVIDER_FORBIDDEN_AUTHORITY_FIELDS")
    assert {
        "identity_root_ref",
        "root_packet_ref",
        "root_generation",
        "revocation_epoch",
        "role_ref",
        "seat_ref",
        "action_hash",
        "member_consent",
        "consent_ref",
    } <= forbidden


def test_rotation_creates_four_kinds_of_invalidation_candidates_only():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    for target_type in ("ROOT", "SESSION", "SCENE", "CONSENT_LEASE"):
        assert f'("{target_type}", value)' in registration_source or (
            target_type == "ROOT"
            and 'targets = [("ROOT", self.sovereign_root_packet_ref)]'
            in registration_source
        )
    assert '"runtime_propagated": False' in registration_source
    invalidation_source = _source(
        _class_node("WuchangMemberSovereignInvalidationCandidate")
    )
    assert "HOLD_RUNTIME_PROPAGATION_FORBIDDEN" in invalidation_source


def test_no_authority_ledger_accepts_raw_private_or_member_plaintext_keys():
    forbidden = _assigned_literal(MODEL_TREE, "FORBIDDEN_LEDGER_VALUE_KEYS")
    assert {
        "raw_provider_profile",
        "raw_provider_subject",
        "raw_key",
        "private_key",
        "access_token",
        "refresh_token",
        "token",
        "password",
        "secret",
        "member_name",
        "email",
        "phone",
        "address",
    } <= forbidden
    for class_name in LEDGER_CLASSES:
        assert "FORBIDDEN_LEDGER_VALUE_KEYS & set(vals)" in _source(
            _class_node(class_name)
        )


def test_acl_is_append_only_and_admin_has_no_ordinary_authority_write():
    rows = _acl_rows()
    append_only_acl_ids = {
        "access_wuchang_member_consent_ledger_manager",
        "access_wuchang_member_consent_ledger_admin",
        "access_wuchang_member_consent_ledger_subject",
        "access_wuchang_member_sovereign_root_ledger_subject",
        "access_wuchang_member_sovereign_revocation_ledger_subject",
        "access_wuchang_member_sovereign_recovery_ledger_subject",
        "access_wuchang_member_sovereign_invalidation_candidate_subject",
    }
    for acl_id in append_only_acl_ids:
        assert rows[acl_id]["perm_write"] == "0"
        assert rows[acl_id]["perm_unlink"] == "0"
    assert rows["access_wuchang_member_consent_ledger_admin"]["perm_create"] == "1"
    assert rows["access_wuchang_member_recovery_case_admin"]["perm_write"] == "0"
    assert rows["access_wuchang_member_recovery_case_admin"]["perm_create"] == "0"


def test_member_subject_record_rules_are_owner_scoped_and_nonwritable():
    records = _xml_records()
    assert "group_wuchang_member_subject" in records
    rule_ids = {
        "rule_wuchang_member_registration_subject_own",
        "rule_wuchang_member_external_auth_subject_own",
        "rule_wuchang_member_consent_ledger_subject_own",
        "rule_wuchang_member_sovereign_root_ledger_subject_own",
        "rule_wuchang_member_sovereign_revocation_ledger_subject_own",
        "rule_wuchang_member_sovereign_recovery_ledger_subject_own",
        "rule_wuchang_member_sovereign_invalidation_candidate_subject_own",
    }
    for rule_id in rule_ids:
        record = records[rule_id]
        domain = (_field(record, "domain_force").text or "").strip()
        assert domain in {
            "[('create_uid', '=', user.id)]",
            "[('member_user_id', '=', user.id)]",
        }
        assert _field(record, "perm_write").attrib["eval"] == "False"
        assert _field(record, "perm_unlink").attrib["eval"] == "False"


def test_source_candidate_never_claims_runtime_release_or_execution_authority():
    registration_source = _source(_class_node("WuchangMemberRegistration"))
    assert '"runtime_propagated": True' not in registration_source
    assert '"candidate_only": True' in registration_source
    assert '"candidate_authority": "none"' in MODEL_SOURCE
    assert '"ALLOW"' not in registration_source
