#!/usr/bin/env python3
import json
import pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

ROOT = pathlib.Path.home() / "Taiji_Hub"
SCHEMA_PATH = ROOT / "schemas" / "utsl_schema.v0.1.json"
LOG_PATH = ROOT / "logs" / "utsl_runtime.jsonl"

NODE = "MSI"
BIND = "127.0.0.1"
PORT = 8128

def now():
    return datetime.now(timezone.utc).isoformat()

def read_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

def audit(event):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def result(action, level="L0_allow", reason="ok", details=None):
    return {
        "action": action,
        "level": level,
        "reason": reason,
        "details": details or {},
        "time": now()
    }

def validate_packet(packet):
    schema = read_schema()
    required = schema["canonical_packet"]["required_fields"]
    missing = [k for k in required if k not in packet]
    if missing:
        return result("block", "L3_metric_hazard", "missing_required_fields", {"missing": missing})

    dim_names = packet.get("dimension_names")
    tensor_code = packet.get("tensor_code")

    if not isinstance(dim_names, list) or not isinstance(tensor_code, list):
        return result("block", "L3_metric_hazard", "dimension_names_and_tensor_code_must_be_lists")

    if len(dim_names) != len(tensor_code):
        return result("block", "L3_metric_hazard", "dimension_count_mismatch", {
            "dimension_names": len(dim_names),
            "tensor_code": len(tensor_code)
        })

    five = schema["reserved_dimension_sets"]["5D"]
    if dim_names[:5] != five:
        return result("block", "L3_metric_hazard", "5d_prefix_modified", {
            "expected_prefix": five,
            "actual_prefix": dim_names[:5]
        })

    payload_class = str(packet.get("payload_class", "")).strip()
    if payload_class in schema["canonical_packet"]["blocked_payload_classes"]:
        return result("block", "L3_metric_hazard", "blocked_payload_class", {
            "payload_class": payload_class
        })

    formation = packet.get("formation", {})
    bits = formation.get("bits") if isinstance(formation, dict) else None
    if bits not in schema["bagua_opcode"]:
        return result("block", "L3_metric_hazard", "invalid_bagua_opcode", {"bits": bits})

    route = packet.get("route", {})
    audit_data = packet.get("audit", {})

    actor = route.get("actor") or audit_data.get("actor")
    target = route.get("target")
    gate = route.get("gate")

    if actor == "cloud_ai" and target in ["odoo", "database", "device", "policy", "real_state"]:
        return result("block", "L3_metric_hazard", "cloud_direct_write_real_state")

    if target == "odoo" and gate not in ["metric_gate", "risk_gate", "audit_gate"]:
        return result("block", "L3_metric_hazard", "odoo_mutation_without_metric_gate")

    if not audit_data.get("required", False):
        return result("block", "L3_metric_hazard", "audit_required_missing_or_false")

    return result("allow", "L1_allow_with_audit", "packet_valid", {
        "dimension_count": len(dim_names),
        "formation": schema["bagua_opcode"][bits],
        "payload_class": payload_class
    })

def route_packet(packet):
    schema = read_schema()
    check = validate_packet(packet)
    if check["action"] != "allow":
        return check

    bits = packet["formation"]["bits"]
    formation_name = schema["bagua_opcode"][bits]["name"]

    route_map = {
        "TIAN": ["DI", "FENG", "HU", "NIAO"],
        "DI": ["TIAN", "YUN", "NIAO"],
        "FENG": ["YUN", "LONG", "HU", "NIAO"],
        "YUN": ["LONG", "NIAO", "SHE", "TIAN"],
        "LONG": ["TIAN", "HU", "NIAO", "SHE"],
        "HU": ["TIAN", "DI", "NIAO"],
        "NIAO": ["TIAN", "FENG", "HU"],
        "SHE": ["FENG", "YUN", "LONG", "NIAO"]
    }

    return result("route", "L1_allow_with_audit", "route_resolved", {
        "from": formation_name,
        "next": route_map.get(formation_name, [])
    })

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        schema = read_schema()

        if self.path == "/health":
            self.send_json({
                "service": "utsl_runtime",
                "language": "UTSL",
                "language_name": "通用張量態語言",
                "version": "0.1",
                "runtime": "五常7維度數位陣型",
                "node": NODE,
                "status": "running",
                "bind": f"{BIND}:{PORT}",
                "time": now()
            })
            return

        if self.path == "/schema":
            self.send_json(schema)
            return

        if self.path == "/dimensions":
            self.send_json(schema["reserved_dimension_sets"])
            return

        if self.path == "/formations":
            self.send_json(schema["bagua_opcode"])
            return

        self.send_json({"error": "not_found", "path": self.path}, 404)

    def do_POST(self):
        try:
            packet = self.read_json_body()

            if self.path == "/packet/validate":
                r = validate_packet(packet)
                audit({"event": "utsl_packet_validate", "packet_ref": packet.get("payload_ref"), "result": r, "time": now()})
                self.send_json(r)
                return

            if self.path == "/packet/route":
                r = route_packet(packet)
                audit({"event": "utsl_packet_route", "packet_ref": packet.get("payload_ref"), "result": r, "time": now()})
                self.send_json(r)
                return

            if self.path == "/hazard-check":
                r = validate_packet(packet)
                audit({"event": "utsl_hazard_check", "packet_ref": packet.get("payload_ref"), "result": r, "time": now()})
                self.send_json(r)
                return

            self.send_json({"error": "not_found", "path": self.path}, 404)

        except Exception as e:
            self.send_json({"error": "exception", "message": repr(e), "time": now()}, 500)

def main():
    audit({"event": "utsl_runtime_start", "node": NODE, "bind": f"{BIND}:{PORT}", "time": now()})
    HTTPServer((BIND, PORT), Handler).serve_forever()

if __name__ == "__main__":
    main()
