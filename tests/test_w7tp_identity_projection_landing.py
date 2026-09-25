from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.total_field.w7tp_intent_field_suite.api import process_http_request
from tools.total_field.w7tp_intent_field_suite.identity_prefix import (
    build_natural_person_identity_prefix,
)
from tools.total_field.w7tp_intent_field_suite.identity_projection import (
    BOUNDARY_HEADER,
    HEADER_BY_FIELD,
    PROJECTION_FIELDS,
    PROJECTION_HEADER_NAMES,
    TRUSTED_BOUNDARY_VALUE,
    prefix_ref_for,
    trusted_caddy_boundary,
)


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_LINKING_PATH = (
    ROOT
    / "Taiji_Odoo/addons/wuchang_google_member_login/services/account_linking.py"
)
CADDY_CANDIDATE_PATH = (
    ROOT / "deploy/caddy/w7tp-odoo-identity-projection.caddy"
)
SCHEMA_PATH = ROOT / "schemas/field/w7tp_identity_projection.schema.json"
COMPLETE_GENERIC_INTENT = {
    "requested_result": "分析候選",
    "constraints": "只讀",
    "evidence_refs": ["repo 正典"],
}


def load_account_linking():
    spec = importlib.util.spec_from_file_location(
        "w7tp_projection_account_linking", ACCOUNT_LINKING_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


odoo_linking = load_account_linking()


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def ref(prefix: str, label: str) -> str:
    return f"{prefix}:sha256:{digest(label)}"


def verified_link(label: str = "person-one") -> dict[str, str]:
    return {
        "local_subject_reference": ref("subject", f"{label}-local-subject"),
        "link_state": "PROVIDER_LINK_FOUND",
        "verifier_result": "PASS",
    }


def identity_prefix_for(link: dict[str, str], label: str = "person-one"):
    identity_ref = odoo_linking.identity_packet_ref_from_link_context(link)
    packet = build_natural_person_identity_prefix(
        identity_packet_ref=identity_ref,
        protected_plaintext_binding_ref=ref(
            "identity_binding_ref", f"{label}-protected-record"
        ),
        identity_registry_ref=ref(
            "identity_registry_ref", "shared-total-field-registry"
        ),
        field_context_ref="field_context_ref:wuchang.shared-runtime",
        device_bindings=[
            {
                "device_ref": ref("device_ref", f"{label}-device"),
                "binding_ref": ref("binding_ref", f"{label}-device-binding"),
                "state": "ACTIVE",
            }
        ],
        provider_bindings=[
            {
                "provider_ref": "provider_ref:google",
                "provider_subject_sha256": digest(f"{label}-provider-subject"),
                "binding_ref": ref("binding_ref", f"{label}-provider-binding"),
                "state": "ACTIVE",
            }
        ],
        source_refs=[ref("source_ref", f"{label}-identity-canonical")],
        binding_evidence_refs=[
            ref("evidence_ref", f"{label}-binding-evidence")
        ],
    )
    prefix_ref = prefix_ref_for(packet)
    registry = {
        "entries": [
            {
                "protected_plaintext_binding_ref": packet["D1"][
                    "protected_plaintext_binding_ref"
                ],
                "identity_packet_ref": identity_ref,
                "identity_prefix_ref": prefix_ref,
            }
        ]
    }
    return packet, prefix_ref, registry


def projection_for(
    link: dict[str, str],
    prefix_ref: str,
    *,
    nonce_label: str = "projection-one",
    issued_at: str = "2026-07-18T10:00:00Z",
    expires_at: str = "2026-07-18T10:04:00Z",
):
    projection = odoo_linking.build_verified_identity_projection(
        link,
        prefix_ref=prefix_ref,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=ref("nonce_ref", nonce_label),
    )
    return projection, odoo_linking.identity_projection_response_headers(projection)


def run_projected_request(
    headers,
    packet,
    prefix_ref,
    registry,
    *,
    trusted_boundary=True,
    now="2026-07-18T10:01:00Z",
):
    resolver = {prefix_ref: packet}.get
    return process_http_request(
        json.dumps(
            {"profile": "GENERIC", "intent": COMPLETE_GENERIC_INTENT}
        ).encode("utf-8"),
        trusted_identity_projection_headers=headers,
        trusted_boundary=trusted_boundary,
        identity_prefix_resolver=resolver,
        identity_registry_snapshot=registry,
        projection_now=now,
    )


def test_valid_odoo_caddy_9107_projection_passes_and_is_schema_valid():
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    projection, headers = projection_for(link, prefix_ref)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(projection)) == []
    assert set(projection) == set(PROJECTION_FIELDS)
    assert set(headers) == set(PROJECTION_HEADER_NAMES)

    status, result = run_projected_request(
        headers, packet, prefix_ref, registry
    )
    assert status == 200
    assert result["D1"]["identity_packet_ref"] == projection["identity_ref"]
    assert result["identity_prefix"] == packet
    assert result["D8"]["identity_prefix_sha256"] == packet["D8"][
        "prefix_sha256"
    ]
    assert result["execution_metadata"]["identity_projection_state"] == (
        "PASS_TRUSTED_IDENTITY_PROJECTION"
    )


def test_direct_forged_headers_and_missing_projection_are_rejected():
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    _, headers = projection_for(link, prefix_ref)
    forged_status, forged = run_projected_request(
        headers,
        packet,
        prefix_ref,
        registry,
        trusted_boundary=False,
    )
    assert forged_status == 401
    assert forged["reason_code"] == "IDENTITY_PROJECTION_UNTRUSTED_SOURCE"

    missing_status, missing = run_projected_request(
        {}, packet, prefix_ref, registry, trusted_boundary=True
    )
    assert missing_status == 401
    assert missing["reason_code"] == "IDENTITY_PROJECTION_HEADER_REQUIRED"


def test_identical_client_headers_do_not_establish_the_caddy_boundary():
    headers = {BOUNDARY_HEADER: TRUSTED_BOUNDARY_VALUE}
    assert trusted_caddy_boundary(headers, "203.0.113.9") is False
    assert trusted_caddy_boundary({}, "127.0.0.1") is False
    assert trusted_caddy_boundary(headers, "127.0.0.1") is True


@pytest.mark.parametrize("field", PROJECTION_FIELDS)
def test_every_projection_field_tamper_is_rejected(field: str):
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    _, headers = projection_for(link, prefix_ref)
    tampered = dict(headers)
    header = HEADER_BY_FIELD[field]
    replacements = {
        "schema_version": "W7TP-ODOO-IDENTITY-PROJECTION/2.0",
        "identity_ref": ref("identity_packet_ref", "tampered-identity"),
        "canonical_ref": "canonical_ref:UNTRUSTED",
        "prefix_ref": ref("identity_prefix_ref", "tampered-prefix"),
        "prefix_version": "W7TP-NATURAL-PERSON-IDENTITY-PREFIX/2.0",
        "issuer_ref": "issuer_ref:untrusted",
        "projection_ref": ref("identity_projection_ref", "tampered-projection"),
        "projection_sha256": digest("tampered-sha"),
        "issued_at": "2026-07-18T10:00:01Z",
        "expires_at": "2026-07-18T10:03:59Z",
        "nonce": ref("nonce_ref", "tampered-nonce"),
    }
    tampered[header] = replacements[field]
    status, result = run_projected_request(
        tampered, packet, prefix_ref, registry
    )
    assert status != 200
    assert result["state"] == "HOLD"


def test_expired_projection_is_rejected():
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    _, headers = projection_for(
        link,
        prefix_ref,
        issued_at="2026-07-18T09:00:00Z",
        expires_at="2026-07-18T09:04:00Z",
    )
    status, result = run_projected_request(
        headers,
        packet,
        prefix_ref,
        registry,
        now="2026-07-18T09:04:00Z",
    )
    assert status == 401
    assert result["reason_code"] == "IDENTITY_PROJECTION_EXPIRED"


def test_same_identity_keeps_prefix_and_different_identity_cannot_share_it():
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    first_projection, first_headers = projection_for(
        link, prefix_ref, nonce_label="projection-one"
    )
    second_projection, second_headers = projection_for(
        link, prefix_ref, nonce_label="projection-two"
    )
    first_status, first = run_projected_request(
        first_headers, packet, prefix_ref, registry
    )
    second_status, second = run_projected_request(
        second_headers, packet, prefix_ref, registry
    )
    assert (first_status, second_status) == (200, 200)
    assert first_projection["projection_ref"] != second_projection["projection_ref"]
    assert first["D8"]["identity_prefix_sha256"] == second["D8"][
        "identity_prefix_sha256"
    ]

    other_link = verified_link("person-two")
    _, conflicting_headers = projection_for(other_link, prefix_ref)
    conflict_status, conflict = run_projected_request(
        conflicting_headers, packet, prefix_ref, registry
    )
    assert conflict_status == 422
    assert conflict["reason_code"] == "IDENTITY_PROJECTION_IDENTITY_MISMATCH"


def test_odoo_projection_requires_verified_link_and_never_projects_plaintext():
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    projection, headers = projection_for(link, prefix_ref)
    status, result = run_projected_request(
        headers, packet, prefix_ref, registry
    )
    serialized = json.dumps(
        {"projection": projection, "headers": headers, "result": result},
        ensure_ascii=False,
        sort_keys=True,
    )
    assert status == 200
    assert link["local_subject_reference"] not in serialized
    assert result["D5"]["side_effects"]["member_plaintext"] is False
    assert "credential_material" in serialized
    assert '"credential_material_inside_packet": false' in serialized

    for state, verifier in (("LINKING_PENDING", "HOLD"), ("LINK_DENIED", "BLOCK")):
        held = dict(link, link_state=state, verifier_result=verifier)
        with pytest.raises(ValueError):
            projection_for(held, prefix_ref)


def test_active_forward_auth_uses_only_existing_opaque_identity_ref():
    link = verified_link()
    identity_ref = odoo_linking.identity_packet_ref_from_link_context(link)
    headers = {HEADER_BY_FIELD["identity_ref"]: identity_ref}
    payload = {
        "profile": "GENERIC",
        "intent": COMPLETE_GENERIC_INTENT,
        "nonce": ref("nonce_ref", "active-ref-only-request"),
        "return_coordinate": "/wuchang/intent-field",
    }
    status, result = process_http_request(
        json.dumps(payload).encode("utf-8"),
        trusted_identity_projection_headers=headers,
        trusted_boundary=True,
    )
    receipt = result["execution_metadata"]["total_field_receipt"]
    serialized = json.dumps(
        {"headers": headers, "result": result},
        ensure_ascii=False,
        sort_keys=True,
    )
    assert status == 200
    assert receipt["identity_ref"] == identity_ref
    assert receipt["receiver_call_count"] == 1
    assert receipt["member_plaintext"] is False
    assert link["local_subject_reference"] not in serialized
    assert "identity_prefix_ref" not in serialized
    assert "provider_subject_reference" not in serialized


def test_registry_snapshot_is_ref_only_and_rejection_never_echoes_value():
    link = verified_link()
    packet, prefix_ref, registry = identity_prefix_for(link)
    _, headers = projection_for(link, prefix_ref)
    unsafe_registry = json.loads(json.dumps(registry))
    unsafe_registry["entries"][0]["display_name"] = "SYNTHETIC-PRIVATE-VALUE"
    status, result = run_projected_request(
        headers, packet, prefix_ref, unsafe_registry
    )
    assert status == 422
    assert result["reason_code"] == "IDENTITY_PREFIX_REGISTRY_REF_ONLY_REQUIRED"
    assert "SYNTHETIC-PRIVATE-VALUE" not in json.dumps(result)


def test_caddy_candidate_clears_external_headers_and_copies_only_allowlist():
    source = CADDY_CANDIDATE_PATH.read_text(encoding="utf-8")
    clear_end = source.index("forward_auth")
    copy_line = next(
        line.strip() for line in source.splitlines() if "copy_headers" in line
    )
    copied = set(copy_line.split()[1:])
    assert copied == {HEADER_BY_FIELD["identity_ref"]}
    for header in PROJECTION_HEADER_NAMES + (BOUNDARY_HEADER,):
        assert f"request_header -{header}" in source[:clear_end]
    assert (
        f'request_header {BOUNDARY_HEADER} "{TRUSTED_BOUNDARY_VALUE}"' in source
    )
    assert source.startswith("# SOURCE_CANDIDATE_ONLY")
    assert "copy_headers *" not in source


def test_projection_artifacts_are_in_the_shared_release_inventory():
    from tools.total_field.w7tp_intent_field_suite.cli import _release_files

    paths = {path.relative_to(ROOT).as_posix() for path in _release_files()}
    assert {
        "tools/total_field/w7tp_intent_field_suite/identity_projection.py",
        "schemas/field/w7tp_identity_projection.schema.json",
        "tests/test_w7tp_identity_projection_landing.py",
        "deploy/caddy/w7tp-odoo-identity-projection.caddy",
    } <= paths
