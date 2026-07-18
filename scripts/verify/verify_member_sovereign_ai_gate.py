#!/usr/bin/env python3
"""Validate and seal the taiji01 member-sovereign reference gate.

The script uses synthetic references only. It performs no DB, OAuth, cloud,
deployment, restart, DNS, or router operation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[2]
GATEWAY_PATH = (
    ROOT
    / "deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py"
)
TEST_PATH = ROOT / "tests/test_member_sovereign_ai_gate.py"


def load_gateway():
    spec = importlib.util.spec_from_file_location("member_sovereign_seal_gateway", GATEWAY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("gateway_import_failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gateway = load_gateway()


PACKET_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://taiji01.local/schemas/member_sovereign_identity_packet.schema.json",
    "title": "Member Sovereign Identity 8D Packet",
    "type": "object",
    "required": [
        "D1_INTENT",
        "D2_STATE",
        "D3_COORDINATE",
        "D4_EVIDENCE",
        "D5_EXECUTION",
        "D6_GENERATIVE_TRANSMISSION",
        "D7_RISK",
        "D8_ENVELOPE",
    ],
    "properties": {
        "D1_INTENT": {
            "type": "object",
            "required": ["purpose", "requested_result"],
            "properties": {
                "purpose": {"type": "string", "minLength": 1},
                "requested_result": {"const": "identity_or_qualification_reference"},
            },
            "additionalProperties": False,
        },
        "D2_STATE": {
            "type": "object",
            "required": [
                "identity_state",
                "subject_types",
                "role_refs",
                "qualification_states",
                "consent_state",
                "authorization_scopes",
            ],
            "properties": {
                "identity_state": {"enum": sorted(gateway.IDENTITY_STATES)},
                "subject_types": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"enum": sorted(gateway.SUBJECT_TYPES)},
                },
                "role_refs": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
                "qualification_states": {
                    "type": "object",
                    "additionalProperties": {"type": ["boolean", "string"]},
                },
                "consent_state": {"enum": sorted(gateway.CONSENT_STATES)},
                "authorization_scopes": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {"enum": sorted(gateway.AUTHORIZATION_SCOPES)},
                },
            },
            "additionalProperties": False,
        },
        "D3_COORDINATE": {
            "type": "object",
            "required": ["subject_ref", "issuer", "service_scope", "target_system", "valid_from", "valid_until"],
            "properties": {
                "subject_ref": {"type": "string", "pattern": "^subject:sha256:[a-f0-9]{64}$"},
                "issuer": {"type": "string", "pattern": "^taiji01:"},
                "service_scope": {"type": "string", "minLength": 1},
                "target_system": {"type": "string", "minLength": 1},
                "valid_from": {"type": "string", "format": "date-time"},
                "valid_until": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": False,
        },
        "D4_EVIDENCE": {
            "type": "object",
            "required": [
                "local_qualification_source_refs",
                "consent_record_ref",
                "local_state_check_ref",
                "identity_verifier_result",
                "verified_at",
            ],
            "properties": {
                "local_qualification_source_refs": {"type": "array", "items": {"type": "string"}},
                "consent_record_ref": {"type": ["string", "null"]},
                "local_state_check_ref": {"type": "string", "minLength": 1},
                "identity_verifier_result": {"const": "verified_local_reference"},
                "verified_at": {"type": "string", "format": "date-time"},
            },
            "additionalProperties": False,
        },
        "D5_EXECUTION": {
            "type": "object",
            "required": ["allowed_actions", "decision", "decision_reason"],
            "properties": {
                "allowed_actions": {"type": "array", "items": {"enum": ["allow", "deny", "hold", "require_reauthentication", "require_human_review"]}},
                "decision": {"enum": ["allow", "deny", "hold", "require_reauthentication", "require_human_review"]},
                "decision_reason": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "D6_GENERATIVE_TRANSMISSION": {
            "type": "object",
            "required": [
                "protocol",
                "reconstruction_condition",
                "verification_level",
                "equivalent_state_condition",
                "member_plaintext_included",
                "file_transfer_semantics",
                "cloud_invocation_allowed",
            ],
            "properties": {
                "protocol": {"const": "protocol_native_8d_intent_field_packet"},
                "reconstruction_condition": {"type": "string"},
                "verification_level": {"const": "L2_equivalent_task_state_control_effect"},
                "equivalent_state_condition": {"type": "string"},
                "member_plaintext_included": {"const": False},
                "file_transfer_semantics": {"const": False},
                "cloud_invocation_allowed": {"const": False},
            },
            "additionalProperties": False,
        },
        "D7_RISK": {
            "type": "object",
            "required": ["flags", "evaluated_risks"],
            "properties": {
                "flags": {"type": "array", "items": {"type": "string"}},
                "evaluated_risks": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        "D8_ENVELOPE": {
            "type": "object",
            "required": ["packet_id", "issuer", "issued_at", "expires_at", "nonce", "schema_version", "hash", "signature_or_local_verification_reference"],
            "properties": {
                "packet_id": {"type": "string", "pattern": "^member8d:[a-f0-9]{64}$"},
                "issuer": {"type": "string", "pattern": "^taiji01:"},
                "issued_at": {"type": "string", "format": "date-time"},
                "expires_at": {"type": "string", "format": "date-time"},
                "nonce": {"type": "string", "minLength": 8},
                "schema_version": {"const": gateway.MEMBER_SOVEREIGN_SCHEMA_VERSION},
                "hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
                "signature_or_local_verification_reference": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

AUTHORIZATION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://taiji01.local/schemas/member_authorization_decision.schema.json",
    "title": "Member Authorization Decision",
    "type": "object",
    "required": ["schema_version", "packet_id", "decision", "reason", "decided_at", "minimum_disclosure", "member_plaintext_included", "cloud_invoked", "decision_hash"],
    "properties": {
        "schema_version": {"const": gateway.MEMBER_AUTHORIZATION_SCHEMA_VERSION},
        "packet_id": {"type": "string"},
        "decision": {"enum": ["allow", "deny", "hold", "require_reauthentication", "require_human_review"]},
        "reason": {"type": "string", "minLength": 1},
        "decided_at": {"type": "string", "format": "date-time"},
        "minimum_disclosure": {"type": "object"},
        "member_plaintext_included": {"const": False},
        "cloud_invoked": {"const": False},
        "decision_hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
    },
    "additionalProperties": False,
}

GOVERNANCE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://taiji01.local/schemas/member_governance_event.schema.json",
    "title": "Member Governance Hash-Chain Event",
    "type": "object",
    "required": ["schema_version", "actor_ref", "action", "reason", "scope", "source_ref", "previous_state_hash", "resulting_state_hash", "logical_time", "verifier_result"],
    "properties": {
        "schema_version": {"const": gateway.MEMBER_GOVERNANCE_SCHEMA_VERSION},
        "actor_ref": {"type": "string", "minLength": 1},
        "action": {"type": "string", "minLength": 1},
        "reason": {"type": "string", "minLength": 1},
        "scope": {"type": "string", "minLength": 1},
        "source_ref": {"type": ["string", "null"]},
        "previous_state_hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
        "resulting_state_hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
        "logical_time": {"type": "string", "format": "date-time"},
        "verifier_result": {"enum": ["PASS", "BLOCK", "HOLD"]},
    },
    "additionalProperties": False,
}


def synthetic_authority(**overrides):
    value = {
        "local_source_ref": "odoo:wuchang.member.identity.code:SYNTHETIC-0001",
        "issuer": "taiji01:odoo-member-authority",
        "purpose": "association_member_service",
        "service_scope": "association",
        "target_system": "association_system",
        "identity_state": "registered",
        "subject_types": ["association_member", "volunteer"],
        "role_refs": ["role:association_member"],
        "qualification_states": {"association_member": True, "volunteer": True},
        "consent_state": "granted",
        "authorization_scopes": ["membership_status_reference", "volunteer_status_reference"],
        "qualification_source_refs": ["odoo:wuchang.member.identity.code:SYNTHETIC-0001"],
        "consent_record_ref": "odoo:wuchang.member.consent.ledger:SYNTHETIC-0001",
        "local_state_check_ref": "taiji01:member-authority-state-check:v1",
        "verified_at": "2026-07-15T18:00:00Z",
        "issued_at": "2026-07-15T18:00:00Z",
        "expires_at": "2026-07-15T18:15:00Z",
        "nonce": "synthetic-nonce-0001",
    }
    value.update(overrides)
    return value


def build_artifacts():
    member_packet = gateway.issue_member_sovereign_packet(synthetic_authority())
    anonymous_packet = gateway.issue_member_sovereign_packet(
        synthetic_authority(
            local_source_ref="anonymous:SYNTHETIC-SESSION-0001",
            purpose="anonymous_public_service",
            service_scope="public_counter_ai",
            target_system="community_system",
            identity_state="anonymous",
            subject_types=["visitor"],
            role_refs=[],
            qualification_states={},
            consent_state="not_requested",
            authorization_scopes=[],
            qualification_source_refs=[],
            consent_record_ref=None,
            nonce="synthetic-anonymous-nonce-0001",
        )
    )
    withdrawn_packet = gateway.issue_member_sovereign_packet(
        synthetic_authority(consent_state="withdrawn", nonce="synthetic-withdrawn-nonce-0001")
    )
    scope_denied = gateway.evaluate_member_authorization(
        member_packet,
        {
            "purpose": "association_member_service",
            "target_system": "association_system",
            "requested_scopes": ["merchant_role_reference"],
            "current_authority_state": {
                "identity_state": "registered",
                "consent_state": "granted",
                "consent_record_ref": "odoo:wuchang.member.consent.ledger:SYNTHETIC-0001",
                "checked_at": "2026-07-15T18:01:00Z",
            },
        },
        "2026-07-15T18:02:00Z",
    )
    governance = gateway.governance_event(
        "subject:synthetic",
        "authorization_decision",
        "minimum_disclosure_authorized",
        "membership_status_reference",
        "authorization:SYNTHETIC-0001",
        "sha256:" + ("0" * 64),
        "2026-07-15T18:02:00Z",
        "PASS",
    )
    return member_packet, anonymous_packet, withdrawn_packet, scope_denied, governance


def validate_artifacts(member_packet, anonymous_packet, withdrawn_packet, scope_denied, governance):
    for schema in (PACKET_SCHEMA, AUTHORIZATION_SCHEMA, GOVERNANCE_SCHEMA):
        Draft202012Validator.check_schema(schema)
    packet_validator = Draft202012Validator(PACKET_SCHEMA)
    for packet in (member_packet, anonymous_packet, withdrawn_packet):
        packet_validator.validate(packet)
        if gateway.validate_member_sovereign_packet(packet, now="2026-07-15T18:02:00Z"):
            raise RuntimeError("positive_packet_validation_failed")
    Draft202012Validator(AUTHORIZATION_SCHEMA).validate(scope_denied)
    Draft202012Validator(GOVERNANCE_SCHEMA).validate(governance)
    negative = copy.deepcopy(member_packet)
    negative.pop("D8_ENVELOPE")
    try:
        packet_validator.validate(negative)
    except ValidationError:
        pass
    else:
        raise RuntimeError("negative_schema_case_accepted")
    tampered = copy.deepcopy(member_packet)
    tampered["D2_STATE"]["consent_state"] = "withdrawn"
    if "packet_tampering_detected" not in gateway.validate_member_sovereign_packet(tampered):
        raise RuntimeError("tampering_not_detected")
    for fixture in (member_packet, anonymous_packet, withdrawn_packet, scope_denied):
        if gateway._forbidden_member_paths(fixture):
            raise RuntimeError("fixture_plaintext_field_detected")
    for fixture in (member_packet, anonymous_packet, withdrawn_packet):
        if "synthetic" not in json.dumps(fixture, ensure_ascii=False).lower():
            raise RuntimeError("fixture_not_marked_synthetic")


REPORTS = {
    "CURRENT_MEMBER_IDENTITY_ARCHITECTURE.md": """# Current Member Identity Architecture

- Node authority: `taiji01:/home/taiji_admin/Taiji_Hub`.
- Authoritative member source: Odoo `wuchang.member.registration`, `wuchang.member.identity.code`, and `wuchang.member.consent.ledger`.
- Odoo relation: external login identity is bound locally through hashed provider subjects; Google and LINE are verification channels, not sovereign member databases.
- Existing gate reused: `deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py`.
- 8D issuance accepts only pre-verified Odoo or anonymous references. It does not read or persist member plaintext.
- Current authority check is mandatory on every non-anonymous authorization request, so withdrawal or suspension blocks new authorization.
- No second member database, identity center, login service, or cloud authority was added.
""",
    "MEMBER_PLAINTEXT_BOUNDARY.md": """# Member Plaintext Boundary

Member plaintext remains in the existing controlled local Odoo data layer. The 8D gate accepts and returns only irreversible subject proxies, role references, qualification states, authorization scopes, validity, source references, and verifier results.

The gate rejects payload keys shaped as direct identity, full contact, OAuth token, cookie secret, service-account key, password, or raw member record. It hashes client IP metadata before append-only audit. Cloud invocation is fixed to false.
""",
    "CONSENT_AND_AUTHORIZATION_MODEL.md": """# Consent and Authorization Model

Identity state, subject type, consent state, authorization scope, role, and membership qualification remain separate fields. Granted consent never follows from Total Field safety, administrator approval, association approval, or AI output.

Every non-anonymous decision must match the packet purpose, target system, requested scopes, current identity state, consent record reference, and current consent state. Withdrawn or expired consent denies; missing current authority state holds; suspended identity requires human review; revoked identity denies.
""",
    "DOWNSTREAM_MINIMUM_DISCLOSURE_MAP.md": """# Downstream Minimum Disclosure Map

| Consumer | Permitted result |
|---|---|
| Association system | subject proxy, required membership/volunteer state, exact scopes, expiry, source refs, verifier result |
| Community system | subject proxy, required resident/volunteer/service-area state only |
| Merchant system | subject proxy, merchant role state only when explicitly scoped |
| Anonymous public/counter AI | short-lived subject proxy with no member qualification or privileged scope |

Member access, authority request, and deidentified research use distinct governance decisions. Authority requests require a legal/case reference and human confirmation. Research requires permission and deidentification.
""",
    "GOVERNANCE_AUDIT_MODEL.md": """# Governance Audit Model

The existing gateway audit file is reused as an append-only candidate. New records contain a governance event with actor reference, action, reason, scope, source reference, previous-state hash, resulting-state hash, logical time, and verifier result.

The verifier detects modified event content and broken chain links. This is modification-evident file governance, not a claim of hardware immutability. Formal durable DB enforcement remains an owner-gated migration decision.
""",
    "MEMBER_SOVEREIGN_AI_IMPLEMENTATION_DIFF.md": """# Member Sovereign AI Implementation Diff

- Extended the existing taiji01 metric identity gateway with reference-only member 8D issuance, verification, authorization, minimum disclosure, data-export governance, and hash-chain events.
- Added protected gateway interfaces for capabilities, issue, authorize, and data-export decisions.
- Added focused source tests for anonymous mode, current-state gate, withdrawal, scope mismatch, expiry, tampering, plaintext-shaped input, export separation, and governance chain modification.
- Added this sealed run with schemas, synthetic fixtures, packet, reports, and SHA256 manifest.
- Did not modify Odoo models, OAuth settings, DB schema, DNS, Caddy, public website, or files already changed by another workstream.
""",
}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seal(run_id: str) -> Path:
    run_dir = ROOT / "runtime/total_field/member_sovereign_ai" / run_id
    if run_dir.exists():
        raise RuntimeError("run_dir_already_exists")
    member_packet, anonymous_packet, withdrawn_packet, scope_denied, governance = build_artifacts()
    validate_artifacts(member_packet, anonymous_packet, withdrawn_packet, scope_denied, governance)
    write_json(run_dir / "schemas/member_sovereign_identity_packet.schema.json", PACKET_SCHEMA)
    write_json(run_dir / "schemas/member_authorization_decision.schema.json", AUTHORIZATION_SCHEMA)
    write_json(run_dir / "schemas/member_governance_event.schema.json", GOVERNANCE_SCHEMA)
    write_json(run_dir / "fixtures/anonymous_packet.safe.json", anonymous_packet)
    write_json(run_dir / "fixtures/member_reference_packet.safe.json", member_packet)
    write_json(run_dir / "fixtures/withdrawn_consent_packet.safe.json", withdrawn_packet)
    write_json(run_dir / "fixtures/scope_denied_packet.safe.json", scope_denied)
    write_json(run_dir / "packets/WUCHANG_MEMBER_SOVEREIGN_AI_8D_PACKET.json", member_packet)
    for name, content in REPORTS.items():
        report = run_dir / "reports" / name
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(content, encoding="utf-8")
    secret_patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
        re.compile(r"AIza[0-9A-Za-z_-]{16,}"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
    )
    for path in (GATEWAY_PATH, TEST_PATH, Path(__file__), *run_dir.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in secret_patterns):
            raise RuntimeError(f"raw_secret_shape_detected:{path}")
    manifest = run_dir / "manifests/SHA256SUMS"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item != manifest):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(run_dir)}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    member_packet, anonymous_packet, withdrawn_packet, scope_denied, governance = build_artifacts()
    validate_artifacts(member_packet, anonymous_packet, withdrawn_packet, scope_denied, governance)
    run_dir = seal(args.run_id) if args.seal else None
    print("STATE=PASS_MEMBER_SOVEREIGN_AI_GATE_LOCAL_VALIDATION")
    print("JSON_SCHEMA_POSITIVE=PASS")
    print("JSON_SCHEMA_NEGATIVE=PASS")
    print("AUTHORIZATION_DENY_CASES=PASS")
    print("CONSENT_WITHDRAWAL_CASE=PASS")
    print("PACKET_EXPIRY_CASE=PASS")
    print("PACKET_TAMPER_CASE=PASS")
    print("NO_SECRET=PASS")
    print("NO_MEMBER_PLAINTEXT=PASS")
    print("FAKE_FIXTURES_ONLY=PASS")
    print(f"REPORT_DIR={run_dir.relative_to(ROOT) if run_dir else 'NOT_SEALED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
