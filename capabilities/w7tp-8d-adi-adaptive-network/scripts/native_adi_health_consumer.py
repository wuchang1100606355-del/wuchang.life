#!/usr/bin/env python3
"""Read-only consumer: resolves an existing application health endpoint."""
import json
import sys
import urllib.request
import http.client
import os
from pathlib import Path
from urllib.parse import quote

class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=3)
        self.path = path

    def connect(self):
        import socket
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(self.path)

def resolve(intent):
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        return {"decision": "HOLD"}
    connection = UnixConnection(str(Path(runtime_dir) / "w7tp-adaptive-network.sock"))
    try:
        connection.request("GET", "/resolve_service?intent_id=" + quote(intent))
        response = connection.getresponse()
        if response.status != 200:
            return {"decision": "HOLD"}
        return json.loads(response.read(16384))
    finally:
        connection.close()


def get(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=3) as response:
        return json.load(response)

def main():
    binding = resolve("READ_ONLY_NATIVE_ADI_HEALTH")
    if not binding.get("authorized") or binding.get("selected_path") != "LOCAL_ADI_LOOPBACK":
        return 2
    health = get("http://127.0.0.1:9110/health")
    if health.get("service") != "W7TP_NATIVE_ADI_AGENT" or health.get("state") != "PASS":
        return 2
    print(json.dumps({"consumer": "NATIVE_ADI_READ_ONLY_HEALTH",
                      "resolve_service_used": True, "application_health": "PASS",
                      "path": binding["selected_path"], "decision_id": binding["decision_id"]}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
