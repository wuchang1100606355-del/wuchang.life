#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


FORBIDDEN_KEY_PATTERNS = [
    r"password",
    r"passwd",
    r"pwd",
    r"secret",
    r"token",
    r"private[_-]?key",
    r"wireguard[_-]?private",
    r"openvpn[_-]?key",
    r"credential",
    r"api[_-]?key",
]

FORBIDDEN_VALUE_PATTERNS = [
    r"-----BEGIN .*PRIVATE KEY-----",
    r"sk-[A-Za-z0-9_\-]{20,}",
    r"AIza[0-9A-Za-z_\-]{20,}",
    r"(?i)password\s*[:=]",
    r"(?i)private[_ -]?key\s*[:=]",
    r"(?i)token\s*[:=]",
    r"(?i)secret\s*[:=]",
]

REQUIRED_TOP = [
    "inventory_version",
    "router_identity",
    "network_boundary",
    "admin_surface",
    "wireless_fields",
    "device_fields",
    "firewall_port_forwarding",
    "vpn",
    "qos_traffic",
    "usb_storage",
    "aimesh",
    "w7tp_mapping",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(obj: Any, path: str = "$") -> List[Tuple[str, Any]]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append((f"{path}.{k}", v))
            out.extend(walk(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(walk(v, f"{path}[{i}]"))
    return out


def validate(data: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    for k in REQUIRED_TOP:
        if k not in data:
            errors.append(f"missing_required_top_field:{k}")

    for p, v in walk(data):
        key = p.split(".")[-1].lower()

        for pat in FORBIDDEN_KEY_PATTERNS:
            if re.search(pat, key, re.I):
                # allow explicit false flags that say secrets are not stored
                if isinstance(v, bool) and v is False:
                    continue
                errors.append(f"forbidden_key_name:{p}")
                break

        if isinstance(v, str):
            if len(v) > 160:
                warnings.append(f"long_string_value_redacted_check:{p}")

            for pat in FORBIDDEN_VALUE_PATTERNS:
                if re.search(pat, v):
                    errors.append(f"secret_like_value_detected:{p}")
                    break

            if re.search(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", v):
                warnings.append(f"possible_raw_mac_address:{p}")

    w7tp = data.get("w7tp_mapping", {})
    if w7tp.get("cloud_allowed") is not False:
        errors.append("w7tp_mapping.cloud_allowed_must_be_false")

    if data.get("vpn", {}).get("keys_or_secrets_stored") is not False:
        errors.append("vpn.keys_or_secrets_stored_must_be_false")

    if data.get("wireless_fields", {}).get("wifi_passwords_stored") is not False:
        errors.append("wireless_fields.wifi_passwords_stored_must_be_false")

    if data.get("usb_storage", {}).get("credentials_stored") is not False:
        errors.append("usb_storage.credentials_stored_must_be_false")

    return {
        "decision": "safe_for_xiaoj_redacted_inventory" if not errors else "blocked_needs_redaction",
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        default="configs/merlin/router_inventory_redacted.local.json",
        help="redacted local inventory json path",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="optional report path",
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        result = {
            "decision": "missing_inventory_file",
            "file": str(path),
            "errors": ["inventory_file_not_found"],
            "warnings": [],
        }
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = validate(data)
            result.update({
                "file": str(path),
                "file_hash": sha256_file(path),
                "validated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "secret_values_printed": False,
                "router_login": False,
                "router_modified": False,
                "git_commit": False,
            })
        except Exception as e:
            result = {
                "decision": "invalid_json",
                "file": str(path),
                "errors": [f"json_error:{e}"],
                "warnings": [],
            }

    report = Path(args.report) if args.report else Path("runtime/reports") / f"merlin_inventory_validator_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"REPORT={report}")

    return 0 if result.get("decision") == "safe_for_xiaoj_redacted_inventory" else 2


if __name__ == "__main__":
    raise SystemExit(main())
