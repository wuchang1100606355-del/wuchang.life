from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_adapters import sovereign_ai_candidate_intake as intake  # noqa: E402
from tools.sovereign_ai_domain_completion_candidate import build_candidate  # noqa: E402


def load_member_gateway():
    path = (
        ROOT
        / "deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py"
    )
    spec = importlib.util.spec_from_file_location("member_candidate_gateway", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gateway = load_member_gateway()


def synthetic_local_member_verifier(packet, request_state, now):
    return {
        "decision": "allow",
        "reason": "synthetic_natural_person_authority_verified",
        "verifier_result": "PASS",
        "evidence_ref": "authority-verifier:sha256:" + ("a" * 64),
    }


gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER = synthetic_local_member_verifier


def candidate(**overrides):
    value = {
        "domain": "COMMUNITY",
        "entity_ref": "entity:community:developer-member:synthetic",
        "attribute_name": "public_description",
        "candidate_value": "SYNTHETIC-CANDIDATE-VALUE",
        "source_mode": "LLM_PUSH",
        "model_ref": "model:laptop:local:synthetic",
        "provider_ref": "provider:laptop:ollama:synthetic",
        "event_ref": "event:developer-member:synthetic",
        "observation_domain_ref": "observation-domain:community:synthetic",
        "rule_ref": "rules/tfct/identity_v0_1",
        "evidence_refs": [],
        "confidence": 0.75,
        "sensitivity": "SAFE_DERIVED",
        "requires_human_confirmation": False,
    }
    value.update(overrides)
    return build_candidate(**value)


def candidate_request(candidate_value=None):
    item = candidate() if candidate_value is None else candidate_value
    return {
        "schema_version": intake.REQUEST_SCHEMA_VERSION,
        "request_id": "request:developer-member:synthetic-0001",
        "candidate": item,
        "previous_value": "SYNTHETIC-PREVIOUS-VALUE",
        "observation_domains": {
            item["observation_domain_ref"]: {
                "configured": True,
                "observations": {"observation_ref": "observation:synthetic"},
            }
        },
    }


def member_authority(**overrides):
    value = {
        "local_source_ref": "odoo:wuchang.member.identity.code:SYNTHETIC-DEVELOPER",
        "issuer": "taiji01:odoo-member-authority",
        "purpose": "sovereign_ai_candidate_submission",
        "service_scope": "developer_member",
        "target_system": "total_field_candidate_gateway",
        "identity_state": "registered",
        "subject_types": ["association_member", "system_operator"],
        "role_refs": ["role:synthetic:developer-operator"],
        "qualification_states": {"developer_operator": True},
        "consent_state": "granted",
        "authorization_scopes": ["sovereign_ai_candidate_submission"],
        "qualification_source_refs": [
            "authority:synthetic:developer-operator",
            "assurance:usage-pattern:sha256:" + ("1" * 64),
            "assurance:login-location:sha256:" + ("2" * 64),
            "assurance:trusted-device:sha256:" + ("3" * 64),
            "assurance:connection-pattern:sha256:" + ("4" * 64),
        ],
        "consent_record_ref": "consent:SYNTHETIC-DEVELOPER",
        "local_state_check_ref": "taiji01:member-authority-state-check:synthetic",
        "verified_at": "2026-07-18T00:00:00Z",
        "issued_at": "2026-07-18T00:00:00Z",
        "expires_at": "2099-07-18T00:15:00Z",
        "nonce": "synthetic-developer-member-nonce",
    }
    value.update(overrides)
    return value


def member_request_state(**overrides):
    value = {
        "purpose": "sovereign_ai_candidate_submission",
        "target_system": "total_field_candidate_gateway",
        "requested_scopes": ["sovereign_ai_candidate_submission"],
        "provider_link_state": "PROVIDER_LINK_FOUND",
        "current_authority_state": {
            "identity_state": "registered",
            "consent_state": "granted",
            "consent_record_ref": "consent:SYNTHETIC-DEVELOPER",
        },
    }
    value.update(overrides)
    return value


def bridge_payload(**overrides):
    value = {
        "schema_version": "w7tp-member-sovereign-candidate-bridge/0.1",
        "packet": gateway.issue_member_sovereign_packet(member_authority()),
        "request_state": member_request_state(),
        "candidate_request": candidate_request(),
    }
    value.update(overrides)
    return value


def test_request_schema_is_closed_and_valid() -> None:
    schema = json.loads(intake.REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False


def test_candidate_intake_returns_only_non_executable_summary() -> None:
    result = intake.run_sovereign_ai_candidate_intake(candidate_request())
    assert result["state"] == "PASS_CANDIDATE_ACCEPTED"
    assert result["candidate_core_decision"] == "ALLOW"
    assert result["candidate_only"] is True
    assert result["execution_authority"] is False
    assert result["production_commit_applied"] is False
    assert result["seal_applied"] is False
    serialized = json.dumps(result, ensure_ascii=False)
    assert "SYNTHETIC-CANDIDATE-VALUE" not in serialized
    assert "SYNTHETIC-PREVIOUS-VALUE" not in serialized


def test_member_entry_requires_google_link_system_operator_and_role_ref() -> None:
    valid = bridge_payload()
    result = gateway.member_total_field_candidate_intake(
        valid, "2026-07-18T00:01:00Z"
    )
    assert result["state"] == "PASS_CANDIDATE_ACCEPTED"
    assert result["member_entry"] is True
    assert result["member_authorization_decision"] == "allow"
    assert result["member_plaintext_included"] is False

    no_link = bridge_payload()
    no_link["request_state"]["provider_link_state"] = "LINKING_PENDING"
    no_link_result = gateway.member_total_field_candidate_intake(
        no_link, "2026-07-18T00:01:00Z"
    )
    assert no_link_result["state"] == "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
    assert no_link_result["member_authorization_reason"] == "verified_provider_link_required"

    no_operator = bridge_payload(
        packet=gateway.issue_member_sovereign_packet(
            member_authority(subject_types=["association_member"])
        )
    )
    no_operator_result = gateway.member_total_field_candidate_intake(
        no_operator, "2026-07-18T00:01:00Z"
    )
    assert no_operator_result["state"] == "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
    assert no_operator_result["member_authorization_reason"] == "system_operator_membership_required"

    incomplete_assurance = bridge_payload(
        packet=gateway.issue_member_sovereign_packet(
            member_authority(
                qualification_source_refs=["authority:synthetic:developer-operator"]
            )
        )
    )
    incomplete_result = gateway.member_total_field_candidate_intake(
        incomplete_assurance, "2026-07-18T00:01:00Z"
    )
    assert incomplete_result["state"] == "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
    assert incomplete_result["member_authorization_reason"].startswith(
        "natural_person_assurance_incomplete:"
    )


def test_one_8d_member_packet_carries_full_verified_scope_vector() -> None:
    all_scopes = sorted(gateway.AUTHORIZATION_SCOPES)
    packet = gateway.issue_member_sovereign_packet(
        member_authority(authorization_scopes=all_scopes)
    )
    assert set(packet) == {
        "D1_INTENT",
        "D2_STATE",
        "D3_COORDINATE",
        "D4_EVIDENCE",
        "D5_EXECUTION",
        "D6_GENERATIVE_TRANSMISSION",
        "D7_RISK",
        "D8_ENVELOPE",
    }
    assert packet["D2_STATE"]["authorization_scopes"] == all_scopes
    assert gateway.validate_member_sovereign_packet(
        packet, now="2026-07-18T00:01:00Z"
    ) == []
    result = gateway.member_total_field_candidate_intake(
        bridge_payload(packet=packet), "2026-07-18T00:01:00Z"
    )
    assert result["state"] == "PASS_CANDIDATE_ACCEPTED"
    assert result["member_authorization_decision"] == "allow"
    assert result["production_commit_applied"] is False


def test_local_natural_person_verifier_is_mandatory_and_red_team_block_is_evidenced() -> None:
    original = gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER
    try:
        gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER = None
        unbound = gateway.member_total_field_candidate_intake(
            bridge_payload(), "2026-07-18T00:01:00Z"
        )
        assert unbound["state"] == "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
        assert unbound["member_authorization_reason"] == (
            "local_natural_person_authority_verifier_not_bound"
        )

        gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER = lambda packet, request, now: {
            "decision": "block",
            "reason": "unsubstantiated_negative_claim",
            "verifier_result": "BLOCK",
        }
        unsupported = gateway.member_total_field_candidate_intake(
            bridge_payload(), "2026-07-18T00:01:00Z"
        )
        assert unsupported["state"] == "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
        assert unsupported["member_authorization_reason"] == (
            "red_team_contradiction_evidence_required"
        )

        gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER = lambda packet, request, now: {
            "decision": "block",
            "reason": "red_team_proven_not_subject",
            "verifier_result": "BLOCK",
            "evidence_ref": "red-team-contradiction:sha256:" + ("b" * 64),
        }
        evidenced = gateway.member_total_field_candidate_intake(
            bridge_payload(), "2026-07-18T00:01:00Z"
        )
        assert evidenced["state"] == "BLOCK_NOT_NATURAL_PERSON"
        assert evidenced["member_authorization_decision"] == "deny"

        gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER = lambda packet, request, now: {
            "decision": "step_up",
            "reason": "high_assurance_reverification_required",
            "step_up_method": "w7tp_privacy_preserving_no_retention_image",
        }
        step_up = gateway.member_total_field_candidate_intake(
            bridge_payload(), "2026-07-18T00:01:00Z"
        )
        assert step_up["state"] == "HOLD_IDENTITY_OR_AUTHORITY_NOT_CONVERGED"
        assert step_up["step_up_required"] is True
        assert step_up["step_up_method"] == (
            "w7tp_privacy_preserving_no_retention_image"
        )
    finally:
        gateway.LOCAL_PRIVILEGED_MEMBER_VERIFIER = original


def test_member_authority_cannot_be_claimed_inside_candidate() -> None:
    unsafe = candidate()
    unsafe["candidate_value"] = {
        "member_plaintext": "MEMBER-PLAINTEXT-SYNTHETIC-DO-NOT-ECHO"
    }
    unsafe.pop("candidate_hash")
    unsafe = build_candidate(**unsafe)
    result = intake.run_sovereign_ai_candidate_intake(candidate_request(unsafe))
    serialized = json.dumps(result, ensure_ascii=False)
    assert result["state"] == "BLOCK_REQUEST_FORBIDDEN_FIELD"
    assert "MEMBER-PLAINTEXT-SYNTHETIC-DO-NOT-ECHO" not in serialized
    assert result["production_commit_applied"] is False

    image_payload = bridge_payload()
    image_payload["request_state"]["face_image"] = "SYNTHETIC-IMAGE-DATA"
    assert "request_state.face_image" in gateway._forbidden_member_paths(image_payload)


def test_source_mode_and_observation_domain_fail_closed() -> None:
    wrong_mode = candidate(source_mode="TOTAL_FIELD_PULL")
    mode_result = intake.run_sovereign_ai_candidate_intake(
        candidate_request(wrong_mode)
    )
    assert mode_result["state"] == "BLOCK_SOURCE_MODE_FORBIDDEN"

    mismatched = candidate_request()
    mismatched["observation_domains"] = {
        "observation-domain:property:synthetic": {
            "configured": True,
            "observations": {},
        }
    }
    ref_result = intake.run_sovereign_ai_candidate_intake(mismatched)
    assert ref_result["state"] == "HOLD_OBSERVATION_DOMAIN_REF_MISMATCH"


def test_intake_adapter_has_no_network_database_or_process_api() -> None:
    source = intake.__file__ and Path(intake.__file__).read_text(encoding="utf-8")
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
    assert imports.isdisjoint(
        {"httpx", "odoo", "openai", "psycopg", "requests", "socket", "sqlite3", "subprocess", "urllib"}
    )


def test_http_member_route_is_allowlisted_direct_and_never_proxied(tmp_path) -> None:
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(
        json.dumps(
            {
                "nodes": [
                    {"node_id": "laptop-test", "allowed_ips": ["127.0.0.1"]}
                ]
            }
        ),
        encoding="utf-8",
    )
    gateway.ALLOWLIST_PATH = allowlist
    gateway.AUDIT_PATH = tmp_path / "audit.jsonl"
    server = ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}{gateway.MEMBER_TOTAL_FIELD_CANDIDATE_PATH}"
        body = json.dumps(bridge_payload()).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        assert result["state"] == "PASS_CANDIDATE_ACCEPTED"
        assert result["external_network_called"] is False

        spoofed = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Forwarded-For": "127.0.0.1",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(spoofed, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
            blocked = json.loads(exc.read().decode("utf-8"))
            assert blocked["state"] == "BLOCK_FORWARDED_IDENTITY_FORBIDDEN"
        else:
            raise AssertionError("forwarded identity spoof was accepted")

        privileged_issue = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/w7tp/member-sovereign/issue",
            data=json.dumps({"authority": member_authority()}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(privileged_issue, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            blocked_issue = json.loads(exc.read().decode("utf-8"))
            assert blocked_issue["reason"] == "privileged_packet_local_authority_only"
        else:
            raise AssertionError("laptop self-issued a privileged member packet")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
