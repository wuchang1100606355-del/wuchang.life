#!/usr/bin/env python3
"""Single-shot operator for the existing native GST mobile approval capture.

Only gst_mobile_approval_first verifies assertions. Factual receipts never issue
a Founder role, canonical promotion, runtime authority, or a machine signature.
The fixed native contract is explicit; arbitrary contracts are rejected.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gst_mobile_approval_first as capture
import gst_mobile_approval_server as native_http

DEFAULT_CONTRACT = capture.ROOT / capture.BUNDLE / 'PROMOTION_CONTRACT.json'
DEFAULT_TARGET = capture.ROOT / capture.LEAF / 'FOUNDER_RATIFICATION_RECEIPT.json'
RECEIPT_SCHEMA = 'GST_V21_FOUNDER_RATIFICATION_EVIDENCE_RECEIPT/2.0'
require = capture.require

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def checked_target(path):
    path = Path(path).absolute()
    capture.safe_path(path)
    require(path.parent.is_dir(), 'RECEIPT_PARENT_MISSING')
    require(path.parent.stat().st_uid == os.geteuid(), 'RECEIPT_PARENT_OWNER')
    if path.exists():
        info = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid(), 'RECEIPT_TARGET_OWNER_OR_TYPE')
    return path

def publish_receipt(path, value, expected_preimage=None):
    """Publish atomically; a different existing receipt needs its reviewed hash."""
    path = checked_target(path)
    raw = capture.canon(value) + b'\n'
    before = capture.raw_read(path) if path.exists() else None
    if before is not None:
        if json.loads(before) == value:
            return {'path': str(path), 'sha256': digest(before), 'reused': True}
        require(expected_preimage is not None and digest(before) == expected_preimage, 'RECEIPT_PREIMAGE_REVIEW_REQUIRED')
        history = capture.STATE / 'receipt-history'
        capture.private_dir(history)
        old = history / (digest(before) + '.json')
        if old.exists():
            require(capture.raw_read(old) == before, 'RECEIPT_HISTORY_CONFLICT')
        else:
            capture.persist_bytes_new(old, before)
    else:
        require(expected_preimage is None, 'RECEIPT_EXPECTED_PREIMAGE_MISSING')
    temporary = path.parent / ('.receipt-' + secrets.token_hex(16))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if before is None:
            os.link(temporary, path, follow_symlinks=False)
        else:
            require(capture.raw_read(path) == before, 'RECEIPT_PREIMAGE_DRIFT')
            os.replace(temporary, path)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        temporary.unlink(missing_ok=True)
    require(capture.raw_read(path) == raw, 'RECEIPT_READBACK_MISMATCH')
    return {'path': str(path), 'sha256': digest(raw), 'reused': False}

class ReceiptWriter:
    def __init__(self, fido, contract, target, expected_preimage=None):
        self.fido = fido
        self.contract = Path(contract).absolute()
        self.target = checked_target(target)
        self.expected_preimage = expected_preimage
        require(self.contract == DEFAULT_CONTRACT, 'NATIVE_FIXED_CONTRACT_REQUIRED')
        capture.raw_read(self.contract, capture.CONTRACT_SHA)
        self.sources = [Path(capture.__file__).absolute(), Path(native_http.__file__).absolute(), Path(__file__).absolute()]
        self.loaded_hashes = {str(p): digest(p.read_bytes()) for p in self.sources}
        self.result = None
        self.published_monotonic_ns = None

    def __call__(self, summary=None):
        raw = capture.raw_read(capture.EVIDENCE)
        proof = json.loads(raw)
        verified = capture.verify_proof(self.fido, proof)
        require(verified.get('signature_verified') is True, 'NATIVE_SIGNATURE_NOT_VERIFIED')
        verified['evidence_sha256'] = digest(raw)
        capture.raw_read(self.contract, capture.CONTRACT_SHA)
        for path in self.sources:
            require(digest(path.read_bytes()) == self.loaded_hashes[str(path)], 'LOADED_SOURCE_CHANGED')
        spec = capture.ROOT / capture.LEAF / 'SPECIFICATION.md'
        spec_sha = capture.INTENDED_POSTIMAGES[capture.LEAF + '/SPECIFICATION.md']
        capture.raw_read(spec, spec_sha)
        payload = proof['pending']['signed_payload']
        receipt = {
            'schema': RECEIPT_SCHEMA,
            'state': 'MOBILE_SIGNATURE_VERIFIED_NATIVE_AUTHORITY_PENDING',
            'status': 'EVIDENCE_VERIFIED_NOT_CANONICAL_RATIFICATION',
            'contract_ref': str(self.contract), 'contract_sha256': capture.CONTRACT_SHA,
            'specification_sha256': spec_sha,
            'evidence_file_path': str(capture.EVIDENCE), 'evidence_sha256': digest(raw),
            'signed_payload_sha256': digest(capture.canon(payload)),
            'public_credential_sha256': payload['public_credential_sha256'],
            'ceremony_id': proof['pending']['ceremony_id'],
            'verified_at': proof['verified_at'],
            'verified_at_source': proof.get('verified_at_source', 'LOCAL_SERVER_OBSERVATION'),
            'signature_verified': True, 'user_presence_verified': True,
            'user_verification_verified': True, 'human_approval_intent_captured': True,
            'authenticator_evidence': 'WEBAUTHN_PUBLIC_KEY_ASSERTION_WITH_UP_AND_UV',
            'biometric_method_attested': False,
            'signed_origin': payload['bindings']['origin'], 'rp_id': payload['bindings']['rp_id'],
            'approval_scope': payload['bindings']['scope'],
            'founder_binding_verified': False, 'formal_effect_authorized': False,
            'canonical_promotion_executed': False, 'runtime_activation_authorized': False,
            'ed25519_grant_issued': False, 'machine_private_key_used': False,
            'native_verifier_source_sha256': self.loaded_hashes[str(Path(capture.__file__).absolute())],
            'governance_correction_ref': capture.LEAF + '/PROMOTION_GOVERNANCE_CORRECTION.json',
        }
        require(capture.raw_read(capture.EVIDENCE) == raw, 'HUMAN_PROOF_CHANGED_DURING_READBACK')
        replacing_existing = self.target.exists()
        self.result = publish_receipt(self.target, receipt, self.expected_preimage)
        self.published_monotonic_ns = time.monotonic_ns()
        self.expected_preimage = self.result['sha256']
        return {**verified, 'receipt': self.result,
                'receipt_repair_executed': replacing_existing and not self.result['reused'],
                'receipt_publication_scope': 'D5_OPERATOR_ACTION_NOT_AUTHORITY_FROM_SIGNATURE',
                'message': '手機簽章已驗證，證據回執已原子保存；正式權威狀態另據原生裁決。'}

class TemporaryProxy:
    """Own only a newly-created 9122 endpoint; never reset Tailscale Serve."""
    def __init__(self):
        self.owned = False
        self.before = None
        self.created_endpoint = None

    @staticmethod
    def command(args):
        p = subprocess.run(['tailscale', 'serve', *args], capture_output=True, text=True, timeout=8)
        require(p.returncode == 0, 'TAILSCALE_SERVE_COMMAND_FAILED')
        return p.stdout

    @classmethod
    def status(cls):
        value = json.loads(cls.command(['status', '--json']))
        require(isinstance(value, dict), 'TAILSCALE_SERVE_STATUS_INVALID')
        return value

    @staticmethod
    def endpoint(config):
        return {'TCP': config.get('TCP', {}).get('9122'),
                'Web': {k: v for k, v in config.get('Web', {}).items() if k.endswith(':9122')}}

    @staticmethod
    def permanent(config):
        value = json.loads(json.dumps(config))
        value.get('TCP', {}).pop('9122', None)
        for key in list(value.get('Web', {})):
            if key.endswith(':9122'):
                value['Web'].pop(key)
        for key in ('TCP', 'Web'):
            if value.get(key) == {}:
                value.pop(key, None)
        return value

    @staticmethod
    def expected():
        return {'TCP': {'HTTPS': True},
                'Web': {capture.RP_ID + ':9122': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:9122'}}}}}

    def open(self):
        self.before = self.status()
        require(self.endpoint(self.before) == {'TCP': None, 'Web': {}}, 'TEMPORARY_PROXY_ALREADY_PRESENT')
        self.owned = True
        self.command(['--bg', '--https=9122', 'http://127.0.0.1:9122'])
        current = self.status()
        require(self.endpoint(current) == self.expected(), 'TEMPORARY_PROXY_UNEXPECTED_SHAPE')
        self.created_endpoint = self.expected()
        require(self.permanent(current) == self.permanent(self.before), 'PERMANENT_PROXY_CHANGED')

    def close(self):
        if not self.owned:
            return {'temporary_proxy_removed': True, 'proxy_created': False}
        current = self.status()
        endpoint = self.endpoint(current)
        require(endpoint in ({'TCP': None, 'Web': {}}, self.expected()), 'TEMPORARY_PROXY_OWNERSHIP_CHANGED')
        if endpoint != {'TCP': None, 'Web': {}}:
            self.command(['--https=9122', 'off'])
        final = self.status()
        require(self.endpoint(final) == {'TCP': None, 'Web': {}}, 'TEMPORARY_PROXY_NOT_REMOVED')
        require(self.permanent(final) == self.permanent(self.before), 'PERMANENT_PROXY_CHANGED')
        self.owned = False
        return {'temporary_proxy_removed': True, 'proxy_created': True, 'permanent_proxy_unchanged': True}

@contextlib.contextmanager
def single_operator():
    capture.private_dir(capture.STATE)
    fd = os.open(capture.STATE / '.single-shot.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'OPERATOR_LOCK_TYPE')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PermissionError('SIGNING_OPERATOR_ALREADY_RUNNING') from None
        yield
    finally:
        os.close(fd)

def run_once(args):
    require(args.port == 9122 and args.origin == capture.ORIGIN, 'EXACT_NATIVE_ORIGIN_AND_PORT_REQUIRED')
    require(1 <= args.timeout <= 900, 'SIGNING_TIMEOUT_OUT_OF_RANGE')
    fido = capture.make_server()
    writer = ReceiptWriter(fido, args.contract, args.target, args.replace_target_sha256)
    with single_operator():
        if capture.EVIDENCE.exists():
            started = time.monotonic_ns()
            result = writer()
            return {**result, 'mode': 'SAVED_PROOF_READBACK', 'new_ceremony_started': False,
                    'listener_opened': False, 'elapsed_ms': (time.monotonic_ns() - started) // 1000000}
        require(not args.reconcile_only, 'SAVED_HUMAN_PROOF_REQUIRED')
        capture.check_signing_inputs()
        capture.initialize_state()
        stop = threading.Event()
        proxy = TemporaryProxy()
        server = native_http.create_server(('127.0.0.1', args.port), fido_instance=fido, on_verified=writer, stop_event=stop)
        worker = None
        worker_started = False
        old_handlers = {}
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_handlers[sig] = signal.signal(sig, lambda *_: stop.set())
            proxy.open()
            worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
            worker.start()
            worker_started = True
            print(json.dumps({'state': 'READY_FOR_REAL_PHONE_APPROVAL', 'url': args.origin + '/gst-v21/',
                              'contract_sha256': capture.CONTRACT_SHA, 'expires_in_seconds': args.timeout,
                              'formal_effect_authorized': False}, ensure_ascii=False), flush=True)
            stop.wait(args.timeout)
        finally:
            try:
                requests_finished = server.finish_requests(timeout=5)
                if worker_started:
                    server.shutdown()
                    worker.join(timeout=0.3)
            finally:
                try:
                    server.server_close()
                    listener_closed_ns = time.monotonic_ns()
                finally:
                    try:
                        cleanup = proxy.close()
                    finally:
                        for sig, previous in old_handlers.items():
                            signal.signal(sig, previous)
        if writer.result is None:
            saved = capture.verify_proof(fido, capture.read(capture.EVIDENCE)) if capture.EVIDENCE.exists() else {}
            return {'state': 'SIGNATURE_SAVED_RECEIPT_PENDING' if saved else 'SIGNING_WINDOW_ENDED_WITHOUT_RECEIPT',
                    'signature_verified': saved.get('signature_verified', False), 'receipt_saved': False,
                    'completion_finished': requests_finished, 'formal_effect_authorized': False,
                    'listener_released': True, **cleanup}
        finish_ns = time.monotonic_ns()
        return {'state': 'MOBILE_SIGNATURE_AND_FACTUAL_RECEIPT_SAVED', 'signature_verified': True,
                'formal_effect_authorized': False, 'receipt': writer.result, 'listener_released': True,
                'receipt_to_listener_close_ms': (listener_closed_ns - writer.published_monotonic_ns) // 1000000,
                'receipt_to_cleanup_complete_ms': (finish_ns - writer.published_monotonic_ns) // 1000000,
                'cleanup_within_one_second': finish_ns - writer.published_monotonic_ns < 1000000000, **cleanup}

def main():
    parser = argparse.ArgumentParser(description='W7TP 原生真人簽章與事實回執單次工具；不自行授予正典權威')
    parser.add_argument('--contract', type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument('--target', type=Path, default=DEFAULT_TARGET)
    parser.add_argument('--port', type=int, default=9122)
    parser.add_argument('--origin', default=capture.ORIGIN)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--reconcile-only', action='store_true')
    parser.add_argument('--replace-target-sha256', help='Exact reviewed old receipt hash; preserves its preimage')
    try:
        result = run_once(parser.parse_args())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        if result.get('cleanup_within_one_second') is False:
            return 3
        return 0 if result.get('signature_verified') and result.get('receipt') else 2
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        reason = str(exc) if isinstance(exc, PermissionError) else type(exc).__name__
        print(json.dumps({'state': 'SIGNING_NOT_COMPLETED', 'reason_code': reason,
                          'formal_effect_authorized': False}, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

