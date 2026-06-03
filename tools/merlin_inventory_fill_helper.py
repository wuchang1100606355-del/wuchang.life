#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merlin Redacted Inventory Fill Helper

Updates configs/merlin/router_inventory_redacted.local.json with allowlisted,
non-sensitive fields only.

Safety:
- no router login
- no SSH
- no router config change
- no credential read/write
- local inventory is not a Git commit target
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "configs" / "merlin" / "router_inventory_redacted.local.json"

ALLOWED_KEYS = {
    "router_identity.firmware_version": str,
    "network_boundary.lan_subnet": str,
    "network_boundary.dhcp_range": str,
    "network_boundary.ddns_enabled": bool,
    "network_boundary.remote_admin_from_wan": bool,
    "admin_surface.web_admin_lan_only": bool,
    "admin_surface.ssh_enabled": bool,
    "admin_surface.ssh_scope": str,
    "admin_surface.ssh_port_forwarding_enabled": bool,
    "firewall_port_forwarding.firewall_enabled": bool,
    "vpn.vpn_enabled": bool,
    "qos_traffic.qos_enabled": bool,
    "qos_traffic.traffic_analyzer_enabled": bool,
    "aimesh.enabled": bool,
    "aimesh.node_count": int,
    "usb_storage.usb_attached": bool,
    "usb_storage.samba_enabled": bool,
    "usb_storage.ftp_enabled": bool,
    "usb_storage.media_server_enabled": bool,
    "operator_notes": str,
}

FORBIDDEN_PAT = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key|credential|wifi[_-]?password|vpn[_-]?private|ddns[_-]?token)",
    re.I,
)

SSH_SCOPE_ALLOWED = {"disabled", "lan_only", "vpn_only", "wan_exposed", "unknown"}


def parse_value(raw: str, typ: type) -> Any:
    if typ is bool:
        s = raw.strip().lower()
        if s in {"true", "1", "yes", "y", "on"}:
            return True
        if s in {"false", "0", "no", "n", "off"}:
            return False
        raise ValueError(f"invalid bool value: {raw}")
    if typ is int:
        return int(raw)
    return raw


def set_path(obj: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur: Any = obj
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_validator(path: Path) -> Tuple[bool, str]:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "merlin_inventory_validator.py"),
        "--file",
        str(path.relative_to(ROOT)),
    ]
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return p.returncode == 0, (p.stdout + "\n" + p.stderr).strip()


def validate_set_expr(expr: str) -> Tuple[str, str]:
    if "=" not in expr:
        raise ValueError("--set must be key=value")
    key, raw = expr.split("=", 1)
    key = key.strip()
    raw = raw.strip()

    if FORBIDDEN_PAT.search(key) or FORBIDDEN_PAT.search(raw):
        raise ValueError("blocked_secret_like_key_or_value")

    if key not in ALLOWED_KEYS:
        raise ValueError(f"key_not_allowlisted:{key}")

    if key == "admin_surface.ssh_scope" and raw not in SSH_SCOPE_ALLOWED:
        raise ValueError(f"invalid_ssh_scope:{raw}")

    return key, raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_FILE))
    ap.add_argument("--set", action="append", default=[], help="allowlisted key=value")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.is_absolute():
        path = ROOT / path

    if not path.exists():
        print(json.dumps({
            "decision": "missing_local_inventory",
            "file": str(path),
            "dry_run": args.dry_run,
        }, ensure_ascii=False, indent=2))
        return 2

    ok_before, val_before = run_validator(path)
    if not ok_before:
        print(json.dumps({
            "decision": "blocked_validator_before_failed",
            "file": str(path),
            "validator": val_before,
        }, ensure_ascii=False, indent=2))
        return 3

    data = load_json(path)
    new_data = copy.deepcopy(data)

    changes = []
    for expr in args.set:
        key, raw = validate_set_expr(expr)
        value = parse_value(raw, ALLOWED_KEYS[key])
        set_path(new_data, key, value)
        changes.append({"key": key, "value_type": type(value).__name__, "value_preview": str(value)[:80]})

    if not args.dry_run:
        backup = path.with_suffix(path.suffix + f".bak_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ok_after, val_after = run_validator(path)
        if not ok_after:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({
                "decision": "rolled_back_validator_after_failed",
                "file": str(path),
                "backup": str(backup),
                "validator": val_after,
            }, ensure_ascii=False, indent=2))
            return 4
    else:
        ok_after, val_after = True, "dry_run_no_write"

    print(json.dumps({
        "decision": "dry_run_ok" if args.dry_run else "updated_local_inventory",
        "file": str(path),
        "dry_run": args.dry_run,
        "changes": changes,
        "validator_before": "ok",
        "validator_after": "ok" if ok_after else "failed",
        "router_login": False,
        "router_modified": False,
        "secrets_written": False,
        "git_commit": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
