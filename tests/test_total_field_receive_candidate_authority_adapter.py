from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = CANDIDATE_ROOT / "tools/total_field_receive_candidate_authority_adapter.py"
REPO_ROOT = Path(os.environ["W7TP_REPO_ROOT"]).resolve()
RESOLVER_PATH = Path(os.environ["W7TP_RESOLVER_PATH"]).resolve()
OWNER_PATH = Path(os.environ["W7TP_OWNER_PATH"]).resolve()

adapter = load_module("candidate_authority_adapter", ADAPTER_PATH)
resolver = load_module("candidate_authority_resolver", RESOLVER_PATH)
owner = load_module("current_total_field_dynamic_context", OWNER_PATH)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakePersistentLedger:
    persistent = True

    def __init__(self) -> None:
        self.used: set[str] = set()

    def mark_used_or_replay(
        self,
        nonce: str,
        packet_hash: str,
        now_epoch: float,
        ttl_seconds: int,
    ) -> bool:
        del packet_hash, now_epoch, ttl_seconds
        if nonce in self.used:
            return False
        self.used.add(nonce)
        return True


class FakeVolatileLedger(FakePersistentLedger):
    persistent = False


class FakeTrustedVerifier:
    trusted_runtime_verifier = True

    def __init__(self, *, allow: bool = True) -> None:
        self.allow = allow

    def verify(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        del verifier_ref
        return self.allow and signature == f"sig:{payload_sha256}"


class OwnerRecorder:
    def __init__(
        self,
        callback: Callable[[Mapping[str, Any], Mapping[str, Any] | None, Any], Any]
        | None = None,
    ) -> None:
        self.callback = callback or owner.receive_candidate
        self.calls = 0

    def __call__(
        self,
        candidate_packet: Mapping[str, Any],
        dynamic_context_packet: Mapping[str, Any] | None,
        authority_ref: Any,
    ) -> Any:
        self.calls += 1
        return self.callback(
            candidate_packet,
            dynamic_context_packet,
            authority_ref,
        )


class ResolverReceiveCandidateIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifacts = self.root / resolver.ARTIFACT_ROOT_REL
        self.artifacts.mkdir(parents=True)
        self.pointer_path = self.root / resolver.ACTIVE_POINTER_REL
        self.pointer_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = FakePersistentLedger()
        self.verifier = FakeTrustedVerifier()
        self.trusted = {"verifier_ref:total_field_runtime_v1"}
        self.owner_recorder = OwnerRecorder()
        self._build_valid_chain()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _utc(value: datetime) -> str:
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )

    @staticmethod
    def _bytes(value: Any) -> bytes:
        return (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

    def _write(self, path: Path, value: Any) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._bytes(value)
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def _read(self, path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(value, dict)
        return value

    def _sign_revocation(self, value: dict[str, Any]) -> dict[str, Any]:
        unsigned = dict(value)
        unsigned.pop("revocation_payload_sha256", None)
        unsigned.pop("signature", None)
        payload_hash = resolver.canonical_sha256(unsigned)
        value["revocation_payload_sha256"] = payload_hash
        value["signature"] = f"sig:{payload_hash}"
        return value

    def _resign_pointer(self, pointer: dict[str, Any]) -> None:
        unsigned = dict(pointer)
        unsigned.pop("authority_payload_sha256", None)
        payload_hash = resolver.canonical_sha256(unsigned)
        pointer["authority_payload_sha256"] = payload_hash
        self._write(self.pointer_path, pointer)
        signature = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_SIGNATURE_V1",
            "authority_id": pointer["authority_id"],
            "signed_payload_sha256": payload_hash,
            "verifier_ref": pointer["verifier_ref"],
            "signature": f"sig:{payload_hash}",
        }
        self._write(self.signature_path, signature)

    def _build_valid_chain(self) -> None:
        now = datetime.now(timezone.utc)
        self.authority_id = "authority_ref:founder_receive_candidate_v1"
        self.d8_path = self.artifacts / "d8_decision.json"
        self.owner_path = self.artifacts / "owner_seal.json"
        self.signature_path = self.artifacts / "authority_signature.json"
        self.revocation_path = self.artifacts / "revocation_list.json"

        d8 = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_D8_DECISION_V1",
            "authority_id": self.authority_id,
            "decision": "PASS",
            "reviewed_at": self._utc(now - timedelta(seconds=20)),
            "expires_at": self._utc(now + timedelta(seconds=240)),
        }
        owner_seal = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_OWNER_SEAL_V1",
            "authority_id": self.authority_id,
            "authorization": "FOUNDER_APPROVED_RECEIVE_CANDIDATE",
            "single_use_id": "single_use_ref:founder_authority_v1",
            "issued_at": self._utc(now - timedelta(seconds=20)),
            "expires_at": self._utc(now + timedelta(seconds=240)),
        }
        revocation = self._sign_revocation(
            {
                "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_REVOCATION_LIST_V1",
                "updated_at": self._utc(now - timedelta(seconds=10)),
                "verifier_ref": "verifier_ref:total_field_runtime_v1",
                "revoked_authority_ids": [],
            }
        )
        d8_sha = self._write(self.d8_path, d8)
        owner_sha = self._write(self.owner_path, owner_seal)
        self._write(self.revocation_path, revocation)

        pointer = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_V1",
            "authority_id": self.authority_id,
            "authority_version": "1.0.0",
            "state": "ACTIVE",
            "active": True,
            "founder_person_packet_ref": "person_packet_ref:founder_opaque_v1",
            "registered_device_ref": "device_ref:msi_registered_opaque_v1",
            "founder_capability_assignment_ref": (
                "capability_assignment_ref:receive_candidate_opaque_v1"
            ),
            "access_profile_ref": "access_profile_ref:founder_opaque_v1",
            "authority_scope": ["RECEIVE_CANDIDATE"],
            "issued_at": self._utc(now - timedelta(seconds=20)),
            "expires_at": self._utc(now + timedelta(seconds=240)),
            "nonce": "nonce_ref:sha256:" + "b" * 64,
            "d8_decision_ref": self.d8_path.relative_to(self.root).as_posix(),
            "d8_decision_sha256": d8_sha,
            "owner_seal_ref": self.owner_path.relative_to(self.root).as_posix(),
            "owner_seal_sha256": owner_sha,
            "signature_ref": self.signature_path.relative_to(self.root).as_posix(),
            "revocation_ref": self.revocation_path.relative_to(self.root).as_posix(),
            "verifier_ref": "verifier_ref:total_field_runtime_v1",
        }
        self._resign_pointer(pointer)

    def _candidate(self, **updates: Any) -> dict[str, Any]:
        value: dict[str, Any] = {
            "state": "CANDIDATE_ONLY",
            "execution_authorized": False,
        }
        value.update(updates)
        return value

    def _context(self, **updates: Any) -> dict[str, Any]:
        value: dict[str, Any] = {
            "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
            "source_bindings": [
                {"relative_path": "evidence.json", "sha256": "0" * 64}
            ],
            "context_items": [],
            "policy": {"evidence_only": True},
        }
        value.update(updates)
        value.pop("packet_sha256", None)
        value["packet_sha256"] = adapter.canonical_sha256(value)
        return value

    def _call(
        self,
        *,
        candidate: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
        ledger: Any | None = None,
        verifier: Any | None = None,
        owner_receiver: Any | None = None,
    ) -> dict[str, Any]:
        return adapter.receive_candidate_authority_bound(
            self._candidate() if candidate is None else candidate,
            self._context() if context is None else context,
            repo_root=self.root,
            nonce_ledger=self.ledger if ledger is None else ledger,
            signature_verifier=self.verifier if verifier is None else verifier,
            trusted_verifier_refs=self.trusted,
            authority_resolver=resolver.resolve_active_total_field_authority,
            owner_receive_candidate=(
                self.owner_recorder if owner_receiver is None else owner_receiver
            ),
        )

    def test_01_exact_resolver_and_owner_hash_bindings(self) -> None:
        self.assertEqual(adapter.RESOLVER_CANDIDATE_REL, RESOLVER_PATH.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(adapter.CURRENT_OWNER_REL, OWNER_PATH.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(file_sha256(RESOLVER_PATH), adapter.RESOLVER_CANDIDATE_SHA256)
        self.assertEqual(file_sha256(OWNER_PATH), adapter.CURRENT_OWNER_SHA256)

    def test_02_valid_chain_reaches_existing_owner_without_authority_escalation(self) -> None:
        result = self._call()
        self.assertEqual(result["state"], "ALLOW_CANDIDATE_ACCEPTED")
        self.assertEqual(result["authority_resolution_state"], resolver.PASS_AUTHORITY_STATE if hasattr(resolver, "PASS_AUTHORITY_STATE") else "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED")
        self.assertEqual(self.owner_recorder.calls, 1)
        self.assertFalse(result["candidate_authority"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["formal_decision_authority"])
        self.assertFalse(result["formal_seal_authority"])

    def test_03_missing_pointer_holds_without_calling_owner(self) -> None:
        self.pointer_path.unlink()
        result = self._call()
        self.assertEqual(result["state"], "HOLD_AUTHORITY_INCOMPLETE")
        self.assertEqual(self.owner_recorder.calls, 0)

    def test_04_candidate_cannot_supply_founder_or_d8_authority(self) -> None:
        candidate = self._candidate(
            founder_person_packet_ref="person_packet_ref:claimed",
            d8_decision_state="PASS",
        )
        result = self._call(candidate=candidate)
        self.assertEqual(result["state"], "HOLD_EVIDENCE_INCOMPLETE")
        self.assertEqual(self.owner_recorder.calls, 0)
        self.assertEqual(self.ledger.used, set())

    def test_05_invalid_context_does_not_consume_authority_nonce(self) -> None:
        invalid = self._context()
        invalid["packet_sha256"] = "f" * 64
        first = self._call(context=invalid)
        second = self._call()
        self.assertEqual(first["state"], "HOLD_EVIDENCE_INCOMPLETE")
        self.assertEqual(second["state"], "ALLOW_CANDIDATE_ACCEPTED")
        self.assertEqual(self.owner_recorder.calls, 1)

    def test_06_process_local_nonce_ledger_holds_before_owner(self) -> None:
        result = self._call(ledger=FakeVolatileLedger())
        self.assertEqual(result["state"], "HOLD_NONCE_LEDGER_NOT_PERSISTENT")
        self.assertEqual(self.owner_recorder.calls, 0)

    def test_07_d8_hold_never_reaches_owner(self) -> None:
        d8 = self._read(self.d8_path)
        d8["decision"] = "HOLD"
        pointer = self._read(self.pointer_path)
        pointer["d8_decision_sha256"] = self._write(self.d8_path, d8)
        self._resign_pointer(pointer)
        result = self._call()
        self.assertEqual(result["state"], "HOLD_D8_AUTHORITY_NOT_APPROVED")
        self.assertEqual(self.owner_recorder.calls, 0)

    def test_08_invalid_owner_seal_never_reaches_owner(self) -> None:
        seal = self._read(self.owner_path)
        seal["authorization"] = "CANDIDATE_SELF_APPROVED"
        pointer = self._read(self.pointer_path)
        pointer["owner_seal_sha256"] = self._write(self.owner_path, seal)
        self._resign_pointer(pointer)
        result = self._call()
        self.assertEqual(result["state"], "BLOCK_OWNER_SEAL_INVALID")
        self.assertEqual(self.owner_recorder.calls, 0)

    def test_09_signature_failure_never_reaches_owner(self) -> None:
        result = self._call(verifier=FakeTrustedVerifier(allow=False))
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_SIGNATURE_INVALID")
        self.assertEqual(self.owner_recorder.calls, 0)

    def test_10_revoked_authority_never_reaches_owner(self) -> None:
        revocation = self._read(self.revocation_path)
        revocation["revoked_authority_ids"] = [self.authority_id]
        self._write(self.revocation_path, self._sign_revocation(revocation))
        result = self._call()
        self.assertEqual(result["state"], "BLOCK_AUTHORITY_REVOKED")
        self.assertEqual(self.owner_recorder.calls, 0)

    def test_11_nonce_replay_blocks_second_owner_call(self) -> None:
        first = self._call()
        second = self._call()
        self.assertEqual(first["state"], "ALLOW_CANDIDATE_ACCEPTED")
        self.assertEqual(second["state"], "BLOCK_AUTHORITY_REPLAY")
        self.assertEqual(self.owner_recorder.calls, 1)

    def test_12_candidate_execution_claim_is_rejected_before_resolution(self) -> None:
        result = self._call(candidate=self._candidate(execution_authorized=True))
        self.assertEqual(result["state"], "HOLD_EVIDENCE_INCOMPLETE")
        self.assertEqual(self.owner_recorder.calls, 0)
        self.assertEqual(self.ledger.used, set())

    def test_13_breakpoint_deny_does_not_consume_nonce(self) -> None:
        denied = self._call(candidate=self._candidate(breakpoint_disposition="DENY"))
        accepted = self._call()
        self.assertEqual(denied["state"], "BLOCK_BREAKPOINT_OR_POLICY")
        self.assertEqual(accepted["state"], "ALLOW_CANDIDATE_ACCEPTED")
        self.assertEqual(self.owner_recorder.calls, 1)

    def test_14_owner_boundary_escalation_is_blocked(self) -> None:
        def unsafe_owner(*args: Any, **kwargs: Any) -> dict[str, Any]:
            del args, kwargs
            return {
                "state": "ALLOW_CANDIDATE_ACCEPTED",
                "candidate_authority": True,
                "execution_authorized": True,
            }

        result = self._call(owner_receiver=unsafe_owner)
        self.assertEqual(result["state"], "BLOCK_OWNER_BOUNDARY_VIOLATION")
        self.assertFalse(result["candidate_authority"])
        self.assertFalse(result["execution_authorized"])

    def test_15_owner_non_mapping_result_is_blocked(self) -> None:
        result = self._call(owner_receiver=lambda *args, **kwargs: None)
        self.assertEqual(result["state"], "BLOCK_OWNER_RECEIVER_INVALID")
        self.assertFalse(result["candidate_authority"])
        self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
