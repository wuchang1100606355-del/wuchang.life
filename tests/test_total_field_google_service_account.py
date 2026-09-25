import ast
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "adapters/total_field_google_service_account.py"
SCHEMA_PATH = ROOT / "schemas/w7tp_total_field_service_account_binding.schema.json"

spec = importlib.util.spec_from_file_location("total_field_google_service_account", MODULE_PATH)
adapter = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(adapter)


def valid_binding():
    return {
        "binding_id": "binding:total-field:vertex-candidate-v1",
        "schema_version": "W7TP-TOTAL-FIELD-SERVICE-ACCOUNT-BINDING/1.0",
        "channel": "TOTAL_FIELD",
        "connector": "VERTEX_AI_GEMINI_CANDIDATE",
        "runtime_identity": "DEDICATED_SERVICE_ACCOUNT",
        "auth_mode": "ADC_IMPERSONATION",
        "principal_ref": "service-account-ref:total-field-runtime",
        "impersonation_target_ref": "service-account-ref:vertex-candidate",
        "service_account_key_file_policy": "PREFER_NONE",
        "super_admin_role": "BOOTSTRAP_AND_APPROVAL_ONLY",
        "authority_boundary": {
            "cloud_connector_identity_only": True,
            "governance_authority": False,
            "xiaoj_identity": False,
            "owner_intent": False,
            "member_identity": False,
            "final_decision": False,
        },
        "candidate_return_boundary": {
            "execution_authority": False,
            "verification_required": True,
        },
    }


def test_service_account_schema_and_binding_are_valid():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert adapter.validate_service_account_binding(valid_binding())["state"] == "PASS"


def test_raw_credential_fields_are_rejected():
    binding = valid_binding()
    binding["private_key"] = "forbidden-placeholder"
    result = adapter.validate_service_account_binding(binding)
    assert result["state"] == "HOLD"
    assert any("FORBIDDEN_CREDENTIAL_FIELD" in error for error in result["errors"])


def test_mock_configuration_passes_without_claiming_adc_or_live_probe():
    result = adapter.assess_adc_readiness(valid_binding())
    assert result == {
        "state": "PASS_MOCK_CONFIGURATION",
        "adc_check": "NOT_RUN",
        "live_probe": "NOT_RUN",
        "errors": [],
    }


def test_live_probe_holds_when_credentials_are_not_provisioned():
    result = adapter.assess_adc_readiness(valid_binding(), live_probe=True)
    assert result["state"] == "HOLD_CREDENTIAL_NOT_PROVISIONED"
    assert result["adc_check"] == "HOLD_CREDENTIAL_NOT_PROVISIONED"
    assert result["live_probe"] == "NOT_RUN"


def test_candidate_request_keeps_service_account_out_of_governance():
    packet = adapter.build_total_field_candidate_request(
        valid_binding(),
        run_id="RUN-SERVICE-ACCOUNT-0001",
        capability_ref="CAP_RESEARCH_CANDIDATE_V1",
        candidate_packet_ref="candidate:research:0001",
        evidence_refs=["evidence:research:0001"],
    )
    assert packet["channel"] == "TOTAL_FIELD"
    assert packet["execution_authority"] is False
    assert packet["verification_required"] is True
    assert packet["owner_xiaoj_identity_used"] is False
    assert packet["member_identity_used"] is False
    assert packet["seal_status"] == "NOT_SEALED"
    content = dict(packet)
    digest = content.pop("sha256")
    assert digest == adapter.deterministic_sha256(content)


def test_adapter_does_not_read_environment_or_connect_to_cloud():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert "getenv" not in source
    assert "os.environ" not in source
    assert not ({"google", "requests", "subprocess", "socket"} & imported_modules)
