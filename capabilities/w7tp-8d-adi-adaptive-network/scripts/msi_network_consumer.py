#!/usr/bin/env python3
"""MSI read-only health consumer: independent LAN/Tailscale SSH carriers.

No port allocation, router mutation, key reading, or socket listener.
"""
import argparse
import ipaddress
import re
import json
import os
import shlex
import subprocess
import sys
import time

SERVER_TS = "100.71.224.18"
SERVER_LAN = "192.168.50.249"
USER = "taiji_admin"
INGEST = "/home/taiji_admin/Taiji_Hub/capabilities/w7tp-8d-adi-adaptive-network/scripts/msi_evidence_ingest.py"
REMOTE_QUERY = r"""import os,socket,json
s=socket.socket(socket.AF_UNIX)
s.connect("/run/user/%s/w7tp-adaptive-network.sock"%os.getuid())
s.sendall(b"GET /resolve_service?intent_id=MSI_READ_ONLY_NATIVE_ADI_HEALTH HTTP/1.1\r\nHost:localhost\r\nConnection:close\r\n\r\n")
data=b""
while True:
 b=s.recv(65536)
 if not b:break
 data+=b
print(data.split(b"\r\n\r\n",1)[1].decode())
"""

def ssh_args(host):
    args = ["ssh", "-T", "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=4"]
    if host == SERVER_LAN:
        args += ["-o", "HostKeyAlias=" + SERVER_TS]
    return args + [USER + "@" + host]

def probe(host, iface):
    route = subprocess.run(["ip", "route", "get", host], capture_output=True,
                           text=True, timeout=3)
    match = re.search(r"\bdev\s+(\S+)\s+.*?\bsrc\s+(\S+)", route.stdout)
    device, source = match.groups() if route.returncode == 0 and match else ("", "")
    try:
        source_ip = ipaddress.ip_address(source)
        if iface is None:
            route_bound = (bool(re.fullmatch(r"eth[0-9]+", device))
                           and source_ip in ipaddress.ip_network("192.168.50.0/24"))
        else:
            route_bound = (device == iface
                           and source_ip in ipaddress.ip_network("100.64.0.0/10"))
    except ValueError:
        route_bound = False
    if not route_bound:
        return {"interface": device, "source_ipv4": source,
                "route_bound": False, "application_pass": False}
    result = subprocess.run(ssh_args(host) + ["-W", "127.0.0.1:9110"],
        input=b"GET /health HTTP/1.1\r\nHost:localhost\r\nConnection:close\r\n\r\n",
        capture_output=True, timeout=8)
    application_pass = False
    if result.returncode == 0 and result.stdout.startswith(b"HTTP/1.0 200"):
        try:
            health = json.loads(result.stdout.split(b"\r\n\r\n", 1)[1])
            application_pass = (health.get("service") == "W7TP_NATIVE_ADI_AGENT"
                                and health.get("state") == "PASS")
        except (ValueError, IndexError):
            pass
    return {"interface": device, "source_ipv4": source,
            "route_bound": route_bound, "application_pass": application_pass}

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--suppress-lan-for-one-cycle", action="store_true")
    args = parser.parse_args(argv)
    lan = probe(SERVER_LAN, None)
    tailscale = probe(SERVER_TS, "tailscale0")
    if args.suppress_lan_for_one_cycle:
        lan["application_pass"] = False
    packet = {"schema": "MSI_TWO_PATH_HEALTH_OBSERVATION/1",
              "source_node": "MSI", "observed_at_epoch": time.time(),
              "paths": {"LAN_IPV4": lan, "TAILSCALE_IPV4": tailscale}}
    push = subprocess.run(ssh_args(SERVER_TS) + ["python3 " + shlex.quote(INGEST)],
        input=json.dumps(packet).encode(), capture_output=True, timeout=9)
    if push.returncode != 0:
        print("HOLD_REMOTE_EVIDENCE_INGEST", file=sys.stderr)
        return 2
    # The server observer independently refreshes and selects this intent.
    query = subprocess.run(
        ssh_args(SERVER_TS) + ["python3 -c " + shlex.quote(REMOTE_QUERY)],
        capture_output=True, text=True, timeout=8)
    selected = None
    selected_health = None
    if query.returncode == 0:
        try:
            binding = json.loads(query.stdout)
            selected = binding.get("selected_path") if binding.get("authorized") else None
            if selected == "MSI_ADI_LAN" and not args.suppress_lan_for_one_cycle:
                selected_health = probe(SERVER_LAN, None)["application_pass"]
            elif selected == "MSI_ADI_TAILSCALE":
                selected_health = probe(SERVER_TS, "tailscale0")["application_pass"]
        except (ValueError, KeyError):
            pass
    print(json.dumps({"lan_probe": lan["application_pass"],
                      "tailscale_probe": tailscale["application_pass"],
                      "evidence_ingested": True,
                      "resolve_service_selected": selected,
                      "selected_application_pass": selected_health,
                      "failure_injection": args.suppress_lan_for_one_cycle}))
    return 0 if args.suppress_lan_for_one_cycle or selected_health is True or selected is None else 2

if __name__ == "__main__":
    sys.exit(main())
