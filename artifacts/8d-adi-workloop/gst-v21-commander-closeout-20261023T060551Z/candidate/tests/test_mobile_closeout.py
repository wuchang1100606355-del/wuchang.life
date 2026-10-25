#!/usr/bin/env python3
"""Bounded regression tests using ONLY synthetic, isolated WebAuthn fixtures.

Run with the target system's existing fido2 and cryptography installations.
No production credential, proof, key, repository state, or proxy is accessed.
Synthetic private keys exist only in process memory; fixture state is temporary.
Passing these tests establishes implementation behavior, not Founder authority.
"""
from __future__ import annotations

import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fido2 import cbor
from fido2.cose import ES256
from fido2.webauthn import Aaguid, AttestedCredentialData

import gst_mobile_approval_first as capture
import gst_mobile_approval_server as native_http
import w7tp_founder_sign as operator


METRICS = []
REJECTED = (PermissionError, ValueError, TypeError, KeyError, InvalidSignature)


class SyntheticFixture(unittest.TestCase):
    def setUp(self):
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        directory = self.resources.enter_context(
            tempfile.TemporaryDirectory(prefix="w7tp_SYNTHETIC_TEST_ONLY_")
        )
        self.root = Path(directory).resolve()
        self.state = self.root / "synthetic-state"
        self.state.mkdir(mode=0o700)
        self.bundle = "artifacts/synthetic-contract"
        self.leaf = "manifests/synthetic-specification"
        self.contract = self.root / self.bundle / "PROMOTION_CONTRACT.json"
        self.descriptor = self.root / self.bundle / "ADMISSION_DESCRIPTOR.json"
        self.spec = self.root / self.leaf / "SPECIFICATION.md"
        self.receipt = self.root / self.leaf / "FOUNDER_RATIFICATION_RECEIPT.json"
        for path, raw in (
            (self.contract, b'{"synthetic_fixture_only":true,"authority":false}\n'),
            (self.descriptor, b'{"synthetic_fixture_only":true,"grant":false}\n'),
            (self.spec, b"SYNTHETIC TEST FIXTURE. NO FOUNDER OR CANONICAL AUTHORITY.\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(32)
        cose = ES256.from_cryptography_key(self.private_key.public_key())
        self.key = AttestedCredentialData.create(Aaguid.NONE, self.credential_id, cose)
        public = self.state / "synthetic-public-credential.json"
        public_raw = capture.canon({
            "synthetic_fixture_only": True,
            "credential_data_b64url": capture.b64(bytes(self.key)),
        }) + b"\n"
        public.write_bytes(public_raw)
        public.chmod(0o600)
        replacements = {
            "ROOT": self.root, "BUNDLE": self.bundle, "LEAF": self.leaf,
            "STATE": self.state, "EVIDENCE": self.state / "SIGNED_APPROVAL.json",
            "PUBLIC_CRED": public, "CRED": public,
            "CONTRACT_SHA": capture.sha(self.contract.read_bytes()),
            "DESCRIPTOR_SHA": capture.sha(self.descriptor.read_bytes()),
            "CRED_SHA": capture.sha(public_raw),
            "COSE_SHA": capture.sha(cbor.encode(cose)),
            "SCOPE": "SYNTHETIC_TEST_ONLY_NO_AUTHORITY",
            "DOMAIN": "SYNTHETIC_TEST_ONLY_NO_AUTHORITY",
            "FILES": {
                self.bundle + "/PROMOTION_CONTRACT.json": capture.sha(self.contract.read_bytes()),
                self.bundle + "/ADMISSION_DESCRIPTOR.json": capture.sha(self.descriptor.read_bytes()),
            },
            "INTENDED_POSTIMAGES": {
                self.leaf + "/SPECIFICATION.md": capture.sha(self.spec.read_bytes()),
            },
        }
        for name, value in replacements.items():
            self.resources.enter_context(mock.patch.object(capture, name, value))
        self.resources.enter_context(mock.patch.object(operator, "DEFAULT_CONTRACT", self.contract))
        self.resources.enter_context(mock.patch.object(operator, "DEFAULT_TARGET", self.receipt))
        self.fido = capture.make_server()

    def pending(self):
        started = capture.begin(self.fido)
        path = self.state / "ceremonies" / started["ceremony_id"] / "PENDING.json"
        return capture.read(path)

    @staticmethod
    def rebind_pending(pending):
        """Recompute an isolated fixture challenge after deliberate test changes."""
        challenge = capture.b64(hashlib.sha256(
            capture.canon([capture.DOMAIN, pending["signed_payload"]])
        ).digest())
        pending["webauthn_state"]["challenge"] = challenge
        pending["options"]["publicKey"]["challenge"] = challenge

    def assertion(self, pending, *, origin=None, cross_origin=False, flags=5,
                  challenge=None, rp_id=None):
        client = capture.canon({
            "type": "webauthn.get",
            "challenge": challenge or pending["webauthn_state"]["challenge"],
            "origin": capture.ORIGIN if origin is None else origin,
            "crossOrigin": cross_origin,
        })
        auth = (hashlib.sha256((rp_id or capture.RP_ID).encode()).digest()
                + bytes([flags]) + struct.pack(">I", 1))
        signature = self.private_key.sign(
            auth + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256())
        )
        encoded_id = capture.b64(self.credential_id)
        return {
            "id": encoded_id, "rawId": encoded_id, "type": "public-key",
            "clientExtensionResults": {},
            "response": {
                "clientDataJSON": capture.b64(client),
                "authenticatorData": capture.b64(auth),
                "signature": capture.b64(signature), "userHandle": None,
            },
        }

    def proof(self, pending=None, **assertion_options):
        pending = self.pending() if pending is None else pending
        return {
            "schema": capture.DOMAIN + "/SIGNED_APPROVAL", "pending": pending,
            "assertion": self.assertion(pending, **assertion_options),
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "verified_at_source": "SYNTHETIC_ISOLATION_TEST_ONLY",
            "founder_binding_verified": False, "formal_effect_authorized": False,
        }

    def completion(self, pending=None):
        pending = self.pending() if pending is None else pending
        return {"ceremony_id": pending["ceremony_id"],
                "response": self.assertion(pending)}

    def serve(self, callback):
        stop = threading.Event()
        closed = threading.Event()
        times = {}
        server = native_http.create_server(
            ("127.0.0.1", 0), fido_instance=self.fido,
            on_verified=callback, stop_event=stop,
        )
        port = server.server_address[1]
        worker = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        worker.start()

        def close_on_stop():
            stop.wait()
            server.shutdown()
            server.server_close()
            times["closed_ns"] = time.monotonic_ns()
            closed.set()

        closer = threading.Thread(target=close_on_stop, daemon=True)
        closer.start()

        def cleanup():
            stop.set()
            closer.join(2)
            worker.join(2)
            self.assertFalse(closer.is_alive(), "isolated HTTP server did not close")

        self.addCleanup(cleanup)
        return server, port, stop, closed, times

    def request(self, port, path, body=None, *, host=None, origin=None,
                include_origin=True):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        headers = {"Host": host or capture.RP_ID + ":9122"}
        if body is not None:
            headers["Content-Type"] = "application/json"
            if include_origin:
                headers["Origin"] = capture.ORIGIN if origin is None else origin
            headers["Sec-Fetch-Site"] = "same-origin"
        try:
            conn.request("GET" if body is None else "POST", path,
                         body=None if body is None else capture.canon(body), headers=headers)
            response = conn.getresponse()
            raw = response.read()
            return response.status, json.loads(raw), raw
        finally:
            conn.close()


class CryptoAndStorageTests(SyntheticFixture):
    def test_real_p256_verifier_and_historical_window(self):
        pending = self.pending()
        old = datetime.now(timezone.utc) - timedelta(days=1)
        pending["signed_payload"]["issued_at"] = old.isoformat()
        pending["signed_payload"]["expires_at"] = (old + timedelta(seconds=900)).isoformat()
        self.rebind_pending(pending)
        proof = self.proof(pending)
        proof["verified_at"] = (old + timedelta(seconds=30)).isoformat()
        with mock.patch.object(self.fido, "authenticate_complete",
                               wraps=self.fido.authenticate_complete) as verifier:
            result = capture.verify_proof(self.fido, proof)
        self.assertEqual(verifier.call_count, 1)
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["founder_binding_verified"])
        self.assertFalse(result["formal_effect_authorized"])

    def test_cryptographic_and_origin_rejections(self):
        pending = self.pending()
        cases = {
            "wrong_origin": self.proof(pending, origin="https://example.invalid"),
            "legacy_8444_origin": self.proof(pending, origin="https://" + capture.RP_ID + ":8444"),
            "cross_origin": self.proof(pending, cross_origin=True),
            "wrong_challenge": self.proof(pending, challenge=capture.b64(os.urandom(32))),
            "missing_up": self.proof(pending, flags=4),
            "missing_uv": self.proof(pending, flags=1),
            "wrong_rp": self.proof(pending, rp_id="example.invalid"),
        }
        changed = self.proof(pending)
        signature = bytearray(capture.unb64(changed["assertion"]["response"]["signature"]))
        signature[-1] ^= 1
        changed["assertion"]["response"]["signature"] = capture.b64(bytes(signature))
        cases["tampered_signature"] = changed
        for name, proof in cases.items():
            with self.subTest(case=name), self.assertRaises(REJECTED):
                capture.verify_proof(self.fido, proof)
        self.assertFalse(capture.EVIDENCE.exists())

    def test_expiry_lifetime_and_time_zone_rejections(self):
        pending = self.pending()
        proof = self.proof(pending)
        proof["verified_at"] = pending["signed_payload"]["expires_at"]
        with self.assertRaises(REJECTED):
            capture.verify_proof(self.fido, proof)
        issued = capture.instant(pending["signed_payload"]["issued_at"])
        for name, expiry in (
            ("overlong", (issued + timedelta(seconds=901)).isoformat()),
            ("nonpositive", issued.isoformat()),
            ("no_timezone", (issued + timedelta(seconds=30)).replace(tzinfo=None).isoformat()),
        ):
            changed = copy.deepcopy(pending)
            changed["signed_payload"]["expires_at"] = expiry
            self.rebind_pending(changed)
            with self.subTest(case=name), self.assertRaises(REJECTED):
                capture.check_pending(changed)

    def test_same_completion_is_idempotent_other_replay_rejected(self):
        body = self.completion()
        result = capture.complete(self.fido, body)
        before = capture.EVIDENCE.read_bytes()
        self.assertTrue(result["signature_verified"])
        self.assertTrue(capture.complete(self.fido, copy.deepcopy(body))["signature_verified"])
        self.assertEqual(capture.EVIDENCE.read_bytes(), before)
        for field in ("ceremony", "assertion"):
            changed = copy.deepcopy(body)
            if field == "ceremony":
                changed["ceremony_id"] = "f" * 32
            else:
                changed["response"]["response"]["signature"] = capture.b64(b"wrong")
            with self.subTest(case=field), self.assertRaises(REJECTED):
                capture.complete(self.fido, changed)
        self.assertEqual(capture.EVIDENCE.read_bytes(), before)

    def test_fixed_input_drift_rejected_before_publication(self):
        body = self.completion()
        self.descriptor.write_bytes(b"synthetic fixture drift\n")
        with self.assertRaises(REJECTED):
            capture.complete(self.fido, body)
        self.assertFalse(capture.EVIDENCE.exists())

    def test_factual_receipt_atomic_idempotent_and_no_authority_escalation(self):
        capture.complete(self.fido, self.completion())
        proof_before = capture.EVIDENCE.read_bytes()
        writer = operator.ReceiptWriter(self.fido, self.contract, self.receipt)
        first = writer()
        raw = self.receipt.read_bytes()
        value = json.loads(raw)
        self.assertTrue(value["signature_verified"])
        for field in ("founder_binding_verified", "formal_effect_authorized",
                      "canonical_promotion_executed", "runtime_activation_authorized",
                      "ed25519_grant_issued", "machine_private_key_used"):
            self.assertFalse(value[field], field)
        self.assertEqual(value["evidence_sha256"], capture.sha(proof_before))
        self.assertEqual(first["receipt"]["sha256"], capture.sha(raw))
        self.assertTrue(writer()["receipt"]["reused"])
        self.assertEqual(self.receipt.read_bytes(), raw)
        self.assertEqual(capture.EVIDENCE.read_bytes(), proof_before)

    def test_receipt_compare_and_swap_preserves_exact_previous_bytes(self):
        before = b'{"synthetic_fixture_only": true, "version": 1}\n'
        self.receipt.write_bytes(before)
        replacement = {"synthetic_fixture_only": True, "version": 2,
                       "formal_effect_authorized": False}
        with self.assertRaises(PermissionError):
            operator.publish_receipt(self.receipt, replacement, "0" * 64)
        self.assertEqual(self.receipt.read_bytes(), before)
        self.assertFalse((self.state / "receipt-history").exists())
        result = operator.publish_receipt(self.receipt, replacement, capture.sha(before))
        expected = capture.canon(replacement) + b"\n"
        self.assertEqual(self.receipt.read_bytes(), expected)
        self.assertEqual(result["sha256"], capture.sha(expected))
        historical = self.state / "receipt-history" / (capture.sha(before) + ".json")
        self.assertEqual(historical.read_bytes(), before)
        self.assertEqual(list(self.receipt.parent.glob(".receipt-*")), [])


class HTTPClosureTests(SyntheticFixture):
    def test_host_and_origin_are_enforced(self):
        callback = mock.Mock()
        _, port, stop, _, _ = self.serve(callback)
        self.assertEqual(self.request(port, "/health")[0], 200)
        cases = (
            ("host", {"host": "example.invalid"}),
            ("origin", {"origin": "https://example.invalid"}),
            ("missing_origin", {"include_origin": False}),
        )
        for name, extra in cases:
            with self.subTest(case=name):
                code, _, _ = self.request(port, "/gst-v21/options", {}, **extra)
                self.assertGreaterEqual(code, 400)
                self.assertLess(code, 500)
        self.assertFalse(stop.is_set())
        callback.assert_not_called()
        self.assertFalse(capture.EVIDENCE.exists())

    def test_valid_complete_receipt_and_port_close_under_one_second(self):
        times = {}
        writer = operator.ReceiptWriter(self.fido, self.contract, self.receipt)

        def callback(summary):
            result = writer(summary)
            times["published_ns"] = time.monotonic_ns()
            return result

        _, port, stop, closed, close_times = self.serve(callback)
        body = self.completion()
        code, result, _ = self.request(port, "/gst-v21/complete", body)
        self.assertEqual(code, 200)
        self.assertTrue(result["signature_verified"])
        self.assertTrue(stop.wait(0.8))
        self.assertTrue(closed.wait(0.8))
        elapsed_ms = (close_times["closed_ns"] - times["published_ns"]) / 1_000_000
        self.assertLess(elapsed_ms, 1000)
        with socket.socket() as probe:
            probe.settimeout(0.2)
            self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0)
        self.assertTrue(self.receipt.exists())
        self.assertFalse(json.loads(self.receipt.read_bytes())["formal_effect_authorized"])
        METRICS.append({"test": "synthetic_http_completion_to_port_close",
                        "elapsed_ms": round(elapsed_ms, 3),
                        "under_one_second": True, "production_phone_test": False})

    def test_receipt_callback_failure_preserves_proof_and_stops(self):
        marker = "SYNTHETIC_SENSITIVE_EXCEPTION_MARKER"

        def broken_callback(_summary):
            raise RuntimeError(marker)

        _, port, stop, closed, _ = self.serve(broken_callback)
        code, result, raw = self.request(port, "/gst-v21/complete", self.completion())
        self.assertGreaterEqual(code, 400)
        self.assertNotIn(marker.encode(), raw)
        self.assertTrue(stop.wait(0.8))
        self.assertTrue(closed.wait(0.8))
        self.assertTrue(capture.EVIDENCE.exists())
        self.assertTrue(capture.verify_proof(self.fido, capture.read(capture.EVIDENCE))["signature_verified"])
        self.assertTrue(result["signature_verified"], "saved proof must not be reported as unverified")
        self.assertFalse(result["formal_effect_authorized"])
        self.assertFalse(self.receipt.exists())

    def test_timeout_drain_waits_for_running_completion_without_losing_proof(self):
        entered = threading.Event()
        release = threading.Event()
        drained = threading.Event()
        drain_result = []
        response = []
        errors = []
        writer = operator.ReceiptWriter(self.fido, self.contract, self.receipt)

        def callback(summary):
            entered.set()
            if not release.wait(0.8):
                raise RuntimeError("SYNTHETIC_TEST_CALLBACK_TIMEOUT")
            return writer(summary)

        server, port, stop, closed, _ = self.serve(callback)
        self.addCleanup(release.set)
        body = self.completion()

        def submit():
            try:
                response.append(self.request(port, "/gst-v21/complete", body))
            except Exception as exc:
                errors.append(type(exc).__name__)

        requester = threading.Thread(target=submit, daemon=True)
        requester.start()
        try:
            self.assertTrue(entered.wait(0.8))
            self.assertTrue(capture.EVIDENCE.exists())
            before = capture.EVIDENCE.read_bytes()
            self.assertFalse(server.finish_requests(timeout=0.02))

            def drain():
                drain_result.append(server.finish_requests(timeout=0.5))
                drained.set()

            waiter = threading.Thread(target=drain, daemon=True)
            waiter.start()
            self.assertFalse(drained.wait(0.02), "drain returned while completion was still running")
            release.set()
            self.assertTrue(drained.wait(0.7))
            self.assertEqual(drain_result, [True])
            self.assertTrue(stop.wait(0.7))
            self.assertTrue(closed.wait(0.7))
            waiter.join(0.2)
            self.assertEqual(capture.EVIDENCE.read_bytes(), before)
            self.assertTrue(self.receipt.exists())
        finally:
            release.set()
            requester.join(0.8)
        self.assertFalse(requester.is_alive())
        self.assertFalse(errors)
        self.assertEqual(response[0][0], 200)
        self.assertTrue(response[0][1]["signature_verified"])
        self.assertFalse(response[0][1]["formal_effect_authorized"])


class ProxyIsolationTests(unittest.TestCase):
    @staticmethod
    def baseline():
        return {"TCP": {"8444": {"HTTPS": True}},
                "Web": {capture.RP_ID + ":8444": {
                    "Handlers": {"/": {"Proxy": "http://127.0.0.1:8444"}}
                }}}

    def test_only_owned_9122_proxy_changes_and_8444_is_preserved(self):
        before = self.baseline()
        live = copy.deepcopy(before)
        calls = []

        def fake_command(args):
            calls.append(list(args))
            if args == ["status", "--json"]:
                return json.dumps(live)
            if args == ["--bg", "--https=9122", "http://127.0.0.1:9122"]:
                expected = operator.TemporaryProxy.expected()
                live["TCP"]["9122"] = expected["TCP"]
                live["Web"].update(expected["Web"])
                return ""
            if args == ["--https=9122", "off"]:
                live["TCP"].pop("9122", None)
                live["Web"].pop(capture.RP_ID + ":9122", None)
                return ""
            raise AssertionError("unexpected proxy operation")

        with mock.patch.object(operator.TemporaryProxy, "command", side_effect=fake_command):
            proxy = operator.TemporaryProxy()
            proxy.open()
            result = proxy.close()
        self.assertEqual(live, before)
        self.assertTrue(result["temporary_proxy_removed"])
        self.assertTrue(result["permanent_proxy_unchanged"])
        self.assertNotIn(["reset"], calls)

    def test_existing_9122_is_not_taken_over(self):
        live = self.baseline()
        live["TCP"]["9122"] = {"HTTPS": True}
        with mock.patch.object(operator.TemporaryProxy, "command", return_value=json.dumps(live)) as command:
            proxy = operator.TemporaryProxy()
            with self.assertRaises(PermissionError):
                proxy.open()
        self.assertEqual(command.call_args_list, [mock.call(["status", "--json"])])
        self.assertFalse(proxy.owned)

    def test_unexpected_created_proxy_is_not_removed_as_if_owned(self):
        before = self.baseline()
        live = copy.deepcopy(before)
        calls = []

        def fake_command(args):
            calls.append(list(args))
            if args == ["status", "--json"]:
                return json.dumps(live)
            if args == ["--bg", "--https=9122", "http://127.0.0.1:9122"]:
                live["TCP"]["9122"] = {"HTTPS": True}
                live["Web"][capture.RP_ID + ":9122"] = {
                    "Handlers": {"/": {"Proxy": "http://127.0.0.1:59999"}}
                }
                return ""
            raise AssertionError("unexpected proxy must not be switched off")

        with mock.patch.object(operator.TemporaryProxy, "command", side_effect=fake_command):
            proxy = operator.TemporaryProxy()
            with self.assertRaises(PermissionError):
                proxy.open()
            observed = copy.deepcopy(live)
            with self.assertRaises(PermissionError):
                proxy.close()
        self.assertEqual(live, observed)
        self.assertEqual(operator.TemporaryProxy.permanent(live), before)
        self.assertNotIn(["--https=9122", "off"], calls)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"schema": "SYNTHETIC_MOBILE_CLOSEOUT_TEST_METRICS/1.0",
                      "synthetic_only": True, "production_credentials_accessed": False,
                      "tests_run": result.testsRun, "failures": len(result.failures),
                      "errors": len(result.errors), "metrics": METRICS}, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
