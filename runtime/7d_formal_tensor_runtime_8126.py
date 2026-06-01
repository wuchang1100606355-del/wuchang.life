#!/usr/bin/env python3
import json
import pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

ROOT = pathlib.Path.home() / "Taiji_Hub"

def read_json(path, default=None):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))

class Handler(BaseHTTPRequestHandler):
    def _send(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        now = datetime.now(timezone.utc).isoformat()

        if self.path in ["/", "/health"]:
            self._send({
                "service": "7d_formal_tensor_runtime",
                "runtime": "7D",
                "protocol": "TEFMP-0.1",
                "node": "MSI",
                "status": "running",
                "bind": "127.0.0.1:8126",
                "time": now
            })
            return

        if self.path == "/state":
            self._send({
                "runtime_state": read_json("state/runtime_7d_state.json", {}),
                "virtual_state": read_json("state/7d_virtual_state.json", {}),
                "cloud_policy": read_json("policies/7d_cloud_ai_policy.json", {}),
                "topology": read_json("topology/7d_ai_io_odoo_metric_tensor_topology.json", {})
            })
            return

        if self.path == "/packet":
            self._send(read_json("state/runtime_7d_packet.example.json", {}))
            return

        self._send({"error": "not_found", "path": self.path}, 404)

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8126), Handler)
    server.serve_forever()
