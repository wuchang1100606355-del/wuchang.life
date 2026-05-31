#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path("/home/taiji_admin/Taiji_Hub")
LANGUAGE_PATH = ROOT / "topology" / "7d_bagua_metric_language.json"
MESH_PATH = ROOT / "topology" / "7d_formation_mesh.json"
GEOSPATIAL_TOPOLOGY_PATH = ROOT / "topology" / "7d_geospatial_topology.json"
LOG_PATH = ROOT / "logs" / "7d_formation_runtime.jsonl"
STATE_PATH = ROOT / "state" / "7d_bagua_green_checkpoint_latest.json"

NODE = "MSI"
PROTOCOL = "TEFMP-0.1"
RUNTIME = "7D"
BIND_HOST = "127.0.0.1"
BIND_PORT = 8127
EXPECTED_PREFIX = ["x", "y", "z", "time", "scale"]
FORMATION_BY_NAME = {
    "TIAN": "000",
    "DI": "001",
    "FENG": "010",
    "YUN": "011",
    "LONG": "100",
    "HU": "101",
    "NIAO": "110",
    "SHE": "111",
}
SECRET_CLASSES = {"secret", "oauth_token", "service_account_key", "password"}
PRIVATE_CLASSES = {"identity", "private"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def write_audit(event: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"time": now_iso(), "node": NODE, **event}
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def packet_text(packet: Dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, sort_keys=True).lower()


def route_mentions_cloud(packet: Dict[str, Any]) -> bool:
    route = packet.get("route", {})
    values = [packet.get("actor"), packet.get("target"), route.get("from"), route.get("to")]
    text = " ".join(str(v).lower() for v in values if v is not None)
    return any(term in text for term in ("cloud", "cloud_ai", "long"))


def has_metric_gate(packet: Dict[str, Any]) -> bool:
    route = packet.get("route", {})
    gates = packet.get("gates", [])
    if isinstance(gates, str):
        gates = [gates]
    return route.get("gate") == "metric_gate" or "metric_gate" in gates


def has_complete_audit(packet: Dict[str, Any]) -> bool:
    audit = packet.get("audit")
    if not isinstance(audit, dict):
        return False
    return bool(audit.get("required") is True and audit.get("actor") and audit.get("time") and audit.get("reason"))


def hazard_check(packet: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    hazards: List[Dict[str, str]] = []
    text = packet_text(packet)
    payload_class = str(packet.get("payload_class", "")).lower()
    operation = str(packet.get("operation", packet.get("action", ""))).lower()
    target = str(packet.get("target", "")).lower()
    actor = str(packet.get("actor", packet.get("audit", {}).get("actor", ""))).lower()

    code = packet.get("code")
    if not isinstance(code, list) or len(code) != 7:
        hazards.append({"id": "H001", "name": "modify_5d_prefix", "level": "L3_metric_hazard"})
    if packet.get("mutate_5d_prefix") is True or packet.get("prefix_mutation") is True:
        hazards.append({"id": "H001", "name": "modify_5d_prefix", "level": "L3_metric_hazard"})
    attempted = packet.get("attempted_code_fields")
    if attempted is not None and attempted[:5] != EXPECTED_PREFIX:
        hazards.append({"id": "H001", "name": "modify_5d_prefix", "level": "L3_metric_hazard"})

    writes_real_state = any(word in operation for word in ("write", "commit", "mutate", "update"))
    real_target = any(word in target for word in ("odoo", "database", "device", "policy", "runtime", "state"))
    if actor == "cloud_ai" and writes_real_state and real_target:
        hazards.append({"id": "H002", "name": "cloud_direct_write_real_state", "level": "L3_metric_hazard"})

    if payload_class in SECRET_CLASSES or any(token in text for token in ("oauth_token", "service_account_key", "production_password")):
        hazards.append({"id": "H003", "name": "secret_exfiltration", "level": "L3_metric_hazard"})

    raw_identity_terms = ("raw_identity", "raw line id", "raw_line_id", "member_record", "private_personal_data")
    if route_mentions_cloud(packet) and (payload_class in PRIVATE_CLASSES or any(term in text for term in raw_identity_terms)):
        hazards.append({"id": "H004", "name": "raw_identity_to_cloud", "level": "L3_metric_hazard"})

    odoo_write = "odoo" in target and writes_real_state
    if odoo_write and (not has_metric_gate(packet) or not has_complete_audit(packet)):
        hazards.append({"id": "H005", "name": "odoo_direct_mutation_without_metric_gate", "level": "L3_metric_hazard"})

    policy_change = "policy" in target and writes_real_state
    if policy_change:
        required = ("checkpoint", "impact_analysis", "rollback", "audit")
        if any(item not in text for item in required):
            hazards.append({"id": "H006", "name": "policy_unlocked_mutation", "level": "L3_metric_hazard"})

    canonical_unit = str(packet.get("canonical_unit", "")).lower()
    if canonical_unit == "raw_plaintext_context" or packet.get("raw_plaintext_context") is True:
        hazards.append({"id": "H007", "name": "raw_plaintext_as_canonical_unit", "level": "L3_metric_hazard"})

    unique = []
    seen = set()
    for hazard in hazards:
        if hazard["id"] not in seen:
            unique.append(hazard)
            seen.add(hazard["id"])
    return ("block" if unique else "allow"), unique


def validate_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    decision, hazards = hazard_check(packet)
    formation_bits = str(packet.get("formation_bits", ""))
    formation = str(packet.get("formation", ""))
    mesh = load_json(MESH_PATH, {})
    formations = mesh.get("formations", {})
    errors = []

    if formation_bits not in formations:
        errors.append("unknown_formation_bits")
    if formation and FORMATION_BY_NAME.get(formation) != formation_bits:
        errors.append("formation_bits_name_mismatch")
    if packet.get("node") not in (None, NODE):
        errors.append("node_mismatch")
    if packet.get("protocol") not in (None, PROTOCOL):
        errors.append("protocol_mismatch")
    if packet.get("runtime") not in (None, RUNTIME):
        errors.append("runtime_mismatch")

    if errors and decision == "allow":
        decision = "block"
    return {
        "decision": decision,
        "hazards": hazards,
        "errors": errors,
        "node": NODE,
        "runtime": RUNTIME,
        "protocol": PROTOCOL,
    }


def route_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    validation = validate_packet(packet)
    mesh = load_json(MESH_PATH, {})
    route_type = packet.get("route_type", "IO_EVENT")
    route = mesh.get("route_rules", {}).get(route_type)
    return {
        **validation,
        "route_type": route_type,
        "route": route,
        "committed": False,
        "note": "LONG derivation and DI persistence require governance gates; this endpoint does not mutate real state.",
    }


def health() -> Dict[str, Any]:
    return {
        "service": "7d_formation_runtime",
        "runtime": RUNTIME,
        "protocol": PROTOCOL,
        "node": NODE,
        "status": "running",
        "bind": f"{BIND_HOST}:{BIND_PORT}",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "TaijiFormationRuntime/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        write_audit({"kind": "http_access", "client": self.client_address[0], "message": fmt % args})

    def send_json(self, status: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(200, health())
        elif self.path == "/state":
            state = load_json(STATE_PATH, {})
            self.send_json(200, {"service": "7d_formation_runtime", "node": NODE, "state": state})
        elif self.path == "/formations":
            mesh = load_json(MESH_PATH, {})
            self.send_json(200, {"node": NODE, "formations": mesh.get("formations", {})})
        elif self.path == "/topology":
            self.send_json(200, {
                "language": load_json(LANGUAGE_PATH, {}),
                "mesh": load_json(MESH_PATH, {}),
                "geospatial_topology": load_json(GEOSPATIAL_TOPOLOGY_PATH, {})
            })
        else:
            self.send_json(404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:
        try:
            packet = self.read_json()
            if self.path == "/packet/validate":
                result = validate_packet(packet)
            elif self.path == "/packet/route":
                result = route_packet(packet)
            elif self.path == "/hazard-check":
                decision, hazards = hazard_check(packet)
                result = {"decision": decision, "hazards": hazards, "node": NODE}
            else:
                self.send_json(404, {"error": "not_found", "path": self.path})
                return
            write_audit({"kind": "packet", "path": self.path, "decision": result.get("decision"), "hazards": result.get("hazards", [])})
            self.send_json(200, result)
        except json.JSONDecodeError as exc:
            self.send_json(400, {"error": "invalid_json", "detail": str(exc)})
        except Exception as exc:
            write_audit({"kind": "runtime_error", "path": self.path, "error": str(exc)})
            self.send_json(500, {"error": "internal_error", "detail": str(exc)})


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_audit({"kind": "runtime_start", "bind": f"{BIND_HOST}:{BIND_PORT}"})
    httpd = ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
