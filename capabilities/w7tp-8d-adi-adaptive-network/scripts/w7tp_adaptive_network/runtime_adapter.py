"""Bounded system-level runtime adapter for the existing adaptive network provider.

Only local, read-only application health is registered here. All decisions
come from consumer.resolve_service; this adapter does not grant Total Field authority.
"""
from __future__ import annotations

import hashlib
import json
import ipaddress
import re
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, UnixStreamServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .consumer import resolve_service
from .failover import evaluate_binding_failover
from .observer import observe_local

ROOT = Path(__file__).resolve().parents[2]
SERVICE = "NATIVE_ADI_LOCAL_HEALTH"
TARGET = "http://127.0.0.1:9110/health"
INTENT = "READ_ONLY_NATIVE_ADI_HEALTH"
TTL = 30
REMOTE_INTENT = "MSI_READ_ONLY_NATIVE_ADI_HEALTH"
REMOTE_EVIDENCE = Path.home() / ".local/share/w7tp-adaptive-network/state/msi-observation.json"
ACTIVATION_MARKER = Path.home() / ".local/share/w7tp-adaptive-network/state/activation-gates.json"
GATES = ("SOURCE_BOUND", "SOURCE_ZONE_BOUND", "INTERFACE_BOUND",
         "ROUTE_BOUND", "TARGET_BOUND", "TARGET_ZONE_BOUND",
         "SERVICE_PASS", "APPLICATION_PASS", "RESPONSE_VERIFIED")


def load_contract(root: Path = ROOT) -> dict:
    manifest = json.loads((root / "manifest.json").read_text())
    if (manifest.get("skill_id") != "w7tp-8d-adi-adaptive-network"
            or manifest.get("version") != "0.2.0-candidate.1"
            or manifest.get("entrypoint") != "scripts/network_skill.py"
            or manifest.get("canonical") is not False):
        raise ValueError("SYSTEM_RUNTIME_CONTRACT_INVALID")
    sums = (root / "SOURCE_SHA256SUMS").read_text().splitlines()
    for line in sums:
        digest, name = line.split(None, 1)
        name = name.strip()
        if not name.startswith("capabilities/w7tp-8d-adi-adaptive-network/"):
            raise ValueError("SOURCE_PATH_OUTSIDE_CAPABILITY")
        relative = name.split("capabilities/w7tp-8d-adi-adaptive-network/", 1)[1]
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("SOURCE_SHA256_MISMATCH:" + relative)
    return manifest


def activation_gates_pass(root: Path = ROOT) -> bool:
    """Operational evidence gate; never a Total Field or Canonical decision."""
    try:
        marker = json.loads(ACTIVATION_MARKER.read_text())
        if marker.get("schema") != "SYSTEM_ADAPTIVE_NETWORK_RUNTIME_GATE/1":
            return False
        required = (
            "SYSTEM_RUNTIME_CONTRACT", "INSTALLATION", "RUNTIME_ENTRYPOINT",
            "CONTINUOUS_OBSERVER", "REAL_CONSUMER_BINDING", "PER_INTENT_BINDING",
            "PER_BINDING_FAILOVER", "RESTART_RECOVERY", "FAIL_CLOSED",
        )
        if any(marker.get("gates", {}).get(key) != "PASS" for key in required):
            return False
        if marker.get("canonical_status") != "CANDIDATE_ONLY":
            return False
        if marker.get("source_sha256sum_sha256") != hashlib.sha256(
            (root / "SOURCE_SHA256SUMS").read_bytes()).hexdigest():
            return False
        if marker.get("runtime_contract_sha256") != hashlib.sha256(
            (root / "deploy/w7tp-adaptive-network.service").read_bytes()).hexdigest():
            return False
        for key in ("failover_evidence", "restart_evidence"):
            evidence = (ACTIVATION_MARKER.parent / marker[key]["filename"]).resolve()
            if evidence.parent != ACTIVATION_MARKER.parent or not evidence.is_file():
                return False
            if hashlib.sha256(evidence.read_bytes()).hexdigest() != marker[key]["sha256"]:
                return False
        return True
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def probe(url: str = TARGET) -> bool:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=2) as response:
        document = json.loads(response.read(16384))
        return response.status == 200 and document.get("service") == "W7TP_NATIVE_ADI_AGENT" and document.get("state") == "PASS"


class AdaptiveRuntime:
    def __init__(self, observer=observe_local, application_probe=probe, clock=time.time):
        self.observer = observer
        self.application_probe = application_probe
        self.clock = clock
        self.lock = threading.RLock()
        self.current = None
        self.bindings = {}
        self.failover_bindings = {}
        self.remote_valid_until_epoch = 0.0
        self.last_error = "RECOVERY_NO_FRESH_EVIDENCE"
        self.observation_count = 0
        self.route_drift = "FIRST_OBSERVATION"
        self.dns_drift = "FIRST_OBSERVATION"
        self.process_started_at = datetime.now(timezone.utc).isoformat()

    def refresh(self):
        # Never retain a past decision when a new observation fails.
        with self.lock:
            previous_remote = self.bindings.get(REMOTE_INTENT)
            previous_failover = dict(self.failover_bindings)
            self.current = None
            self.bindings = {}
            self.failover_bindings = {}
            self.remote_valid_until_epoch = 0.0
            self.last_error = "REFRESH_IN_PROGRESS"
        try:
            local = self.observer()
            command = local.get("command_evidence", {})
            if not isinstance(command, dict) or any(
                command.get(key, {}).get("returncode") != 0
                for key in ("links", "addresses", "routes_v4")
            ):
                raise ValueError("LOCAL_NETWORK_EVIDENCE_INCOMPLETE")
            if not any(row.get("ifname") == "lo" and "UP" in row.get("flags", [])
                       for row in local.get("links", [])):
                raise ValueError("LOOPBACK_NOT_UP")
            if not self.application_probe():
                raise ValueError("APPLICATION_HEALTH_FAILED")
            observed = datetime.now(timezone.utc).isoformat()
            path = {"path_id": "LOCAL_ADI_LOOPBACK", "path_type": "LOOPBACK_SERVICE_PATH",
                    "available": True, "host_reachable": True, "service_reachable": True,
                    "qualified": True, "identity_state": "OBSERVED_PARTIAL",
                    "target": "127.0.0.1:9110", "interface": "lo",
                    "service_identity": SERVICE}
            gates = {gate: True for gate in GATES}
            decision = resolve_service(
                INTENT, "taiji01", "taiji01", SERVICE,
                source_zone="ZONE_CORE", target_zone="ZONE_CORE",
                paths=[path], verification={"LOCAL_ADI_LOOPBACK": gates},
                permitted_paths=["LOOPBACK_SERVICE_PATH"], observed_at=observed,
                ttl_seconds=TTL)
            if not decision.get("authorized"):
                raise ValueError("BINDING_NOT_VERIFIED")
            route_hash = hashlib.sha256(json.dumps(
                [local.get("routes_v4"), local.get("routes_v6")],
                sort_keys=True).encode()).hexdigest()
            dns_hash = hashlib.sha256(
                local.get("dns_summary", "").encode()).hexdigest()
            now = self.clock()
            remote = None
            remote_expiry = 0.0
            remote_paths = []
            remote_failover = previous_failover.get(REMOTE_INTENT, {})
            try:
                packet = json.loads(REMOTE_EVIDENCE.read_text())
                if (packet.get("schema") != "MSI_TWO_PATH_HEALTH_OBSERVATION/1"
                        or packet.get("source_node") != "MSI"
                        or abs(time.time() - packet.get("observed_at_epoch", 0)) > TTL):
                    raise ValueError("REMOTE_EVIDENCE_STALE_OR_INVALID")
                remote_expiry = packet["observed_at_epoch"] + TTL
                verification = {}
                for kind, path_id in (
                    ("LAN_IPV4", "MSI_ADI_LAN"),
                    ("TAILSCALE_IPV4", "MSI_ADI_TAILSCALE")):
                    row = packet["paths"][kind]
                    iface = row.get("interface")
                    try:
                        source = ipaddress.ip_address(row.get("source_ipv4", ""))
                        interface_bound = (
                            bool(re.fullmatch(r"eth[0-9]+", iface or ""))
                            and source in ipaddress.ip_network("192.168.50.0/24")
                            if kind == "LAN_IPV4"
                            else iface == "tailscale0"
                            and source in ipaddress.ip_network("100.64.0.0/10"))
                    except ValueError:
                        interface_bound = False
                    qualified = (interface_bound and
                                 row.get("route_bound") is True and
                                 row.get("application_pass") is True)
                    remote_paths.append({
                        "path_id": path_id, "path_type": kind,
                        "available": qualified, "host_reachable": qualified,
                        "service_reachable": qualified, "qualified": qualified,
                        "identity_state": "OBSERVED_PARTIAL",
                        "interface": iface, "service_identity": SERVICE,
                        "target": "taiji01:9110-over-existing-ssh",
                    })
                    verification[path_id] = {gate: qualified for gate in GATES}
                remote = resolve_service(
                    REMOTE_INTENT, "MSI", "taiji01", SERVICE,
                    source_zone="ZONE_CORE", target_zone="ZONE_CORE",
                    paths=remote_paths, verification=verification,
                    permitted_paths=["LAN_IPV4", "TAILSCALE_IPV4"],
                    path_preference=["LAN_IPV4", "TAILSCALE_IPV4"],
                    observed_at=observed, ttl_seconds=TTL)
                if previous_remote and previous_remote.get("authorized"):
                    old_path = previous_remote.get("selected_path")
                    if old_path != remote.get("selected_path"):
                        outcome = evaluate_binding_failover(
                            {**previous_remote, "observed_at": observed}, remote_paths,
                            verification)
                        if outcome.get("selected_path") == remote.get("selected_path"):
                            transition_state = outcome.get("binding_state")
                        elif (remote.get("selected_path") == "MSI_ADI_LAN"
                              and "MSI_ADI_LAN" in remote.get("qualified_path_set", [])):
                            transition_state = "ORIGINAL_REQUALIFIED_ACTIVE"
                        else:
                            raise ValueError("FAILOVER_EVALUATOR_MISMATCH")
                        remote_failover = {
                            "previous_path": old_path,
                            "selected_path": remote.get("selected_path"),
                            "binding_state": transition_state,
                            "observed_at": observed,
                            "other_bindings_modified": False}
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                remote = None  # Remote absence cannot invalidate the local binding.
                remote_expiry = 0.0
                remote_failover = {}
            with self.lock:
                path_set = ["LOCAL_ADI_LOOPBACK"]
                if remote:
                    path_set += remote.get("available_path_set", [])
                prior = getattr(self, "_prior_hashes", None)
                self.route_drift = (
                    "UNCHANGED" if prior and route_hash == prior[0]
                    else "CHANGED" if prior else "FIRST_OBSERVATION")
                self.dns_drift = (
                    "UNCHANGED" if prior and dns_hash == prior[1]
                    else "CHANGED" if prior else "FIRST_OBSERVATION")
                self._prior_hashes = (route_hash, dns_hash)
                self.current = {
                    "observed_at": observed, "valid_until_monotonic": now + TTL,
                    "network_evidence_sha256": hashlib.sha256(
                        json.dumps(local, sort_keys=True).encode()).hexdigest(),
                    "available_path_set": sorted(set(path_set)),
                    "qualified_path_set": sorted(set(path_set)),
                    "dns_summary_sha256": dns_hash,
                    "route_summary_sha256": route_hash,
                    "zone_state": {
                        "ZONE_CORE": "OBSERVED_LOCAL_ONLY",
                        "ZONE_GUEST_SERVICE": "UNOBSERVED",
                        "ZONE_IOT": "UNOBSERVED",
                        "ZONE_MANAGEMENT": "UNOBSERVED",
                        "ZONE_TAILSCALE": "UNOBSERVED",
                        "ZONE_WAN": "UNOBSERVED",
                        "ZONE_FUTURE_PUBLIC_SERVICE": "UNOBSERVED",
                    },
                }
                self.bindings = {INTENT: decision}
                self.remote_valid_until_epoch = remote_expiry
                if remote:
                    self.bindings[REMOTE_INTENT] = remote
                self.failover_bindings = {REMOTE_INTENT: remote_failover} if remote_failover else {}
                self.last_error = None
                self.observation_count += 1
        except Exception as exc:
            with self.lock:
                self.last_error = type(exc).__name__ + ":" + str(exc)
            return False
        return True

    def status(self):
        with self.lock:
            fresh = self.current is not None and self.clock() < self.current["valid_until_monotonic"]
            bindings = dict(self.bindings) if fresh else {}
            remote_fresh = time.time() < self.remote_valid_until_epoch
            if not remote_fresh:
                bindings.pop(REMOTE_INTENT, None)
            active = sorted({path for binding in bindings.values()
                             for path in binding.get("active_path_set", [])})
            operational_active = bool(
                fresh and REMOTE_INTENT in bindings
                and bindings[REMOTE_INTENT].get("authorized")
                and activation_gates_pass())
            return {
                "capability_id": "w7tp-8d-adi-adaptive-network",
                "scope": "TAIJI_HUB_SYSTEM_LEVEL",
                "version": "v0.2.0-candidate.1",
                "canonical_status": "CANDIDATE_ONLY",
                "total_field_decision": "NOT_RUN",
                "runtime_state": ("ACTIVE" if operational_active
                                  else "OBSERVER_RUNNING_LIMITED" if fresh else "HOLD"),
                "health": ("PASS_LOCAL_AND_MSI" if fresh and REMOTE_INTENT in bindings
                           else "PASS_LOCAL_ONLY" if fresh else "HOLD"),
                "continuous_observer": True,
                "observed_at": self.current["observed_at"] if fresh else None,
                "process_started_at": self.process_started_at,
                "observation_count": self.observation_count,
                "available_path_set": (
                    self.current["available_path_set"] if remote_fresh
                    else ["LOCAL_ADI_LOOPBACK"] if fresh else []),
                "qualified_path_set": (
                    self.current["qualified_path_set"] if remote_fresh
                    else ["LOCAL_ADI_LOOPBACK"] if fresh else []),
                "active_path_set": active,
                "intent_path_bindings": dict(bindings),
                "failover_bindings": self.failover_bindings if fresh and remote_fresh else {},
                "zone_state": self.current["zone_state"] if fresh else {},
                "network_evidence_sha256": self.current["network_evidence_sha256"] if fresh else None,
                "dns_summary_sha256": self.current["dns_summary_sha256"] if fresh else None,
                "route_summary_sha256": self.current["route_summary_sha256"] if fresh else None,
                "route_drift": self.route_drift if fresh else "UNKNOWN",
                "dns_drift": self.dns_drift if fresh else "UNKNOWN",
                "binding_health": {key: ("PASS" if value.get("authorized") else "HOLD")
                                   for key, value in bindings.items()},
                "last_error": self.last_error,
                "port_9002_is_d8": False,
                "fail_closed": True,
            }

    def resolve(self, intent_id):
        state = self.status()
        if intent_id not in (INTENT, REMOTE_INTENT) or not state["health"].startswith("PASS_"):
            return {"decision": "HOLD", "reason": "UNKNOWN_OR_STALE_INTENT"}
        return state["intent_path_bindings"].get(intent_id, {
            "decision": "HOLD", "reason": "REMOTE_EVIDENCE_MISSING_OR_STALE"})


class UnixHTTPServer(ThreadingMixIn, UnixStreamServer):
    daemon_threads = True

def socket_path():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        raise ValueError("XDG_RUNTIME_DIR_REQUIRED")
    return Path(runtime_dir) / "w7tp-adaptive-network.sock"

def serve(runtime: AdaptiveRuntime, path=None):
    path = Path(path) if path else socket_path()
    if path.exists():
        if not path.is_socket():
            raise ValueError("SOCKET_PATH_OCCUPIED")
        path.unlink()  # Previous process is gone; the new process starts HOLD.

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = urlsplit(self.path)
            status = runtime.status()
            if parts.path == "/resolve_service":
                value = parse_qs(parts.query).get("intent_id", [""])[0]
                result = runtime.resolve(value)
            elif parts.path == "/health":
                result = {"health": status["health"], "fail_closed": status["fail_closed"]}
            elif parts.path in ("/status", "/observe", "/bindings", "/decision",
                                "/failover_state", "/zone_state"):
                key = {"/observe": "network_evidence_sha256",
                       "/bindings": "intent_path_bindings",
                       "/decision": "intent_path_bindings",
                       "/failover_state": "failover_bindings",
                       "/zone_state": "zone_state"}.get(parts.path)
                result = status if key is None else {key: status[key]}
            else:
                self.send_error(404)
                return
            encoded = json.dumps(result, sort_keys=True).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):
            pass

    server = UnixHTTPServer(str(path), Handler)
    os.chmod(path, 0o600)
    def observer_loop():
        while True:
            runtime.refresh()
            time.sleep(10)
    threading.Thread(target=observer_loop, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
        path.unlink(missing_ok=True)
