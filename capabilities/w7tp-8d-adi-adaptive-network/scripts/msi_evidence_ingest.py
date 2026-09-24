#!/usr/bin/env python3
"""Authenticated SSH caller submits bounded, expiring read-only MSI probe evidence."""
import json
import ipaddress
import re
import math
import os
import sys
import tempfile
from pathlib import Path

DEST = Path.home() / ".local/share/w7tp-adaptive-network/state/msi-observation.json"
def main():
    raw = sys.stdin.buffer.read(16385)
    if len(raw) > 16384:
        return 2
    try:
        data = json.loads(raw)
        assert data["schema"] == "MSI_TWO_PATH_HEALTH_OBSERVATION/1"
        assert data["source_node"] == "MSI"
        assert isinstance(data["observed_at_epoch"], (int, float))
        assert not isinstance(data["observed_at_epoch"], bool)
        assert math.isfinite(data["observed_at_epoch"])
        assert set(data["paths"]) == {"LAN_IPV4", "TAILSCALE_IPV4"}
        for key in ("LAN_IPV4", "TAILSCALE_IPV4"):
            value = data["paths"][key]
            interface = value["interface"]
            source = ipaddress.ip_address(value["source_ipv4"])
            if key == "LAN_IPV4":
                assert isinstance(interface, str) and re.fullmatch(r"eth[0-9]+", interface)
                assert source in ipaddress.ip_network("192.168.50.0/24")
            else:
                assert interface == "tailscale0"
                assert source in ipaddress.ip_network("100.64.0.0/10")
            assert isinstance(value["application_pass"], bool)
            assert isinstance(value["route_bound"], bool)
        assert set(data) == {"schema", "source_node", "observed_at_epoch", "paths"}
    except (KeyError, AssertionError, TypeError, ValueError):
        return 2
    DEST.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=DEST.parent, prefix=".msi-evidence-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(json.dumps(data, sort_keys=True).encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, DEST)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return 0

if __name__ == "__main__":
    sys.exit(main())
