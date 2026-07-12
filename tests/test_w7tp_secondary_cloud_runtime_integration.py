import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime_adapters/w7tp_secondary_cloud_runtime.py"
GATEWAY_PATH = ROOT / "runtime_adapters/taiji01_metric_identity_gateway.py"
SCHEMA_PATH = ROOT / "schemas/w7tp_secondary_cloud_runtime_request.schema.json"
PACKET_TEST_PATH = ROOT / "tests/test_w7tp_secondary_cloud_packet_ramp.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


runtime = load_module("w7tp_secondary_cloud_runtime", MODULE_PATH)
packets = load_module("w7tp_secondary_cloud_packet_fixtures", PACKET_TEST_PATH)


def runtime_request(channel="OWNER_XIAOJ", authorized=True):
    return {
        "run_id": "RUN-RUNTIME-INTEGRATION-0001",
        "channel": channel,
        "owner_explicit_authorization": authorized,
        "capability_id": "CAP_ASSOCIATION_SERVICE_V1",
        "capability_ref": "CAP_ASSOCIATION_SERVICE_V1",
        "packet_type": "PROFESSIONAL_RULE_PACKET",
        "domain_code": "ASSOCIATION",
        "language_code": "zh-TW",
        "compatibility_profile": "W7TP-8D-PACKET-NATIVE/1.0",
        "request_nonce": "runtime-pull-nonce-0001",
        "member_entry_packet": packets.member_entry(),
        "identity_authority_packet": packets.identity_authority(),
        "scenario_translation_packet": packets.scenario_translation(),
        "active_question_refs": [],
    }


class MemoryConnector:
    def __init__(self, packet=None):
        self.packet = packet or packets.capability_packet()
        self.requests = []

    def readiness(self):
        return {
            "state": "PASS",
            "adc_check": "INJECTED_TEST_BOUNDARY",
            "live_connection": False,
        }

    def pull_capability(self, request):
        self.requests.append(copy.deepcopy(dict(request)))
        return {"state": "PASS", "capability_packet": copy.deepcopy(self.packet)}


def test_runtime_schema_is_valid_draft_2020_12_and_json_parses():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    registry = json.loads(
        (ROOT / "runtime/total_field/secondary_cloud/capability_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["node_ref"] == "taiji01"


def test_owner_without_explicit_authorization_cannot_pull():
    connector = MemoryConnector()
    result = runtime.run_secondary_cloud_runtime(runtime_request(authorized=False), connector)
    assert result["state"] == "HOLD_OWNER_AUTHORIZATION_REQUIRED"
    assert result["auto_cloud_call"] == "FORBIDDEN"
    assert connector.requests == []


def test_non_object_json_root_holds_instead_of_raising():
    result = runtime.run_secondary_cloud_runtime([])
    assert result["state"] == "HOLD_REQUEST_REJECTED"
    assert result["seal_status"] == "NOT_SEALED"


def test_owner_authorization_builds_candidate_without_execution_authority():
    connector = MemoryConnector()
    result = runtime.run_secondary_cloud_runtime(runtime_request(), connector)
    assert result["candidate_request"] == connector.requests[0]
    assert result["execution_authority"] is False
    assert result["verification_required"] is True
    assert result["owner_identity_used"] is False


def test_total_field_candidate_is_isolated_and_cannot_start_xiaoj():
    connector = MemoryConnector()
    result = runtime.run_secondary_cloud_runtime(
        runtime_request(channel="TOTAL_FIELD", authorized=False), connector
    )
    assert result["state"] == "PASS"
    assert result["channel"] == "TOTAL_FIELD"
    assert result["xiaoj_started"] is False
    assert result["owner_identity_used"] is False
    assert result["member_identity_used"] is False


def test_connector_receives_only_the_nine_minimal_capability_fields():
    connector = MemoryConnector()
    runtime.run_secondary_cloud_runtime(runtime_request(), connector)
    assert set(connector.requests[0]) == runtime.ramp.MINIMAL_PULL_FIELDS
    assert len(connector.requests[0]) == 9
    assert runtime.ramp.validate_no_uplink_plaintext(
        connector.requests[0], require_minimal_pull=True
    )["state"] == "PASS"


@pytest.mark.parametrize("forbidden_key", ["member_plaintext", "private_key", "access_token"])
def test_member_plaintext_and_credentials_are_recursively_rejected(forbidden_key):
    request = runtime_request()
    request["scenario_translation_packet"]["nested"] = {forbidden_key: "not-returned"}
    connector = MemoryConnector()
    result = runtime.run_secondary_cloud_runtime(request, connector)
    assert result["state"] == "HOLD_REQUEST_REJECTED"
    assert any("FORBIDDEN_RUNTIME_FIELD" in error for error in result["errors"])
    assert connector.requests == []


def test_local_reconstruction_succeeds_on_taiji01():
    result = runtime.run_secondary_cloud_runtime(runtime_request(), MemoryConnector())
    assert result["reconstruction"]["reconstruction_location"] == "TAIJI01_LOCAL"
    assert result["reconstruction"]["local_verified"] is True
    assert result["reconstruction"]["comparison_result"] == "EQUIVALENT"


def test_l3_candidate_cannot_seal():
    result = runtime.run_secondary_cloud_runtime(
        runtime_request(), MemoryConnector(packets.capability_packet("L3_CANDIDATE"))
    )
    assert result["state"] == "HOLD"
    assert result["reconstruction"]["candidate_only"] is True
    assert result["seal_status"] == "NOT_SEALED"


def test_only_verified_result_without_active_question_can_seal():
    passing = runtime.run_secondary_cloud_runtime(runtime_request(), MemoryConnector())
    assert passing["verification"]["verification_result"] == "VERIFIED"
    assert passing["seal_status"] == "SEALED"

    request = runtime_request()
    request["active_question_refs"] = ["question:authority-gap-0001"]
    held = runtime.run_secondary_cloud_runtime(request, MemoryConnector())
    assert held["state"] == "HOLD"
    assert held["seal_status"] == "NOT_SEALED"


@pytest.mark.parametrize(
    ("mutator", "expected_layer"),
    [
        (lambda request: request["scenario_translation_packet"]["d8_envelope"].update(
            {"ttl_seconds": 0}
        ), "L8_ENVELOPE_SEAL"),
        (lambda request: request["scenario_translation_packet"]["d8_envelope"].update(
            {"nonce": "short"}
        ), "L8_ENVELOPE_SEAL"),
        (lambda request: request["scenario_translation_packet"]["d8_envelope"].update(
            {"protocol": "INVALID"}
        ), "L8_ENVELOPE_SEAL"),
        (lambda request: request["scenario_translation_packet"]["d8_envelope"].update(
            {"sha256": "0" * 64}
        ), "L8_ENVELOPE_SEAL"),
    ],
)
def test_invalid_ttl_nonce_or_protocol_holds(mutator, expected_layer):
    request = runtime_request()
    mutator(request)
    result = runtime.run_secondary_cloud_runtime(request, MemoryConnector())
    assert result["state"] == "HOLD"
    layer = next(
        item for item in result["verification"]["audit_layers"] if item["layer"] == expected_layer
    )
    assert layer["state"] == "HOLD"


def test_insufficient_evidence_holds():
    request = runtime_request()
    request["scenario_translation_packet"]["d4_evidence"]["evidence_refs"] = []
    result = runtime.run_secondary_cloud_runtime(request, MemoryConnector())
    assert result["state"] == "HOLD"
    layer = next(
        item
        for item in result["verification"]["audit_layers"]
        if item["layer"] == "L5_REFERENCE_EVIDENCE"
    )
    assert layer["state"] == "HOLD"


def test_missing_adc_holds_without_claiming_live_connection():
    result = runtime.run_secondary_cloud_runtime(runtime_request())
    assert result["state"] == "HOLD_CREDENTIAL_NOT_PROVISIONED"
    assert result["external_network_called"] is False
    assert result["seal_status"] == "NOT_SEALED"


def test_runtime_and_gateway_path_have_no_external_network_call():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not ({"google", "httpx", "requests", "socket", "subprocess", "urllib"} & imports)
    gateway_source = GATEWAY_PATH.read_text(encoding="utf-8")
    route_block = gateway_source.split("if self.path == SECONDARY_CLOUD_RUNTIME_PATH:", 1)[1]
    route_block = route_block.split("hazard = block_payload(body)", 1)[0]
    assert "_proxy(" not in route_block
    assert runtime.EXECUTION_CHAIN == [
        "SOURCE",
        "PACKET",
        "CAPABILITY_REF_RESOLVE",
        "PULL_CAPABILITY_PACKET",
        "LOCAL_RECONSTRUCT",
        "LOCAL_COMPARE",
        "VERIFY",
        "HOLD_OR_SEAL",
    ]
