#!/usr/bin/env python3
"""Independent GST V2.1 candidate checks, confined to temporary synthetic roots.

This program never calls taiji01, imports a live resolver, reads a real grant,
or exercises the codec. Every positive result is functional fixture evidence,
not a formal authorization. Executor cases are added only against its reviewed
public test interface; helper-only results do not satisfy transaction acceptance.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
import marshal
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gst_v21_specification_contract as contract

EXECUTOR_CASES_READY = True


def put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)



def poison_timestamp_cache(source: Path) -> None:
    """Place a valid-header, poisonous pyc only inside a disposable fixture."""
    info = source.stat()
    bytecode = importlib.util.MAGIC_NUMBER + struct.pack(
        "<III", 0, int(info.st_mtime) & 0xFFFFFFFF, info.st_size & 0xFFFFFFFF)
    bytecode += marshal.dumps(compile(
        'raise RuntimeError("INDEPENDENT_SYNTHETIC_POISONED_CACHE_MUST_NOT_RUN")',
        str(source), "exec"))
    put(Path(importlib.util.cache_from_source(str(source))), bytecode)

class SyntheticCase:
    """A complete fixture assembled without the production bundle builder."""

    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="gst-v21-independent-")
        self.base = Path(self.temp.name)
        self.root = self.base / "synthetic-root"
        self.bundle = self.base / "synthetic-bundle"
        self.audit = self.base / "synthetic-audit"
        self.root.mkdir()
        self.bundle.mkdir()
        assert str(self.root) != contract.LIVE_ROOT
        put(self.root / "ISOLATED_TEST_ROOT", b"NO_FORMAL_AUTHORITY\n")
        self.source_bytes = {
            contract.SOURCE_SPEC: b"# SYNTHETIC GST V2.1 SPECIFICATION; NO AUTHORITY\n",
            contract.SOURCE_CODEC: b"# SYNTHETIC CODEC PLACEHOLDER; NEVER EXECUTED\n",
            contract.PARENT_POINTER: b'{"fixture":"parent-pointer"}\n',
            contract.PARENT_CONTRACT: b'{"fixture":"parent-contract"}\n',
            contract.AUTHORITY_POINTER: b'{"fixture":"authority-pointer"}\n',
            "tools/total_field_authority_resolver.py": b"# NO NATIVE RESOLVER IN FIXTURE\n",
            "core/capability_internalization.py": b"# NO NATIVE CONSUMER IN FIXTURE\n",
            "schemas/field/w7tp_capability_internalization_registry.schema.json":
                b'{"fixture":"registry-schema"}\n',
        }
        evidence_scope = {"tier_2": {"state": "REPORTED_EXTENSION_SOURCE_BINDING_PENDING"}}
        self.source_bytes[contract.PREVIOUS_REQUEST] = contract.canonical_bytes({
            "fixture": "SYNTHETIC_PREVIOUS_REQUEST_NOT_ORIGINAL",
            "evidence_scope": evidence_scope,
        }) + b"\n"
        self.source_bytes[contract.PREVIOUS_REVIEW] = b'{"fixture":"synthetic-review","held":true}\n'
        self.source_bytes[contract.PREVIOUS_DISPOSITION] = b'{"fixture":"synthetic-disposition","formal_effect_authorized":false}\n'
        for index in range(32):
            self.source_bytes[f"fixture/protected-source-{index:02d}.txt"] = (
                f"INDEPENDENT SYNTHETIC IMMUTABLE SOURCE {index}\n".encode())
        assert len(self.source_bytes) == 43
        for ref, data in self.source_bytes.items():
            put(self.root / ref, data)
        self.registry_before = {
            "canonical": False,
            "capabilities": [{
                "capability_id": contract.CAPABILITY_ID,
                "source_refs": ["fixture/original-source"],
                "d8_authority": {
                    "canonical": False, "provider_authority": False,
                    "final_decision": False, "requires_total_field_verify": True,
                },
                "d5_execution": {"mode": "CANDIDATE_ONLY", "direct_effect": False},
            }] + [{"capability_id": "INDEPENDENT_FIXTURE_" + str(i), "source_refs": []}
                  for i in range(7)],
        }
        before_raw = contract.canonical_bytes(self.registry_before) + b"\n"
        put(self.root / contract.REGISTRY, before_raw)
        put(self.bundle / "preimages/REGISTRY.json", before_raw)
        after_registry = copy.deepcopy(self.registry_before)
        after_registry["capabilities"][0]["source_refs"].append(contract.RECORD_TARGET)
        source_hashes = {ref: contract.sha256(raw) for ref, raw in self.source_bytes.items()}
        subject = {
            "source_ref": contract.SOURCE_SPEC,
            "source_sha256": source_hashes[contract.SOURCE_SPEC],
            "codec_ref": contract.SOURCE_CODEC,
            "codec_sha256": source_hashes[contract.SOURCE_CODEC],
            "scope": "SPECIFICATION_CANONICAL_IDENTITY_ONLY",
        }
        parent = {
            "canonical_id": "W7TP_8D_ADI_V2_3", "version": "2.3",
            "contract_ref": contract.PARENT_CONTRACT,
            "contract_sha256": source_hashes[contract.PARENT_CONTRACT],
            "pointer_ref": contract.PARENT_POINTER,
            "pointer_sha256": source_hashes[contract.PARENT_POINTER],
        }
        self.non_effects = {name: False for name in contract.NON_EFFECT_KEYS}
        record = {
            "schema": "GST_V21_SPECIFICATION_IDENTITY_RECORD_CANDIDATE/1.0",
            "record_state": "REQUIRES_VERIFIED_NATIVE_PROMOTION_RECEIPT",
            "specification_id": "ORIGIN_CELL_GST_V2_1",
            "definition_authority": "江政隆",
            "record_is_self_authorizing": False,
            "specification": subject, "parent_canonical": parent,
            "formal_validity": {
                "receipt_ref": contract.RECEIPT_TARGET,
                "rule": "EXACT_NATIVE_AUTHORIZATION_AND_POSTIMAGE_VERIFICATION_REQUIRED",
                "file_presence_is_authority": False,
            },
            "evidence_scope": evidence_scope, "non_effects": self.non_effects,
        }
        self.payloads = {
            contract.SPEC_TARGET: self.source_bytes[contract.SOURCE_SPEC],
            contract.RECORD_TARGET: contract.canonical_bytes(record) + b"\n",
            contract.REGISTRY: contract.canonical_bytes(after_registry) + b"\n",
        }
        writes = []
        for ref, raw in self.payloads.items():
            operation, payload_ref = contract.WRITE_SPEC[ref]
            put(self.bundle / payload_ref, raw)
            writes.append({
                "path": ref, "operation": operation, "payload_ref": payload_ref,
                "preimage_sha256": contract.sha256(before_raw) if ref == contract.REGISTRY else None,
                "postimage_sha256": contract.sha256(raw), "postimage_bytes": len(raw),
            })
        executors = {}
        for name in sorted(contract.EXECUTOR_FILES):
            path = HERE / name
            raw = path.read_bytes() if path.exists() else b"# ABSENT EXECUTOR; HELPER TEST ONLY\n"
            put(self.bundle / "candidate" / name, raw)
            executors[name] = contract.sha256(raw)
        order = b"# INDEPENDENT SYNTHETIC ORDER; NEVER A LIVE GRANT\n"
        put(self.bundle / "order.md", order)
        self.document = {
            "schema": contract.SCHEMA,
            "run_id": "INDEPENDENT_SYNTHETIC_TEST",
            "task_id": "GST_V21_INDEPENDENT_FUNCTIONAL_TEST",
            "lifecycle_state": "IMAGINED_CANDIDATE",
            "node": contract.NODE, "root": contract.LIVE_ROOT,
            "branch": "test/gst-v21-independent", "head": "1" * 40,
            "immutable_sources": source_hashes, "executor_bindings": executors,
            "static_writes": writes, "receipt_path": contract.RECEIPT_TARGET,
            "audit_base": contract.AUDIT_BASE,
            "authority": {
                "resolver_ref": "tools/total_field_authority_resolver.py#resolve_founder_signed_break_glass_effect",
                "effect_prefix": contract.EFFECT_PREFIX,
                "signed_grant_schema": "W7TP_FOUNDER_SOVEREIGN_BREAK_GLASS/1.0",
                "max_ttl_seconds": 300,
                "receipt_derived_after_authorization": True,
            },
            "derived_paths": {
                "operation_dir": "audit_base/<contract_raw_sha256>",
                "native_receipt_dir": "operation_dir/authority",
                "nonce_marker": "audit_base/replay/<sha256_raw_nonce>.json",
                "registry_stage": "configs/total_field/.gst-v21-<contract_raw_sha256>.registry-stage",
                "raw_nonce_or_signature_in_output": False,
                "formal_audit_paths_created_in_candidate_run": False,
            },
            "registry_delta": {
                "capability_id": contract.CAPABILITY_ID,
                "append_source_ref": contract.RECORD_TARGET,
                "preimage_payload_ref": "preimages/REGISTRY.json",
                "preimage_sha256": contract.sha256(before_raw),
                "all_other_fields_unchanged": True,
            },
            "parent_canonical": parent, "specification": subject,
            "evidence_scope": evidence_scope, "non_effects": self.non_effects,
            "receipt_derivation": {
                "after_native_authorization_only": True,
                "receipt_is_last_publication_step": True,
                "missing_receipt_is_hold": True,
                "fixed_postimage_hash_before_authorization": False,
                "authority_source": "EXISTING_TAIJI01_NATIVE_RESOLVER_ONLY",
                "caller_supplied_pass_is_authority": False,
                "simulation_can_claim_formal_authority": False,
            },
            "rollback": {
                "before_receipt": "RESTORE_ONLY_OWNED_MATCHING_POSTIMAGES_UNDER_EXACT_CAS",
                "registry_backup_ref": "preimages/REGISTRY.json",
                "preserve_native_audit_and_replay": True,
                "partial_failure_requires_explicit_recovery_record": True,
                "after_receipt": "NEW_EXACT_WITHDRAWAL_AUTHORITY_AND_APPEND_ONLY_HISTORY",
                "delete_historical_receipts": False,
            },
            "order_binding": {"ref": "order.md", "sha256": contract.sha256(order)},
        }
        # These are the published schema vocabulary, not behavior expectations.
        # Independent assertions below still check real bytes, rejection, and
        # absence of authority rather than copying function return values.
        self.document["derived_paths"] = copy.deepcopy(contract.DERIVED_PATH_RULES)
        self.document["receipt_derivation"] = copy.deepcopy(contract.RECEIPT_RULES)
        self.document["rollback"] = copy.deepcopy(contract.ROLLBACK_RULES)
        self.save()

    def save(self) -> None:
        put(self.bundle / "PROMOTION_CONTRACT.json",
            contract.canonical_bytes(self.document) + b"\n")

    def replace_payload(self, ref: str, raw: bytes) -> None:
        self.payloads[ref] = raw
        entry = next(item for item in self.document["static_writes"] if item["path"] == ref)
        entry["postimage_sha256"] = contract.sha256(raw)
        entry["postimage_bytes"] = len(raw)
        put(self.bundle / entry["payload_ref"], raw)
        self.save()

    def publish_static_only(self) -> None:
        for ref, raw in self.payloads.items():
            put(self.root / ref, raw)

    def snapshot(self) -> dict[str, str]:
        return {str(p.relative_to(self.root)): contract.sha256(p.read_bytes())
                for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}

    def close(self) -> None:
        self.temp.cleanup()


class IndependentHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = SyntheticCase()
        self.addCleanup(self.case.close)

    def assert_hold(self, operation, code: str) -> None:
        with self.assertRaises(contract.ContractError) as context:
            operation()
        self.assertEqual(context.exception.code, code)

    def test_preconditions_are_read_only_and_never_authority(self) -> None:
        before = self.case.snapshot()
        observed = contract.verify_preconditions(self.case.root, self.case.bundle)
        self.assertEqual(observed["state"], "PASS_CANDIDATE_PRECONDITIONS")
        for name in ("effect_authorized", "coordinate_authority_verified", "receipt_validated",
                     "writes_performed"):
            self.assertIs(observed[name], False)
        self.assertEqual(self.case.snapshot(), before)
        self.assertFalse(self.case.audit.exists())

    def test_postimages_without_native_receipt_still_cannot_authorize(self) -> None:
        self.case.publish_static_only()
        observed = contract.verify_preconditions(self.case.root, self.case.bundle, "POST")
        self.assertEqual(observed["state"], "PASS_STATIC_POSTIMAGES_ONLY")
        self.assertFalse(observed["receipt_exists"])
        self.assertFalse(observed["effect_authorized"])
        self.assertFalse(observed["receipt_validated"])

    def test_forged_receipt_presence_does_not_turn_static_pass_into_authority(self) -> None:
        self.case.publish_static_only()
        put(self.case.root / contract.RECEIPT_TARGET,
            b'{"state":"PASS","formal_effect_authorized":true}\n')
        observed = contract.verify_preconditions(self.case.root, self.case.bundle, "POST")
        self.assertTrue(observed["receipt_exists"])
        self.assertIs(observed["effect_authorized"], False)
        self.assertIs(observed["receipt_validated"], False)

    def test_source_drift_rejects_before_writes(self) -> None:
        put(self.case.root / contract.SOURCE_CODEC, b"# foreign codec version\n")
        before = self.case.snapshot()
        self.assert_hold(lambda: contract.verify_preconditions(self.case.root, self.case.bundle),
                         "HOLD_IMMUTABLE_SOURCE_DRIFT")
        self.assertEqual(self.case.snapshot(), before)

    def test_registry_preimage_drift_is_not_overwritten(self) -> None:
        foreign = b'{"foreign_registry":"must survive"}\n'
        put(self.case.root / contract.REGISTRY, foreign)
        self.assert_hold(lambda: contract.verify_preconditions(self.case.root, self.case.bundle),
                         "HOLD_STATIC_IMAGE_DRIFT")
        self.assertEqual((self.case.root / contract.REGISTRY).read_bytes(), foreign)

    def test_existing_create_target_is_collision_even_when_bytes_match(self) -> None:
        put(self.case.root / contract.SPEC_TARGET, self.case.payloads[contract.SPEC_TARGET])
        self.assert_hold(lambda: contract.verify_preconditions(self.case.root, self.case.bundle),
                         "HOLD_CREATE_TARGET_ALREADY_EXISTS")

    def test_symlink_write_target_preserves_outside_file(self) -> None:
        outside = self.case.base / "foreign"
        outside.write_bytes(b"foreign content")
        target = self.case.root / contract.SPEC_TARGET
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(outside)
        self.assert_hold(lambda: contract.verify_preconditions(self.case.root, self.case.bundle),
                         "HOLD_PATH_SYMLINK")
        self.assertEqual(outside.read_bytes(), b"foreign content")

    def test_hardlinked_source_rejected(self) -> None:
        os.link(self.case.root / contract.SOURCE_SPEC, self.case.base / "source-hardlink")
        self.assert_hold(lambda: contract.verify_preconditions(self.case.root, self.case.bundle),
                         "HOLD_PATH_HARDLINK")

    def test_frozen_order_drift_rejected(self) -> None:
        put(self.case.bundle / "order.md", b"changed synthetic order")
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle), "HOLD_FROZEN_ORDER_DRIFT")

    def test_executor_source_drift_rejected_without_import(self) -> None:
        put(self.case.bundle / "candidate/promote_origin_cell_gst_v21_specification.py",
            b'raise RuntimeError("this code must never execute")\n')
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle), "HOLD_EXECUTOR_HASH_DRIFT")

    def test_self_authorizing_record_rejected_even_with_rebound_payload_hash(self) -> None:
        record = json.loads(self.case.payloads[contract.RECORD_TARGET])
        record["record_is_self_authorizing"] = True
        self.case.replace_payload(contract.RECORD_TARGET, contract.canonical_bytes(record) + b"\n")
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle), "HOLD_CANONICAL_RECORD_CONTRACT")

    def test_registry_authority_expansion_rejected_with_valid_payload_hash(self) -> None:
        registry = json.loads(self.case.payloads[contract.REGISTRY])
        registry["canonical"] = True
        self.case.replace_payload(contract.REGISTRY, contract.canonical_bytes(registry) + b"\n")
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle),
                         "HOLD_REGISTRY_DELTA_OUTSIDE_SINGLE_REFERENCE")

    def test_runtime_activation_rejected(self) -> None:
        self.case.document["non_effects"]["runtime_activation"] = True
        self.case.save()
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle), "HOLD_NON_EFFECT_EXPANSION")

    def test_path_escape_rejected(self) -> None:
        self.case.document["immutable_sources"].pop("fixture/protected-source-00.txt")
        self.case.document["immutable_sources"]["../outside"] = "0" * 64
        self.case.save()
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle), "HOLD_CONTRACT_PATH")

    def test_duplicate_json_key_rejected(self) -> None:
        raw = (self.case.bundle / "PROMOTION_CONTRACT.json").read_bytes()
        put(self.case.bundle / "PROMOTION_CONTRACT.json", b'{"schema":"forged",' + raw[1:])
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle), "HOLD_JSON_DUPLICATE_KEY")

    def test_contract_cannot_start_authorized(self) -> None:
        self.case.document["lifecycle_state"] = "EXECUTABLE_AUTHORIZED"
        self.case.save()
        self.assert_hold(lambda: contract.load_bundle(self.case.bundle),
                         "HOLD_CONTRACT_PREMATURE_AUTHORITY")



class IndependentExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = SyntheticCase()
        self.addCleanup(self.case.close)
        self.executor = importlib.import_module("promote_origin_cell_gst_v21_specification")
        put(self.case.root / self.executor.SIM_MARKER,
            contract.canonical_bytes({"synthetic_only": True, "formal_effect_authorized": False}) + b"\n")
        self.bundle = contract.load_bundle(self.case.bundle)

    def assert_hold(self, operation, code: str | None = None) -> None:
        with self.assertRaises(contract.ContractError) as context:
            operation()
        if code is not None:
            self.assertEqual(context.exception.code, code)

    def grant_fixture(self) -> tuple[dict, dict, datetime]:
        at = datetime(2030, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
        coordinates = {
            "head": self.bundle["contract"]["head"],
            "git_status_sha256": "2" * 64,
            "authority_preimage_sha256": self.bundle["contract"]["immutable_sources"][contract.AUTHORITY_POINTER],
        }
        grant = {
            "schema": "W7TP_FOUNDER_SOVEREIGN_BREAK_GLASS/1.0",
            "public_key_ref": "SYNTHETIC_UNTRUSTED_KEY_NOT_AUTHORITY",
            "stage_b_signature_hex": "0" * 128,
            "body": {
                "effect": self.bundle["effect"], "target": contract.LIVE_ROOT,
                "git_head": coordinates["head"],
                "git_status_sha256": coordinates["git_status_sha256"],
                "authority_preimage_sha256": coordinates["authority_preimage_sha256"],
                "nonce": "0123456789abcdef" * 4,
                "issued_at": (at-timedelta(seconds=30)).isoformat(),
                "expires_at": (at+timedelta(seconds=30)).isoformat(),
                "single_use": True, "human_direct": True,
            },
        }
        return grant, coordinates, at

    def assert_no_publication(self) -> None:
        for ref in (contract.SPEC_TARGET, contract.RECORD_TARGET, contract.RECEIPT_TARGET):
            self.assertFalse((self.case.root / ref).exists(), ref)
        self.assertEqual((self.case.root / contract.REGISTRY).read_bytes(),
                         (self.case.bundle / "preimages/REGISTRY.json").read_bytes())

    def test_dry_run_makes_no_writes_and_no_authority(self) -> None:
        before = self.case.snapshot()
        result = self.executor.dry_run(self.case.root, self.case.bundle, simulation=True)
        self.assertIs(result["formal_effect_authorized"], False)
        self.assertIs(result["effect_authorized"], False)
        self.assertIs(result["writes_performed"], False)
        self.assertEqual(self.case.snapshot(), before)
        self.assertFalse((self.case.root / ".fixture-audit").exists())

    def test_synthetic_marker_required(self) -> None:
        (self.case.root / self.executor.SIM_MARKER).unlink()
        self.assert_hold(lambda: self.executor.simulate(self.case.root, self.case.bundle))
        self.assert_no_publication()

    def test_success_is_simulation_only_and_cold_status_is_read_only(self) -> None:
        result = self.executor.simulate(self.case.root, self.case.bundle)
        self.assertEqual(result["state"], "SIMULATED_EFFECT_VERIFIED")
        self.assertIs(result["formal_effect_authorized"], False)
        self.assertIs(result["runtime_activated"], False)
        receipt = json.loads((self.case.root / contract.RECEIPT_TARGET).read_bytes())
        self.assertEqual(receipt["schema"], self.executor.SIM_RECEIPT_SCHEMA)
        self.assertIs(receipt["formal_effect_authorized"], False)
        self.assertIs(receipt["native_authorization"]["effect_authorized"], False)
        registry = json.loads((self.case.root / contract.REGISTRY).read_bytes())
        self.assertIs(registry["canonical"], False)
        self.assertIs(registry["capabilities"][0]["d8_authority"]["canonical"], False)
        before = self.case.snapshot()
        process = subprocess.run(
            [sys.executable, "-B", str(HERE / "promote_origin_cell_gst_v21_specification.py"),
             "status", "--root", str(self.case.root), "--bundle", str(self.case.bundle), "--synthetic"],
            check=False, text=True, capture_output=True, timeout=20,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        self.assertEqual(process.returncode, 0, process.stdout[-1000:] + process.stderr[-1000:])
        cold = json.loads(process.stdout)
        self.assertEqual(cold["state"], "SIMULATED_EFFECT_VERIFIED")
        self.assertIs(cold["formal_effect_authorized"], False)
        self.assertIs(cold["nonce_consumed_during_status"], False)
        self.assertEqual(self.case.snapshot(), before)

    def test_simulation_receipt_cannot_be_relabelled_formal(self) -> None:
        self.executor.simulate(self.case.root, self.case.bundle)
        path = self.case.root / contract.RECEIPT_TARGET
        receipt = json.loads(path.read_bytes())
        receipt["formal_effect_authorized"] = True
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = contract.sha256(contract.canonical_bytes(receipt))
        put(path, contract.canonical_bytes(receipt) + b"\n")
        self.assert_hold(lambda: self.executor.status(self.case.root, self.case.bundle, simulation=True),
                         "HOLD_PROMOTION_RECEIPT_BINDING")

    def test_grant_shape_is_not_signature_or_authority(self) -> None:
        grant, coordinates, at = self.grant_fixture()
        before = self.case.snapshot()
        body = self.executor.validate_grant_shape(grant, self.bundle, coordinates, at=at)
        self.assertEqual(body, grant["body"])
        self.assertNotIn("authority_verified", body)
        self.assertNotIn("effect_authorized", body)
        self.assertEqual(self.case.snapshot(), before)

    def test_absent_grant_rejected(self) -> None:
        _, coordinates, at = self.grant_fixture()
        self.assert_hold(lambda: self.executor.validate_grant_shape(None, self.bundle, coordinates, at=at),
                         "HOLD_FOUNDER_FRESH_SIGNATURE_REQUIRED")
        self.assert_no_publication()

    def test_expiry_future_issue_and_excessive_ttl_rejected(self) -> None:
        for name in ("expired", "future", "overlong", "naive"):
            with self.subTest(name=name):
                grant, coordinates, at = self.grant_fixture()
                if name == "expired":
                    grant["body"]["expires_at"] = at.isoformat()
                elif name == "future":
                    grant["body"]["issued_at"] = (at+timedelta(seconds=1)).isoformat()
                elif name == "overlong":
                    grant["body"]["expires_at"] = (at+timedelta(seconds=301)).isoformat()
                else:
                    grant["body"]["issued_at"] = at.replace(tzinfo=None).isoformat()
                self.assert_hold(lambda: self.executor.validate_grant_shape(
                    grant, self.bundle, coordinates, at=at),
                    "HOLD_GRANT_TIMEZONE" if name == "naive" else "HOLD_GRANT_FRESHNESS_OR_TTL")
        self.assert_no_publication()

    def test_effect_preimage_and_human_scope_mismatch_rejected(self) -> None:
        for key, replacement, code in (
            ("effect", "FOREIGN_EFFECT", "HOLD_GRANT_EFFECT_TARGET"),
            ("git_status_sha256", "3" * 64, "HOLD_GRANT_PREIMAGE_BINDING"),
            ("human_direct", 1, "HOLD_GRANT_HUMAN_SINGLE_USE"),
            ("single_use", False, "HOLD_GRANT_HUMAN_SINGLE_USE"),
        ):
            with self.subTest(field=key):
                grant, coordinates, at = self.grant_fixture()
                grant["body"][key] = replacement
                self.assert_hold(lambda: self.executor.validate_grant_shape(
                    grant, self.bundle, coordinates, at=at), code)
        self.assert_no_publication()

    def test_native_founder_false_is_rejected_without_signature_mock_pass(self) -> None:
        grant, _, _ = self.grant_fixture()
        rejecting_module = SimpleNamespace(
            resolve_founder_sovereign_root_role_promotion_authority=
                lambda **kwargs: {"authority_verified": False, "effect_authorized": False})
        self.assert_hold(lambda: self.executor.verify_grant_signature(
            self.case.root, self.bundle, grant, rejecting_module), "HOLD_NATIVE_FOUNDER_TRUST_CHAIN")
        self.assert_no_publication()

    def test_caller_pass_with_absent_native_receipt_is_rejected(self) -> None:
        grant, _, _ = self.grant_fixture()
        paths = self.executor.audit_paths(self.bundle, self.case.root)
        self.executor.directory(paths["authority"], create=True)
        self.assert_hold(lambda: self.executor.verify_native_receipt(
            self.case.root, self.bundle, paths, grant,
            {"state": "FOUNDER_SOVEREIGN_DIRECT_OVERRIDE", "effect_authorized": True,
             "authority_verified": True}), "HOLD_FILE_READ")
        self.assert_no_publication()

    def test_native_false_result_rejected_even_with_consistent_synthetic_receipt_data(self) -> None:
        # Every file in this case is synthetic negative-test data. No signature
        # validation is replaced with a PASS and no formal execution is invoked.
        grant, _, at = self.grant_fixture()
        paths = self.executor.audit_paths(self.bundle, self.case.root)
        body = grant["body"]
        nonce_hash = contract.sha256(body["nonce"].encode())
        native = {
            "schema": "W7TP_FOUNDER_SOVEREIGN_DIRECT_OVERRIDE_RECEIPT/1.0",
            "state": "FOUNDER_SOVEREIGN_DIRECT_OVERRIDE",
            "effect": self.bundle["effect"], "target": contract.LIVE_ROOT,
            "git_head": body["git_head"], "git_status_sha256": body["git_status_sha256"],
            "authority_preimage_sha256": body["authority_preimage_sha256"],
            "nonce_sha256": nonce_hash,
            "signature_sha256": contract.sha256(grant["stage_b_signature_hex"].encode()),
            "human_direct": True, "single_use": True,
            "ai_agent_authority_expansion": False, "validated_at": at.isoformat(),
        }
        native["receipt_sha256"] = contract.sha256(contract.canonical_bytes(native))
        native_path = paths["authority"] / (nonce_hash + ".json")
        put(native_path, contract.canonical_bytes(native) + b"\n")
        put(paths["replay"] / (nonce_hash + ".json"), contract.canonical_bytes({
            "native_receipt_sha256": native["receipt_sha256"],
            "nonce_sha256": nonce_hash, "permanent_replay_rejection": True,
        }) + b"\n")
        rejecting_result = {
            "state": "FOUNDER_SOVEREIGN_DIRECT_OVERRIDE",
            "authority_verified": False, "effect_authorized": False,
            "receipt_sha256": native["receipt_sha256"], "receipt_path": str(native_path),
        }
        self.assert_hold(lambda: self.executor.verify_native_receipt(
            self.case.root, self.bundle, paths, grant, rejecting_result), "HOLD_NATIVE_RESULT_NOT_EXACT")
        self.assert_no_publication()

    def test_live_apply_refuses_synthetic_root_before_effect(self) -> None:
        grant_path = self.case.base / "dummy-grant.json"
        put(grant_path, b"{}\n")
        self.assert_hold(lambda: self.executor.apply(
            self.case.root, self.case.bundle, grant_path, exclusive_change_window=True),
            "HOLD_EXACT_LIVE_ROOT")
        self.assert_no_publication()
        self.assertFalse((self.case.root / ".fixture-audit").exists())

    def test_source_drift_during_transaction_rolls_back(self) -> None:
        def mutate(event, root, stage):
            if event == "before_exchange":
                put(root / contract.SOURCE_CODEC, b"# EXTERNAL VERSION AFTER PREFLIGHT\n")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=mutate)
        self.assertEqual(result["state"], "HOLD")
        self.assertIs(result["formal_effect_authorized"], False)
        self.assert_no_publication()
        self.assertEqual((self.case.root / contract.SOURCE_CODEC).read_bytes(),
                         b"# EXTERNAL VERSION AFTER PREFLIGHT\n")

    def test_failure_after_creates_restores_preimages_and_records_recovery(self) -> None:
        def fail(event, root, stage):
            if event == "after_creates":
                raise RuntimeError("INDEPENDENT_TEST_FAILURE_AFTER_CREATES")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=fail)
        self.assertEqual(result["state"], "HOLD")
        self.assertIs(result["formal_effect_authorized"], False)
        self.assertIs(result["nonce_reuse_permitted"], False)
        self.assert_no_publication()
        before = self.case.snapshot()
        recovery = self.executor.recovery_plan(self.case.root, self.case.bundle, simulation=True)
        self.assertIs(recovery["automatic_mutation_permitted"], False)
        self.assertIs(recovery["formal_effect_authorized"], False)
        self.assertEqual(self.case.snapshot(), before)

    def test_failure_after_exchange_restores_exact_original_registry(self) -> None:
        def fail(event, root, stage):
            if event == "after_exchange":
                raise RuntimeError("INDEPENDENT_TEST_FAILURE_AFTER_EXCHANGE")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=fail)
        self.assertEqual(result["state"], "HOLD")
        self.assertIs(result["registry_exchange_reversed"], True)
        self.assert_no_publication()

    def test_foreign_registry_before_exchange_survives_rollback(self) -> None:
        foreign = b'{"foreign_registry":"arrived in exchange window"}\n'
        def change(event, root, stage):
            if event == "before_exchange":
                put(root / contract.REGISTRY, foreign)
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=change)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual((self.case.root / contract.REGISTRY).read_bytes(), foreign)
        self.assertFalse((self.case.root / contract.RECEIPT_TARGET).exists())

    def test_foreign_registry_after_exchange_is_never_overwritten(self) -> None:
        foreign = b'{"foreign_registry":"after exchange"}\n'
        observed_stage = []
        def change(event, root, stage):
            if event == "after_exchange":
                observed_stage.append(stage)
                put(root / contract.REGISTRY, foreign)
                raise RuntimeError("INDEPENDENT_FOREIGN_REGISTRY")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=change)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual((self.case.root / contract.REGISTRY).read_bytes(), foreign)
        self.assertEqual(observed_stage[0].read_bytes(),
                         (self.case.bundle / "preimages/REGISTRY.json").read_bytes())
        self.assertTrue(result["debt"])
        self.assertFalse((self.case.root / contract.RECEIPT_TARGET).exists())

    def test_unknown_stage_is_preserved_and_not_published_during_rollback(self) -> None:
        foreign = b'{"foreign_stage":"never publish as registry"}\n'
        observed_stage = []
        def change(event, root, stage):
            if event == "after_exchange":
                observed_stage.append(stage)
                put(stage, foreign)
                raise RuntimeError("INDEPENDENT_FOREIGN_STAGE")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=change)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual((self.case.root / contract.REGISTRY).read_bytes(),
                         self.case.payloads[contract.REGISTRY])
        self.assertEqual(observed_stage[0].read_bytes(), foreign)
        self.assertTrue(result["debt"])
        self.assertFalse((self.case.root / contract.RECEIPT_TARGET).exists())

    def test_foreign_created_target_is_not_deleted_during_rollback(self) -> None:
        foreign = b"# OUTSIDE WRITER OWNS THIS REPLACEMENT\n"
        def change(event, root, stage):
            if event == "after_creates":
                put(root / contract.SPEC_TARGET, foreign)
                raise RuntimeError("INDEPENDENT_FOREIGN_CREATED")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=change)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual((self.case.root / contract.SPEC_TARGET).read_bytes(), foreign)
        self.assertTrue(result["debt"])
        self.assertFalse((self.case.root / contract.RECEIPT_TARGET).exists())

    def test_foreign_same_bytes_different_inode_is_not_deleted(self) -> None:
        new_identity = []
        def replace(event, root, stage):
            if event == "after_creates":
                path = root / contract.SPEC_TARGET
                replacement = self.case.base / "foreign-identical-replacement"
                replacement.write_bytes(path.read_bytes())
                os.replace(replacement, path)
                new_identity.append((path.stat().st_dev, path.stat().st_ino))
                raise RuntimeError("INDEPENDENT_FOREIGN_IDENTICAL_INODE")
        result = self.executor.simulate(self.case.root, self.case.bundle, hook=replace)
        self.assertEqual(result["state"], "HOLD")
        path = self.case.root / contract.SPEC_TARGET
        self.assertTrue(path.exists())
        self.assertEqual((path.stat().st_dev, path.stat().st_ino), new_identity[0])
        self.assertTrue(result["debt"])

    def test_existing_stage_is_collision_not_overwritten(self) -> None:
        stage = self.case.root / "configs/total_field" / (
            ".gst-v21-" + self.bundle["contract_sha256"] + ".registry-stage")
        foreign = b"FOREIGN STAGE PREEXISTS"
        put(stage, foreign)
        self.assert_hold(lambda: self.executor.simulate(self.case.root, self.case.bundle),
                         "HOLD_STAGE_ALREADY_EXISTS")
        self.assertEqual(stage.read_bytes(), foreign)
        self.assert_no_publication()

    def test_failed_attempt_cannot_be_blindly_replayed(self) -> None:
        def fail(event, root, stage):
            if event == "after_creates":
                raise RuntimeError("INDEPENDENT_DURABLE_ATTEMPT")
        first = self.executor.simulate(self.case.root, self.case.bundle, hook=fail)
        self.assertEqual(first["state"], "HOLD")
        self.assert_no_publication()
        before = self.case.snapshot()
        try:
            second = self.executor.simulate(self.case.root, self.case.bundle)
        except (contract.ContractError, FileExistsError) as exc:
            if isinstance(exc, contract.ContractError):
                self.assertTrue(exc.code.startswith("HOLD_"))
        else:
            self.assertTrue(second["state"].startswith("HOLD"))
            self.assertIs(second.get("formal_effect_authorized"), False)
        self.assert_no_publication()
        self.assertEqual(self.case.snapshot(), before)

    def test_persistent_replay_rejected_across_instances_and_after_ttl(self) -> None:
        directory = self.case.base / "isolated-replay"
        directory.mkdir(mode=0o700)
        nonce = "1234567890abcdef" * 4
        first = self.executor.PersistentReplayLedger(directory)
        self.assertTrue(first.mark_used_or_replay(nonce, "4" * 64, 1000.0, 300))
        second = self.executor.PersistentReplayLedger(directory)
        self.assertFalse(second.mark_used_or_replay(nonce, "5" * 64, 10000000.0, 300))
        markers = list(directory.iterdir())
        self.assertEqual(len(markers), 1)
        self.assertNotIn(nonce.encode(), markers[0].read_bytes())
        data = json.loads(markers[0].read_bytes())
        self.assertEqual(data["native_receipt_sha256"], "4" * 64)
        self.assertIs(data["permanent_replay_rejection"], True)
        self.assert_no_publication()

    def test_busy_operation_lock_prevents_publication(self) -> None:
        paths = self.executor.audit_paths(self.bundle, self.case.root)
        self.executor.directory(paths["base"], create=True)
        with self.executor.operation_lock(paths["lock"]):
            self.assert_hold(lambda: self.executor.simulate(self.case.root, self.case.bundle),
                             "HOLD_CONCURRENT_OPERATION")
        self.assert_no_publication()


    def test_colocated_raw_helper_ignores_poisoned_valid_timestamp_cache(self) -> None:
        helper = self.case.bundle / "candidate/gst_v21_specification_contract.py"
        poison_timestamp_cache(helper)
        before = self.case.snapshot()
        process = subprocess.run(
            [sys.executable, "-B", str(self.case.bundle / "candidate/promote_origin_cell_gst_v21_specification.py"),
             "dry-run", "--root", str(self.case.root), "--bundle", str(self.case.bundle), "--synthetic"],
            check=False, text=True, capture_output=True, timeout=20,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        self.assertEqual(process.returncode, 0, process.stdout[-1000:] + process.stderr[-1000:])
        observed = json.loads(process.stdout)
        self.assertIs(observed["formal_effect_authorized"], False)
        self.assertIs(observed["writes_performed"], False)
        self.assertEqual(self.case.snapshot(), before)

    def test_native_loader_executes_bound_raw_synthetic_sources_not_cache_or_preloaded_modules(self) -> None:
        names = (
            "tools.total_field.w7tp_v2_3_candidate_source",
            "tools.total_field.w7tp_true8d_contract_sandbox",
            "tools.total_field.w7tp_ed25519_verifier",
            "tools.total_field_ed25519_backend",
            "tools.total_field_authority_resolver",
        )
        previous_modules = {name: module for name, module in sys.modules.items()
                            if name == "tools" or name.startswith("tools.")}
        try:
            for index, name in enumerate(names):
                ref = name.replace(".", "/") + ".py"
                if ref not in self.case.document["immutable_sources"]:
                    self.case.document["immutable_sources"].pop(f"fixture/protected-source-{index:02d}.txt")
                raw = ("SYNTHETIC_SOURCE_ONLY = True\nSOURCE_LABEL = " + repr(name) + "\n").encode()
                put(self.case.root / ref, raw)
                self.case.document["immutable_sources"][ref] = contract.sha256(raw)
                poison_timestamp_cache(self.case.root / ref)
                stale = ModuleType(name)
                stale.__file__ = str(self.case.root / ref)
                stale.SYNTHETIC_SOURCE_ONLY = False
                sys.modules[name] = stale
            self.case.save()
            self.bundle = contract.load_bundle(self.case.bundle)
            before = self.case.snapshot()
            module = self.executor.native_module(self.case.root, self.bundle)
            self.assertEqual(module.SOURCE_LABEL, names[-1])
            for name in names:
                self.assertIs(sys.modules[name].SYNTHETIC_SOURCE_ONLY, True)
                self.assertFalse(hasattr(sys.modules[name], "effect_authorized"))
            self.assertFalse(hasattr(module, "resolve_founder_signed_break_glass_effect"))
            self.assertEqual(self.case.snapshot(), before)
        finally:
            for name in list(sys.modules):
                if name == "tools" or name.startswith("tools."):
                    del sys.modules[name]
            sys.modules.update(previous_modules)

    def test_transaction_rejects_unbound_audit_paths(self) -> None:
        paths = self.executor.audit_paths(self.bundle, self.case.root)
        paths["attempt"] = self.case.base / "unbound-attempt.json"
        before = self.case.snapshot()
        self.assert_hold(lambda: self.executor.transaction(
            self.case.root, self.bundle, paths,
            {"state": "SYNTHETIC_TEST_ONLY", "effect_authorized": False},
            simulation=True))
        self.assertEqual(self.case.snapshot(), before)
        self.assertFalse(paths["attempt"].exists())
        self.assert_no_publication()

class JsonResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rows = []

    def addSuccess(self, test) -> None:
        super().addSuccess(test)
        self.rows.append({"test": test.id(), "status": "PASS"})

    def addFailure(self, test, err) -> None:
        super().addFailure(test, err)
        self.rows.append({"test": test.id(), "status": "FAIL",
                          "exception": err[0].__name__, "detail": str(err[1])[:1200]})

    def addError(self, test, err) -> None:
        super().addError(test, err)
        self.rows.append({"test": test.id(), "status": "ERROR",
                          "exception": err[0].__name__, "detail": str(err[1])[:1200]})

    def addSkip(self, test, reason) -> None:
        super().addSkip(test, reason)
        self.rows.append({"test": test.id(), "status": "SKIP", "reason": reason})

    def addSubTest(self, test, subtest, err) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.rows.append({"test": test.id(), "subtest": str(subtest),
                              "status": "FAIL", "exception": err[0].__name__,
                              "detail": str(err[1])[:1200]})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper-only", action="store_true")
    args = parser.parse_args()
    if not args.helper_only and not EXECUTOR_CASES_READY:
        print(json.dumps({
            "state": "HOLD_EXECUTOR_TEST_API_PENDING",
            "formal_effect_authorized": False, "tests_executed": 0,
            "reason": "Full transaction acceptance has not yet been implemented in this test file.",
        }, sort_keys=True))
        return 2
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentHelperTests)
    if not args.helper_only:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentExecutorTests))
    result = unittest.TextTestRunner(verbosity=2, resultclass=JsonResult).run(suite)
    print(json.dumps({
        "schema": "GST_V21_INDEPENDENT_FUNCTIONAL_TEST/1.0",
        "state": "PASS_ISOLATED_FUNCTIONAL_TESTS" if result.wasSuccessful() else "FAIL_ISOLATED_FUNCTIONAL_TESTS",
        "scope": "HELPER_ONLY_NOT_COMPLETE" if args.helper_only else "HELPER_AND_EXECUTOR_SYNTHETIC",
        "test_count": result.testsRun, "results": result.rows,
        "failure_count": len(result.failures), "error_count": len(result.errors),
        "skip_count": len(result.skipped),
        "formal_effect_authorized": False,
        "native_resolver_called": False,
        "real_nonce_consumed": False,
        "remote_mutations": 0,
        "codec_executed": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
