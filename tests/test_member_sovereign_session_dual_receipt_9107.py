#!/usr/bin/env python3
"""Focused source-only tests for the P3 member action gateway candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.xiaoj_member_bound_session_candidate import (  # noqa: E402
    canonical_sha256,
    evaluate_member_action_session,
)
from tools.total_field_candidate_gateway import (  # noqa: E402
    TotalFieldGatewayError,
    receive_candidate,
)
from tools.w7tp_secondary_cloud_packet_ramp import (  # noqa: E402
    gate_secondary_cloud_action_request,
)
from tools.xiaoj_candidate_adapter import (  # noqa: E402
    DualLLMGovernedNLIOCoordinator,
)


NOW = 2_000_000_100


def _ref(kind: str, label: str) -> str:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    return f"{kind}_ref:sha256:{digest}"


def _seal(value: Mapping[str, Any], ref_field: str, prefix: str) -> str:
    material = {key: item for key, item in value.items() if key != ref_field}
    return f"{prefix}:sha256:{canonical_sha256(material)}"


class DurableNonceDouble:
    """Test-only durable-interface double; it performs no runtime write."""

    def __init__(self) -> None:
        self.seen: set[tuple[str, str]] = set()
        self.calls = 0

    def consume_once(
        self,
        *,
        nonce_ref: str,
        binding_sha256: str,
        expires_at_epoch: int,
    ) -> Mapping[str, Any]:
        self.calls += 1
        key = (nonce_ref, binding_sha256)
        if key in self.seen:
            return {"state": "REPLAY"}
        self.seen.add(key)
        material = {
            "state": "CONSUMED",
            "nonce_ref": nonce_ref,
            "binding_sha256": binding_sha256,
            "expires_at_epoch": expires_at_epoch,
            "durable": True,
            "atomic": True,
        }
        return {
            **material,
            "evidence_ref": (
                "nonce_consumption_evidence_ref:sha256:"
                + canonical_sha256(material)
            ),
        }


class BooleanNonceDouble:
    def consume_once(self, **_: Any) -> bool:
        return True


class NeverProvider:
    def __init__(self) -> None:
        self.calls = 0

    def candidates_for(self, *_: Any) -> tuple[dict[str, Any], ...]:
        self.calls += 1
        raise AssertionError("provider called before the member gate")


class NeverBatchGateway:
    def receive_batch(self, *_: Any, **__: Any) -> tuple[dict[str, Any], ...]:
        raise AssertionError("generic gateway called before the member gate")


def _candidate(*, founder: bool = False, provider_count: int = 2) -> dict[str, Any]:
    root_ref = _ref("identity_root", "root")
    root_packet_ref = _ref("root_packet", "root-packet")
    role_ref = _ref("role", "founder" if founder else "member")
    seat_ref = _ref("seat", "founder" if founder else "member")
    lease = {
        "lease_ref": _ref("lease", "founder" if founder else "member"),
        "seat_ref": seat_ref,
        "seat_class": "FOUNDER_DEVELOPER" if founder else "MEMBER",
        "role_ref": role_ref,
        "identity_root_ref": root_ref,
        "root_generation": 4,
        "revocation_epoch": 7,
        "issued_at_epoch": NOW - 60,
        "expires_at_epoch": NOW + 300,
        "state": "ACTIVE_CANDIDATE",
    }
    snapshot_material = {"role_refs": [role_ref], "seat_leases": [lease]}
    snapshot_hash = canonical_sha256(snapshot_material)
    snapshot = {
        "snapshot_ref": f"role_seat_snapshot_ref:sha256:{snapshot_hash}",
        "snapshot_sha256": snapshot_hash,
        **snapshot_material,
    }
    scopes = [_ref("scope", "read-member-state")]
    session = {
        "session_ref": "",
        "identity_root_ref": root_ref,
        "root_packet_ref": root_packet_ref,
        "root_generation": 4,
        "revocation_epoch": 7,
        "issued_at_epoch": NOW - 30,
        "expires_at_epoch": NOW + 270,
        "ttl_seconds": 300,
        "scope_refs": scopes,
        "effect_class": "E2_CANDIDATE",
        "device_ref": _ref("device", "device"),
        "channel_ref": _ref("channel", "9107"),
        "nonce_ref": _ref("nonce", "nonce"),
        "nonce_binding_sha256": "0" * 64,
        "role_seat_snapshot": snapshot,
    }
    session_material = {
        key: value
        for key, value in session.items()
        if key not in {"session_ref", "nonce_binding_sha256"}
    }
    session["session_ref"] = (
        "session_ref:sha256:" + canonical_sha256(session_material)
    )
    scene = {
        "scene_ref": "",
        "identity_root_ref": root_ref,
        "root_generation": 4,
        "revocation_epoch": 7,
        "session_ref": session["session_ref"],
        "scope_refs": scopes,
        "effect_class": "E2_CANDIDATE",
    }
    scene["scene_ref"] = _seal(scene, "scene_ref", "scene_ref")
    action = {
        "action_hash": hashlib.sha256(b"p0-action").hexdigest(),
        "purpose_ref": _ref("purpose", "member-read"),
        "scope_refs": scopes,
        "effect_class": "E2_CANDIDATE",
    }
    nonce_material = {
        "nonce_ref": session["nonce_ref"],
        "identity_root_ref": root_ref,
        "root_generation": 4,
        "revocation_epoch": 7,
        "session_ref": session["session_ref"],
        "scene_ref": scene["scene_ref"],
        "action_hash": action["action_hash"],
        "scope_refs": scopes,
        "effect_class": action["effect_class"],
        "device_ref": session["device_ref"],
        "channel_ref": session["channel_ref"],
        "expires_at_epoch": session["expires_at_epoch"],
    }
    session["nonce_binding_sha256"] = canonical_sha256(nonce_material)
    member_receipt = {
        "receipt_ref": "",
        "receipt_state": "CONSENT",
        "authority": "member",
        "action_hash": action["action_hash"],
        "root_generation": 4,
        "session_ref": session["session_ref"],
        "scene_ref": scene["scene_ref"],
        "scope_refs": scopes,
        "effect_class": action["effect_class"],
    }
    member_receipt["receipt_ref"] = _seal(
        member_receipt, "receipt_ref", "member_consent_receipt_ref"
    )
    total_field_receipt = {
        "receipt_ref": "",
        "receipt_state": "PASS",
        "authority": "total_field_verifier",
        "action_hash": action["action_hash"],
        "root_generation": 4,
        "session_ref": session["session_ref"],
        "scene_ref": scene["scene_ref"],
        "scope_refs": scopes,
        "effect_class": action["effect_class"],
    }
    total_field_receipt["receipt_ref"] = _seal(
        total_field_receipt, "receipt_ref", "total_field_receipt_ref"
    )
    p1_candidate = {
        "root_chain_evidence": {
            "payload": {
                "roots": [
                    {
                        "identity_root_ref": root_ref,
                        "root_packet_ref": root_packet_ref,
                        "root_generation": 4,
                        "revocation_epoch": 7,
                    }
                ]
            }
        },
        "derived_packets_evidence": {
            "payload": {
                "session": {"payload": {"session_ref": session["session_ref"]}},
                "scene": {"payload": {"scene_ref": scene["scene_ref"]}},
                "role_seat": {
                    "payload": {"role_ref": role_ref, "seat_ref": seat_ref}
                },
            }
        },
        "dual_receipt_evidence": {"payload": {"action_binding": copy.deepcopy(action)}},
    }
    return {
        "schema_version": "w7tp.member-session-dual-receipt-9107.v1",
        "request_mode": "ACTION_REQUEST",
        "p1_identity_candidate": p1_candidate,
        "member_ref": _ref("member", "member"),
        "xiaoj_agent_ref": _ref("xiaoj_agent", "agent"),
        "identity_root_ref": root_ref,
        "root_packet_ref": root_packet_ref,
        "root_generation": 4,
        "revocation_epoch": 7,
        "session": session,
        "scene": scene,
        "action": action,
        "member_consent_receipt": member_receipt,
        "total_field_receipt": total_field_receipt,
        "provider_context": {
            "provider_count": provider_count,
            "provider_refs": [
                _ref("provider", str(index)) for index in range(provider_count)
            ],
            "candidate_authority": "none",
        },
        "verification_refs": [_ref("verification", "p1")],
    }


def _p1_pass(_: Mapping[str, Any]) -> Mapping[str, Any]:
    return {"state": "PASS", "reason_code": "PASS_P1"}


def _evaluate(
    candidate: Mapping[str, Any],
    *,
    nonce: Any | None = None,
    active_seat_leases: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    return evaluate_member_action_session(
        candidate,
        current_epoch=NOW,
        nonce_consumer=nonce or DurableNonceDouble(),
        p1_verifier=_p1_pass,
        active_seat_leases=active_seat_leases,
    )


class MemberSessionDualReceipt9107Tests(unittest.TestCase):
    def test_schema_and_complete_candidate_pass(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "schemas/xiaoj_member_bound_developer_seat_candidate.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        result = _evaluate(_candidate())
        self.assertEqual(result["state"], "PASS")
        self.assertTrue(result["generic_gateway_ready"])
        self.assertEqual(result["candidate_authority"], "none")
        self.assertFalse(result["runtime_released"])

    def test_p1_verifier_runs_before_nonce(self) -> None:
        nonce = DurableNonceDouble()
        result = evaluate_member_action_session(
            _candidate(),
            current_epoch=NOW,
            nonce_consumer=nonce,
            p1_verifier=lambda _: {
                "state": "HOLD",
                "reason_code": "HOLD_NOT_EVIDENCED",
            },
        )
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(nonce.calls, 0)

    def test_missing_either_receipt_holds(self) -> None:
        for field in ("member_consent_receipt", "total_field_receipt"):
            with self.subTest(field=field):
                candidate = _candidate()
                candidate.pop(field)
                self.assertEqual(_evaluate(candidate)["state"], "HOLD")

    def test_total_field_pass_cannot_substitute_member_consent(self) -> None:
        candidate = _candidate()
        candidate.pop("member_consent_receipt")
        self.assertEqual(
            _evaluate(candidate)["reason_code"], "HOLD_MEMBER_ACTION_SCHEMA_INVALID"
        )

    def test_action_hash_mismatch_holds(self) -> None:
        candidate = _candidate()
        receipt = candidate["total_field_receipt"]
        receipt["action_hash"] = hashlib.sha256(b"other-action").hexdigest()
        receipt["receipt_ref"] = _seal(
            receipt, "receipt_ref", "total_field_receipt_ref"
        )
        self.assertEqual(
            _evaluate(candidate)["reason_code"],
            "HOLD_DUAL_RECEIPT_BASIS_MISMATCH",
        )

    def test_cross_root_session_scene_hold(self) -> None:
        mutations = (
            ("session", "identity_root_ref", _ref("identity_root", "other")),
            ("scene", "identity_root_ref", _ref("identity_root", "other")),
            ("scene", "session_ref", _ref("session", "other")),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                candidate = _candidate()
                candidate[section][field] = value
                self.assertEqual(_evaluate(candidate)["state"], "HOLD")

    def test_scope_and_effect_expansion_hold(self) -> None:
        scope_candidate = _candidate()
        scope_candidate["scene"]["scope_refs"] = [
            *scope_candidate["scene"]["scope_refs"],
            _ref("scope", "expanded"),
        ]
        self.assertEqual(_evaluate(scope_candidate)["state"], "HOLD")
        effect_candidate = _candidate()
        effect_candidate["total_field_receipt"]["effect_class"] = "E5_HIGH_IMPACT"
        effect_candidate["total_field_receipt"]["receipt_ref"] = _seal(
            effect_candidate["total_field_receipt"],
            "receipt_ref",
            "total_field_receipt_ref",
        )
        self.assertEqual(
            _evaluate(effect_candidate)["reason_code"],
            "HOLD_EFFECT_CLASS_EXPANSION",
        )

    def test_stale_revocation_epoch_holds(self) -> None:
        candidate = _candidate()
        candidate["revocation_epoch"] = 6
        self.assertEqual(
            _evaluate(candidate)["reason_code"], "HOLD_P1_ROOT_BINDING_MISMATCH"
        )

    def test_nonce_replay_holds(self) -> None:
        candidate = _candidate()
        nonce = DurableNonceDouble()
        self.assertEqual(_evaluate(candidate, nonce=nonce)["state"], "PASS")
        self.assertEqual(
            _evaluate(candidate, nonce=nonce)["reason_code"], "HOLD_NONCE_REPLAY"
        )

    def test_boolean_nonce_claim_is_not_evidence(self) -> None:
        self.assertEqual(
            _evaluate(_candidate(), nonce=BooleanNonceDouble())["reason_code"],
            "HOLD_DURABLE_NONCE_EVIDENCE_REQUIRED",
        )

    def test_founder_lease_must_share_member_root(self) -> None:
        candidate = _candidate(founder=True)
        candidate["session"]["role_seat_snapshot"]["seat_leases"][0][
            "identity_root_ref"
        ] = _ref("identity_root", "static-founder-bypass")
        self.assertEqual(_evaluate(candidate)["state"], "HOLD")

    def test_double_active_seat_holds(self) -> None:
        candidate = _candidate(founder=True)
        active = copy.deepcopy(
            candidate["session"]["role_seat_snapshot"]["seat_leases"][0]
        )
        active["lease_ref"] = _ref("lease", "second-active-founder")
        self.assertEqual(
            _evaluate(candidate, active_seat_leases=(active,))["reason_code"],
            "HOLD_DOUBLE_ACTIVE_SEAT",
        )

    def test_dual_provider_action_cannot_bypass_receipts(self) -> None:
        local = NeverProvider()
        cloud = NeverProvider()
        coordinator = DualLLMGovernedNLIOCoordinator(
            local_provider=local,
            cloud_provider=cloud,
            domain_gateway=NeverBatchGateway(),
        )
        provider_candidate = ({"candidate_only": True},)
        with patch.object(
            DualLLMGovernedNLIOCoordinator,
            "_provider_candidates",
            side_effect=(
                (provider_candidate, None),
                (provider_candidate, None),
            ),
        ):
            result = coordinator.process(
                "opaque action",
                previous_values={},
                request_mode="ACTION_REQUEST",
            )
        self.assertEqual(result["STATE"], "HOLD_MEMBER_DUAL_RECEIPT_REQUIRED")
        self.assertEqual(local.calls + cloud.calls, 0)

    def test_provider_authority_injection_blocks_before_member_gate(self) -> None:
        injections = (
            {"decision": "ALLOW"},
            {"commit": False},
            {"tfid": "provider-forged"},
            {"total_field_hash": "0" * 64},
            {"canonical_pointer": _ref("canonical_pointer", "forged")},
            {"formal_execution_authority": False},
        )
        for provider_output in injections:
            with self.subTest(provider_output=provider_output):
                nonce = DurableNonceDouble()
                result = gate_secondary_cloud_action_request(
                    {
                        "request_mode": "ACTION_REQUEST",
                        "member_action_candidate": _candidate(),
                        "provider_outputs": [provider_output],
                    },
                    current_epoch=NOW,
                    nonce_consumer=nonce,
                    p1_verifier=_p1_pass,
                )
                self.assertEqual(result["state"], "BLOCK")
                self.assertEqual(nonce.calls, 0)

    def test_generic_gateway_rejects_early_commit(self) -> None:
        gate = {
            "state": "PASS",
            "reason_code": "PASS_P3",
            "gate_ref": _ref("member_action_gate", "gate"),
        }
        generic_result = {"commit_applied": True}
        with (
            patch(
                "tools.total_field_candidate_gateway."
                "evaluate_member_action_session",
                return_value=gate,
            ),
            patch(
                "tools.total_field_candidate_gateway._receive_runtime_candidate",
                return_value=generic_result,
            ),
        ):
            with self.assertRaises(TotalFieldGatewayError) as caught:
                receive_candidate(
                    {
                        "context": {"request_mode": "ACTION_REQUEST"},
                        "member_action_candidate": _candidate(),
                    },
                    previous_state={},
                    observation_domains={},
                    member_current_epoch=NOW,
                )
        self.assertEqual(caught.exception.reason_code, "HOLD_GENERIC_GATEWAY_EARLY_COMMIT")


if __name__ == "__main__":
    unittest.main()
