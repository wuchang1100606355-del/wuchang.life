from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = CANDIDATE_ROOT / "tools/total_field_authority_runtime_bindings.py"
RESOLVER_PATH = Path(os.environ["W7TP_RESOLVER_PATH"]).resolve()
ADAPTER_PATH = Path(os.environ["W7TP_ADAPTER_PATH"]).resolve()
OWNER_PREVIEW_PATH = Path(os.environ["W7TP_OWNER_PREVIEW_PATH"]).resolve()

runtime_bindings = load_module("candidate_authority_runtime_bindings", BINDINGS_PATH)
resolver = load_module("candidate_authority_resolver_for_runtime_bindings", RESOLVER_PATH)
adapter = load_module("candidate_authority_adapter_for_runtime_bindings", ADAPTER_PATH)
owner_preview = load_module("candidate_owner_preview_for_runtime_bindings", OWNER_PREVIEW_PATH)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeSignatureBackend:
    def __init__(self, *, allow: bool = True, raises: bool = False) -> None:
        self.allow = allow
        self.raises = raises
        self.calls: list[tuple[str, str, str]] = []

    def verify_detached(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        self.calls.append((verifier_ref, payload_sha256, signature))
        if self.raises:
            raise RuntimeError("backend failure")
        return self.allow and signature == f"sig:{payload_sha256}"


class OwnerRecorder:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.calls = 0

    def __call__(
        self,
        candidate_packet: Mapping[str, Any],
        dynamic_context_packet: Mapping[str, Any] | None,
        authority_ref: Any,
    ) -> Mapping[str, Any]:
        self.calls += 1
        return self.callback(candidate_packet, dynamic_context_packet, authority_ref)


class AuthorityRuntimeBindingsCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifacts = self.root / resolver.ARTIFACT_ROOT_REL
        self.artifacts.mkdir(parents=True)
        self.pointer_path = self.root / resolver.ACTIVE_POINTER_REL
        self.pointer_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path = (
            self.root
            / "runtime/total_field/runtime_state/authority_nonce_ledger.sqlite3"
        )
        self.backend = FakeSignatureBackend()
        self.trusted = {"verifier_ref:total_field_runtime_v1"}
        self.open_bindings: list[Any] = []
        self.original_owner_receive_candidate = owner_preview.receive_candidate
        self._build_valid_chain()
        self._install_module_aliases()

    def tearDown(self) -> None:
        owner_preview.receive_candidate = self.original_owner_receive_candidate
        for bindings in reversed(self.open_bindings):
            try:
                bindings.close()
            except Exception:
                pass
        self.temp.cleanup()

    def _install_module_aliases(self) -> None:
        sys.modules[
            owner_preview.ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVER_MODULE
        ] = resolver
        sys.modules[
            owner_preview.ACTIVE_TOTAL_FIELD_AUTHORITY_ADAPTER_MODULE
        ] = adapter

    def _bindings(
        self,
        *,
        backend: FakeSignatureBackend | None = None,
        ledger_path: Path | None = None,
    ):
        value = runtime_bindings.build_authority_runtime_bindings(
            ledger_path=self.ledger_path if ledger_path is None else ledger_path,
            signature_backend=self.backend if backend is None else backend,
            trusted_verifier_refs=self.trusted,
        )
        self.open_bindings.append(value)
        return value

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
        self.owner_seal_path = self.artifacts / "owner_seal.json"
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
        owner_sha = self._write(self.owner_seal_path, owner_seal)
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
            "nonce": "nonce_ref:sha256:" + "d" * 64,
            "d8_decision_ref": self.d8_path.relative_to(self.root).as_posix(),
            "d8_decision_sha256": d8_sha,
            "owner_seal_ref": self.owner_seal_path.relative_to(self.root).as_posix(),
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

    def _context(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
            "source_bindings": [
                {"relative_path": "evidence.json", "sha256": "0" * 64}
            ],
            "context_items": [],
            "policy": {"evidence_only": True},
        }
        value["packet_sha256"] = owner_preview.canonical_sha256(value)
        return value

    def test_01_exact_upstream_hash_bindings(self) -> None:
        self.assertEqual(file_sha256(BINDINGS_PATH), os.environ["W7TP_BINDINGS_SHA256"])
        self.assertEqual(file_sha256(RESOLVER_PATH), os.environ["W7TP_RESOLVER_SHA256"])
        self.assertEqual(file_sha256(ADAPTER_PATH), os.environ["W7TP_ADAPTER_SHA256"])
        self.assertEqual(
            file_sha256(OWNER_PREVIEW_PATH),
            os.environ["W7TP_OWNER_PREVIEW_SHA256"],
        )

    def test_02_first_nonce_use_is_persisted(self) -> None:
        bindings = self._bindings()
        accepted = bindings.nonce_ledger.mark_used_or_replay(
            "nonce_ref:sha256:" + "1" * 64,
            "2" * 64,
            1000.0,
            300,
        )
        self.assertTrue(accepted)
        self.assertEqual(bindings.nonce_ledger.entry_count(), 1)

    def test_03_same_process_nonce_replay_is_blocked(self) -> None:
        bindings = self._bindings()
        nonce = "nonce_ref:sha256:" + "3" * 64
        self.assertTrue(
            bindings.nonce_ledger.mark_used_or_replay(nonce, "4" * 64, 1000.0, 300)
        )
        self.assertFalse(
            bindings.nonce_ledger.mark_used_or_replay(nonce, "4" * 64, 1001.0, 300)
        )

    def test_04_restart_nonce_replay_is_blocked(self) -> None:
        first = self._bindings()
        nonce = "nonce_ref:sha256:" + "5" * 64
        self.assertTrue(
            first.nonce_ledger.mark_used_or_replay(nonce, "6" * 64, 1000.0, 300)
        )
        first.close()
        second = self._bindings()
        self.assertFalse(
            second.nonce_ledger.mark_used_or_replay(nonce, "6" * 64, 1001.0, 300)
        )
        self.assertEqual(second.nonce_ledger.entry_count(), 1)

    def test_05_two_connections_cannot_consume_same_nonce(self) -> None:
        first = self._bindings()
        second = self._bindings()
        nonce = "nonce_ref:sha256:" + "7" * 64
        self.assertTrue(
            first.nonce_ledger.mark_used_or_replay(nonce, "8" * 64, 1000.0, 300)
        )
        self.assertFalse(
            second.nonce_ledger.mark_used_or_replay(nonce, "8" * 64, 1000.0, 300)
        )

    def test_06_invalid_nonce_is_rejected_without_record(self) -> None:
        bindings = self._bindings()
        self.assertFalse(
            bindings.nonce_ledger.mark_used_or_replay(
                "raw-nonce", "9" * 64, 1000.0, 300
            )
        )
        self.assertEqual(bindings.nonce_ledger.entry_count(), 0)

    def test_07_invalid_packet_hash_is_rejected_without_record(self) -> None:
        bindings = self._bindings()
        self.assertFalse(
            bindings.nonce_ledger.mark_used_or_replay(
                "nonce_ref:sha256:" + "a" * 64,
                "not-a-hash",
                1000.0,
                300,
            )
        )
        self.assertEqual(bindings.nonce_ledger.entry_count(), 0)

    def test_08_invalid_ttl_is_rejected_without_record(self) -> None:
        bindings = self._bindings()
        nonce = "nonce_ref:sha256:" + "b" * 64
        self.assertFalse(
            bindings.nonce_ledger.mark_used_or_replay(nonce, "c" * 64, 1000.0, 0)
        )
        self.assertFalse(
            bindings.nonce_ledger.mark_used_or_replay(nonce, "c" * 64, 1000.0, 301)
        )
        self.assertEqual(bindings.nonce_ledger.entry_count(), 0)

    def test_09_ledger_database_permissions_are_private(self) -> None:
        bindings = self._bindings()
        mode = stat.S_IMODE(self.ledger_path.stat().st_mode)
        self.assertEqual(mode & 0o077, 0)
        self.assertTrue(bindings.nonce_ledger.persistent)
        self.assertFalse(bindings.nonce_ledger.secret_material_access)

    def test_10_trusted_verifier_accepts_injected_backend(self) -> None:
        bindings = self._bindings()
        payload_hash = "e" * 64
        self.assertTrue(
            bindings.signature_verifier.verify(
                verifier_ref="verifier_ref:total_field_runtime_v1",
                payload_sha256=payload_hash,
                signature=f"sig:{payload_hash}",
            )
        )
        self.assertEqual(len(self.backend.calls), 1)

    def test_11_untrusted_verifier_ref_fails_without_backend_call(self) -> None:
        bindings = self._bindings()
        self.assertFalse(
            bindings.signature_verifier.verify(
                verifier_ref="verifier_ref:untrusted_runtime",
                payload_sha256="f" * 64,
                signature="sig:" + "f" * 64,
            )
        )
        self.assertEqual(self.backend.calls, [])

    def test_12_malformed_signature_input_fails_without_backend_call(self) -> None:
        bindings = self._bindings()
        self.assertFalse(
            bindings.signature_verifier.verify(
                verifier_ref="verifier_ref:total_field_runtime_v1",
                payload_sha256="bad",
                signature="",
            )
        )
        self.assertEqual(self.backend.calls, [])

    def test_13_backend_denial_and_exception_fail_closed(self) -> None:
        denied_backend = FakeSignatureBackend(allow=False)
        denied = self._bindings(
            backend=denied_backend,
            ledger_path=self.root / "denied.sqlite3",
        )
        payload_hash = "1" * 64
        self.assertFalse(
            denied.signature_verifier.verify(
                verifier_ref="verifier_ref:total_field_runtime_v1",
                payload_sha256=payload_hash,
                signature=f"sig:{payload_hash}",
            )
        )

        raising_backend = FakeSignatureBackend(raises=True)
        raising = self._bindings(
            backend=raising_backend,
            ledger_path=self.root / "raising.sqlite3",
        )
        self.assertFalse(
            raising.signature_verifier.verify(
                verifier_ref="verifier_ref:total_field_runtime_v1",
                payload_sha256=payload_hash,
                signature=f"sig:{payload_hash}",
            )
        )

    def test_14_candidate_module_has_no_key_or_environment_reader(self) -> None:
        tree = ast.parse(BINDINGS_PATH.read_text(encoding="utf-8"))
        imported_names = {
            alias.name
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        called_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("os", imported_names)
        self.assertTrue({"open", "getenv"}.isdisjoint(called_names))
        self.assertTrue(
            {"read_text", "read_bytes", "open"}.isdisjoint(called_attributes)
        )
        self.assertFalse(
            runtime_bindings.TrustedSignatureVerifierBinding.secret_material_access
        )
        self.assertEqual(
            runtime_bindings.TrustedSignatureVerifierBinding.key_material_source,
            "INJECTED_BACKEND_ONLY",
        )

    def test_15_resolver_accepts_real_runtime_bindings(self) -> None:
        bindings = self._bindings()
        result = resolver.resolve_active_total_field_authority(
            "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
            repo_root=self.root,
            nonce_ledger=bindings.nonce_ledger,
            signature_verifier=bindings.signature_verifier,
            trusted_verifier_refs=bindings.trusted_verifier_refs,
        )
        self.assertEqual(
            result["state"],
            "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
        )
        self.assertTrue(result["authority_verified"])
        self.assertFalse(result["execution_authorized"])

    def test_16_resolver_replay_survives_binding_restart(self) -> None:
        first = self._bindings()
        accepted = resolver.resolve_active_total_field_authority(
            "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
            repo_root=self.root,
            nonce_ledger=first.nonce_ledger,
            signature_verifier=first.signature_verifier,
            trusted_verifier_refs=first.trusted_verifier_refs,
        )
        self.assertEqual(
            accepted["state"],
            "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
        )
        first.close()

        second = self._bindings()
        replay = resolver.resolve_active_total_field_authority(
            "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
            repo_root=self.root,
            nonce_ledger=second.nonce_ledger,
            signature_verifier=second.signature_verifier,
            trusted_verifier_refs=second.trusted_verifier_refs,
        )
        self.assertEqual(replay["state"], "BLOCK_AUTHORITY_REPLAY")

    def test_17_owner_preview_accepts_candidate_only_with_real_bindings(self) -> None:
        bindings = self._bindings()
        recorder = OwnerRecorder(owner_preview.receive_candidate)
        owner_preview.receive_candidate = recorder
        receiver = owner_preview.build_active_authority_receive_candidate(
            repo_root=self.root,
            nonce_ledger=bindings.nonce_ledger,
            signature_verifier=bindings.signature_verifier,
            trusted_verifier_refs=bindings.trusted_verifier_refs,
        )
        result = receiver(
            self._candidate(),
            self._context(),
            owner_preview.ACTIVE_TOTAL_FIELD_AUTHORITY_LOOKUP_REF,
        )
        self.assertEqual(result["state"], "ALLOW_CANDIDATE_ACCEPTED")
        self.assertEqual(recorder.calls, 1)
        self.assertFalse(result["candidate_authority"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["formal_decision_authority"])
        self.assertFalse(result["formal_seal_authority"])

    def test_18_d8_hold_never_reaches_owner_or_consumes_nonce(self) -> None:
        d8 = self._read(self.d8_path)
        d8["decision"] = "HOLD"
        pointer = self._read(self.pointer_path)
        pointer["d8_decision_sha256"] = self._write(self.d8_path, d8)
        self._resign_pointer(pointer)

        bindings = self._bindings()
        recorder = OwnerRecorder(owner_preview.receive_candidate)
        owner_preview.receive_candidate = recorder
        receiver = owner_preview.build_active_authority_receive_candidate(
            repo_root=self.root,
            nonce_ledger=bindings.nonce_ledger,
            signature_verifier=bindings.signature_verifier,
            trusted_verifier_refs=bindings.trusted_verifier_refs,
        )
        result = receiver(
            self._candidate(),
            self._context(),
            owner_preview.ACTIVE_TOTAL_FIELD_AUTHORITY_LOOKUP_REF,
        )
        self.assertEqual(result["state"], "HOLD_D8_AUTHORITY_NOT_APPROVED")
        self.assertEqual(recorder.calls, 0)
        self.assertEqual(bindings.nonce_ledger.entry_count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
