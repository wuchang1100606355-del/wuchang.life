#!/usr/bin/env python3
"""Focused source-only acceptance for the P4 channel/scene/POS/node binding."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.three_major_scene_product_candidate import (  # noqa: E402
    build_member_sovereign_scene_binding_candidate,
)
from tools.total_field.wuchang_three_org_container_scene_bridge import (  # noqa: E402
    bind_taiji04_local_entry_to_founder_scene,
    build_p4_node_carrier_binding_candidate,
)
from tools.w7tp_pos_p2_candidate_projection import (  # noqa: E402
    build_member_bound_pos_dry_run_candidate,
)


NOW = 2_000_001_000
GOOGLE_SERVICE = (
    ROOT
    / "Taiji_Odoo/addons/wuchang_google_member_login/services/account_linking.py"
)
LINE_SERVICE = (
    ROOT
    / "Taiji_Odoo/addons/wuchang_line_login/services/profile_minimization.py"
)
WEBHOOK_SERVICE = (
    ROOT
    / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/"
    "line_official_account_webhook.py"
)


def _load_source_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


google = _load_source_module("p4_google_account_linking", GOOGLE_SERVICE)
line = _load_source_module("p4_line_profile_minimization", LINE_SERVICE)
line_webhook = _load_source_module("p4_line_webhook", WEBHOOK_SERVICE)


def _ref(namespace: str, label: str) -> str:
    return (
        f"{namespace}_ref:sha256:"
        + hashlib.sha256(label.encode("utf-8")).hexdigest()
    )


def _p3(*, founder: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    scope_refs = [_ref("scope", "member-scene")]
    root_ref = _ref("identity_root", "root")
    role_seat = {
        "role_refs": [_ref("role", "founder" if founder else "member")],
        "seat_leases": [],
    }
    if founder:
        role_seat["seat_leases"] = [
            {
                "seat_class": "FOUNDER_DEVELOPER",
                "identity_root_ref": root_ref,
                "root_generation": 4,
                "revocation_epoch": 7,
                "issued_at_epoch": NOW - 60,
                "expires_at_epoch": NOW + 240,
            }
        ]
    request = {
        "request_mode": "ACTION_REQUEST",
        "member_ref": _ref("member", "member"),
        "identity_root_ref": root_ref,
        "root_generation": 4,
        "revocation_epoch": 7,
        "session": {
            "session_ref": _ref("session", "session"),
            "scope_refs": scope_refs,
            "effect_class": "E2_CANDIDATE",
            "device_ref": _ref("device", "device"),
            "channel_ref": _ref("channel", "google"),
            "role_seat_snapshot": role_seat,
        },
        "scene": {
            "scene_ref": _ref("scene", "scene"),
            "scope_refs": scope_refs,
            "effect_class": "E2_CANDIDATE",
        },
        "action": {
            "action_hash": hashlib.sha256(b"p4-action").hexdigest(),
            "scope_refs": scope_refs,
            "effect_class": "E2_CANDIDATE",
        },
    }
    gate_material = {
        "identity_root_ref": request["identity_root_ref"],
        "root_generation": request["root_generation"],
        "revocation_epoch": request["revocation_epoch"],
        "session_ref": request["session"]["session_ref"],
        "scene_ref": request["scene"]["scene_ref"],
        "action_hash": request["action"]["action_hash"],
        "scope_refs": scope_refs,
        "effect_class": request["action"]["effect_class"],
    }
    gate_hash = hashlib.sha256(
        json.dumps(
            gate_material,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    gate = {
        "state": "PASS",
        "gate_ref": f"member_action_gate_ref:sha256:{gate_hash}",
        "gate_material": gate_material,
    }
    return request, gate


def _channel(member_ref: str) -> dict[str, Any]:
    return {
        "verifier_result": "PASS",
        "member_ref": member_ref,
        "verified_channel_binding_ref": _ref(
            "verified_channel_binding", "google-member"
        ),
    }


def _scene_candidate(
    *,
    request: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
    channel: dict[str, Any] | None = None,
    founder_scene: bool = False,
    existing_device_nodes: dict[str, str] | None = None,
    carrier_kind: str = "LAN",
    carrier_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p3_request, p3_gate = _p3(founder=founder_scene)
    p3_request = request or p3_request
    p3_gate = gate or p3_gate
    return build_member_sovereign_scene_binding_candidate(
        p3_request=p3_request,
        p3_gate=p3_gate,
        verified_channel_binding=channel or _channel(p3_request["member_ref"]),
        scene="merchant",
        capability_ref=_ref("capability", "cafe-pos"),
        node_ref=_ref("node", "device-node"),
        d3_coordinate_ref=_ref(
            "d3_coordinate",
            "lan" if carrier_kind == "LAN" else "vpn",
        ),
        carrier_kind=carrier_kind,
        carrier_ref=_ref("carrier", carrier_kind.casefold()),
        existing_device_nodes=existing_device_nodes,
        carrier_metadata=carrier_metadata,
        founder_scene=founder_scene,
        current_epoch=NOW,
    )


class MemberChannelScenePosNodeBindingTests(unittest.TestCase):
    def _google_callback(self, **overrides: Any) -> dict[str, str]:
        values = {
            "expected_state": "state",
            "received_state": "state",
            "expected_nonce": "nonce",
            "token_claims": {
                "nonce": "nonce",
                "aud": ["google-client"],
                "sub": "google-subject",
            },
            "expected_audience": "google-client",
            "authenticated_subject": "google-subject",
            "callback_url": google.CANONICAL_CALLBACK_URL,
            "issued_at_epoch": NOW - 30,
            "current_epoch": NOW,
            "replay_state": "SESSION_STATE_CONSUMED_ONCE",
        }
        values.update(overrides)
        return google.strict_channel_callback_security_decision(**values)

    def _line_callback(self, **overrides: Any) -> dict[str, str]:
        values = {
            "expected_state": "state",
            "received_state": "state",
            "expected_nonce": "nonce",
            "token_claims": {
                "nonce": "nonce",
                "aud": "line-channel",
                "sub": "line-subject",
            },
            "expected_audience": "line-channel",
            "authenticated_subject": "line-subject",
            "callback_url": line.CANONICAL_CALLBACK_URL,
            "issued_at_epoch": NOW - 30,
            "current_epoch": NOW,
            "replay_state": "SESSION_STATE_CONSUMED_ONCE",
        }
        values.update(overrides)
        return line.strict_channel_callback_security_decision(**values)

    def test_google_and_line_strict_callbacks_pass(self) -> None:
        self.assertEqual(self._google_callback()["decision"], "PASS")
        self.assertEqual(self._line_callback()["decision"], "PASS")

    def test_forged_callback_state_and_authenticated_subject_hold(self) -> None:
        cases = (
            self._google_callback(received_state="forged"),
            self._google_callback(authenticated_subject="other-subject"),
            self._line_callback(received_state="forged"),
            self._line_callback(authenticated_subject="other-subject"),
        )
        self.assertTrue(all(item["decision"] == "DENY" for item in cases))

    def test_nonce_replay_and_ttl_hold(self) -> None:
        cases = (
            self._google_callback(replay_state="REPLAY"),
            self._google_callback(issued_at_epoch=NOW - 301),
            self._line_callback(replay_state="REPLAY"),
            self._line_callback(issued_at_epoch=NOW - 301),
        )
        self.assertTrue(all(item["decision"] == "DENY" for item in cases))

    def test_audience_mismatch_holds(self) -> None:
        self.assertEqual(
            self._google_callback(expected_audience="other")["reason"],
            "AUDIENCE_MISMATCH",
        )
        self.assertEqual(
            self._line_callback(expected_audience="other")["reason"],
            "AUDIENCE_MISMATCH",
        )

    def test_raw_provider_profile_is_minimized_to_hashes(self) -> None:
        raw_profile = {
            "userId": "line-raw-subject",
            "displayName": "raw display value",
            "pictureUrl": "https://example.invalid/raw",
        }
        record = line.minimized_link_record(
            raw_profile,
            {
                "local_subject_reference": _ref("subject", "local"),
                "identity_prefix_ref": _ref("identity_prefix", "prefix"),
                "link_state": "PROVIDER_LINK_FOUND",
                "consent_reference": _ref("consent", "consent"),
                "verified_channel_binding_ref": _ref(
                    "verified_channel_binding", "line"
                ),
                "member_ref": _ref("member", "member"),
                "verifier_result": "PASS",
            },
            "2033-05-18T03:50:00+00:00",
        )
        serialized = json.dumps(record, ensure_ascii=False)
        self.assertNotIn(raw_profile["userId"], serialized)
        self.assertNotIn(raw_profile["displayName"], serialized)
        self.assertNotIn("pictureUrl", serialized)

    def test_provider_output_has_no_root_role_seat_or_consent_authority(self) -> None:
        record = line.minimized_link_record(
            {"userId": "line-subject"},
            {
                "link_state": "LINKING_PENDING",
                "verifier_result": "HOLD",
            },
            "2033-05-18T03:50:00+00:00",
        )
        forbidden = {
            "identity_root_ref",
            "root_generation",
            "revocation_epoch",
            "role_ref",
            "seat_ref",
            "permission_ref",
        }
        self.assertFalse(forbidden & set(record))

    def test_scene_and_schema_pass_from_p3_and_channel(self) -> None:
        scene = _scene_candidate()
        self.assertEqual(scene["state"], "PASS_SCENE_BINDING_CANDIDATE")
        schema = json.loads(
            (
                ROOT
                / "schemas/field/"
                "w7tp_three_major_scene_packet_candidate_v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": "#/$defs/p4MemberSceneBinding",
                "$defs": schema["$defs"],
            }
        )
        self.assertEqual(list(validator.iter_errors(scene)), [])

    def test_cross_member_scene_and_scope_expansion_hold(self) -> None:
        request, gate = _p3()
        cross_member = _channel(_ref("member", "other"))
        self.assertEqual(
            _scene_candidate(
                request=request,
                gate=gate,
                channel=cross_member,
            )["state"],
            "HOLD_CROSS_MEMBER_CHANNEL_BINDING",
        )
        expanded = copy.deepcopy(request)
        expanded["session"]["scope_refs"].append(_ref("scope", "expanded"))
        self.assertTrue(
            _scene_candidate(request=expanded, gate=gate)["state"].startswith(
                "HOLD_"
            )
        )

    def test_one_device_one_node_and_lan_vpn_coordinates(self) -> None:
        request, _ = _p3()
        device_ref = request["session"]["device_ref"]
        node_ref = _ref("node", "device-node")
        lan = _scene_candidate(existing_device_nodes={device_ref: node_ref})
        vpn = _scene_candidate(
            existing_device_nodes={device_ref: node_ref},
            carrier_kind="VPN",
        )
        self.assertEqual(lan["transport_priority"], "LAN_PRIMARY")
        self.assertEqual(vpn["transport_priority"], "VPN_FALLBACK")
        duplicate = _scene_candidate(
            existing_device_nodes={
                device_ref: _ref("node", "other-node")
            }
        )
        self.assertEqual(duplicate["state"], "HOLD_DUPLICATE_NODE_REF")

    def test_carrier_cannot_claim_protocol_or_mount_device(self) -> None:
        for metadata in (
            {"generative_transmission": True},
            {"whole_device_mount": True},
            {"mount_path": "/device"},
        ):
            with self.subTest(metadata=metadata):
                result = _scene_candidate(carrier_metadata=metadata)
                self.assertEqual(
                    result["state"],
                    "BLOCK_CARRIER_PROTOCOL_OR_MOUNT_ESCALATION",
                )

    def test_founder_scene_requires_same_root_short_lease(self) -> None:
        founder = _scene_candidate(founder_scene=True)
        self.assertEqual(founder["state"], "PASS_SCENE_BINDING_CANDIDATE")
        self.assertTrue(
            founder["founder_role_seat_lease_ref"].startswith(
                "role_seat_lease_ref:sha256:"
            )
        )
        request, gate = _p3(founder=True)
        request["session"]["role_seat_snapshot"]["seat_leases"][0][
            "identity_root_ref"
        ] = _ref("identity_root", "other")
        self.assertEqual(
            _scene_candidate(
                request=request,
                gate=gate,
                founder_scene=True,
            )["state"],
            "HOLD_FOUNDER_ROLE_SEAT_LEASE_REQUIRED",
        )

    def test_legacy_founder_bridge_cannot_bypass_p4_lease(self) -> None:
        result = bind_taiji04_local_entry_to_founder_scene(
            intent_text="fixture",
            input_mode="text",
            developer_session_request={},
            role_table={},
            current_epoch=NOW,
            founder_identity_request={},
            sealed_founder_root=None,
            total_field_preflight_receipt={},
            lawful_scope_confirmed=True,
        )
        self.assertEqual(
            result["STATE"],
            "HOLD_P4_MEMBER_ROOT_FOUNDER_LEASE_REQUIRED",
        )

    def test_pos_is_reference_only_dry_run(self) -> None:
        scene = _scene_candidate()
        pos = build_member_bound_pos_dry_run_candidate(
            scene,
            {"pos_intent_ref": _ref("pos_intent", "dry-run")},
        )
        self.assertEqual(pos["state"], "PASS_POS_DRY_RUN_CANDIDATE")
        for field in (
            "formal_db_write",
            "formal_pos_write",
            "order_created",
            "payment_capture",
            "inventory_write",
            "price_write",
            "member_data_write",
            "runtime_released",
        ):
            self.assertFalse(pos[field])

    def test_pos_write_fields_block(self) -> None:
        scene = _scene_candidate()
        for request in (
            {"pos_intent_ref": _ref("pos_intent", "x"), "lines": []},
            {"pos_intent_ref": _ref("pos_intent", "x"), "payment": {}},
            {"pos_intent_ref": _ref("pos_intent", "x"), "unit_price": 1},
        ):
            with self.subTest(request=request):
                self.assertEqual(
                    build_member_bound_pos_dry_run_candidate(
                        scene,
                        request,
                    )["state"],
                    "BLOCK_POS_WRITE_FIELD_FORBIDDEN",
                )

    def test_public_entry_is_canonical_local_only_and_orphans_removed(self) -> None:
        login_xml = (
            ROOT
            / "Taiji_Odoo/addons/wuchang_member_registration/views/"
            "login_templates.xml"
        )
        etree.parse(str(login_xml))
        public_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                login_xml,
                ROOT
                / "Taiji_Odoo/addons/wuchang_member_registration/"
                "controllers/main.py",
                ROOT
                / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/"
                "controllers/main.py",
            )
        )
        self.assertIn('href="/web/signup"', public_sources)
        self.assertNotIn('href="/google/member/login"', public_sources)
        self.assertNotIn('href="/line/login"', public_sources)
        self.assertNotIn("/wuchang/google/member/recruitment", public_sources)

    def test_body_member_ref_and_pos_writes_are_rejected_in_controllers(self) -> None:
        cafe = (
            ROOT
            / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
        ).read_text(encoding="utf-8")
        pos = (
            ROOT
            / "Taiji_Odoo/addons/wuchang_core/controllers/pos_mvp_api.py"
        ).read_text(encoding="utf-8")
        self.assertIn("HOLD_BODY_MEMBER_REF_FORBIDDEN", cafe)
        self.assertNotIn(".sudo().create(", cafe)
        self.assertNotIn(".sudo().write(", cafe)
        self.assertIn("BLOCK_POS_BODY_AUTHORITY_OR_WRITE_FIELD", pos)
        self.assertNotRegex(pos, re.compile(r"\.create\s*\("))
        self.assertNotRegex(pos, re.compile(r"\.write\s*\("))

    def test_line_official_account_remains_hold_without_member_session(self) -> None:
        candidate = line_webhook.build_line_official_account_webhook_candidate(
            webhook_payload={
                "events": [
                    {
                        "type": "message",
                        "timestamp": 1,
                        "source": {"type": "user", "userId": "raw-subject"},
                        "message": {"type": "text", "text": "candidate"},
                    }
                ]
            },
            headers={"x-line-signature": "SIGNATURE_REF_SAFE"},
            verification={
                "verified": True,
                "signature_verification_ref": "SIGNATURE_VERIFICATION_REF_SAFE",
                "channel_secret_ref": "CHANNEL_SECRET_REF_SAFE",
            },
        )
        binding = candidate["verified_channel_binding"]
        self.assertEqual(
            binding["state"],
            "HOLD_NOT_AUTHENTICATED_MEMBER_SESSION",
        )
        self.assertFalse(binding["root_issued"])
        self.assertFalse(binding["permission_issued"])


if __name__ == "__main__":
    unittest.main()
