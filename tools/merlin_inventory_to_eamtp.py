#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.merlin_inventory_validator import validate, sha256_file
from runtime.router.eamtp_7d_translator import build_packet
from runtime.dead_letter.eamtp_policy_gate import check_packet


def compact_summary(data: Dict[str, Any]) -> str:
    ident = data.get("router_identity", {})
    net = data.get("network_boundary", {})
    admin = data.get("admin_surface", {})
    fw = data.get("firewall_port_forwarding", {})
    vpn = data.get("vpn", {})
    qos = data.get("qos_traffic", {})
    mesh = data.get("aimesh", {})

    return (
        f"Merlin router redacted inventory: "
        f"model={ident.get('model','')}, firmware={ident.get('firmware','')}, "
        f"lan_subnet={net.get('lan_subnet','')}, dhcp_range={net.get('dhcp_range','')}, "
        f"remote_admin_from_wan={net.get('remote_admin_from_wan')}, "
        f"ssh_enabled={admin.get('ssh_enabled')}, ssh_scope={admin.get('ssh_scope')}, "
        f"firewall_enabled={fw.get('firewall_enabled')}, "
        f"msi_core_exposed_to_wan={fw.get('msi_core_exposed_to_wan')}, "
        f"vpn_enabled={vpn.get('vpn_enabled')}, vpn_types={vpn.get('vpn_types')}, "
        f"qos_enabled={qos.get('qos_enabled')}, "
        f"aimesh_enabled={mesh.get('enabled')}, node_count={mesh.get('node_count')}."
    )


def risk_notes(data: Dict[str, Any]) -> list[str]:
    notes = []
    admin = data.get("admin_surface", {})
    net = data.get("network_boundary", {})
    fw = data.get("firewall_port_forwarding", {})

    if net.get("remote_admin_from_wan") is True:
        notes.append("remote_admin_from_wan_enabled_requires_review")

    if admin.get("ssh_scope") == "wan_exposed":
        notes.append("ssh_wan_exposed_requires_review_or_dead_letter")

    if fw.get("msi_core_exposed_to_wan") is True:
        notes.append("msi_core_exposed_to_wan_hardwall_risk")

    exposed = fw.get("wan_exposed_services") or []
    if exposed:
        notes.append(f"wan_exposed_services_count:{len(exposed)}")

    if not notes:
        notes.append("no_high_risk_network_exposure_declared_in_inventory")

    return notes


def build_adapter_result(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validation = validate(data)

    if validation["decision"] != "safe_for_xiaoj_redacted_inventory":
        return {
            "adapter": "merlin_inventory_to_eamtp",
            "decision": "blocked_inventory_not_safe",
            "validation": validation,
            "file": str(path),
            "router_login": False,
            "router_modified": False,
            "secret_values_printed": False,
        }

    summary = compact_summary(data)
    notes = risk_notes(data)

    packet = build_packet(
        summary=summary + " Risk notes: " + "; ".join(notes),
        intent_type="system_check",
        actor_type="system",
        auth_level="system",
        entry="local",
        source_field="local_ops",
        target_field="router",
        privacy_level="redacted",
        consent_state="system",
        cloud_allowed=False,
        preferred_lane="local",
        latency_class="normal",
        cost_policy="balanced",
        allowed_actions=["summarize", "draft_plan", "answer"],
    )

    decision, reasons = check_packet(packet)

    return {
        "adapter": "merlin_inventory_to_eamtp",
        "decision": decision,
        "reasons": reasons,
        "validation": validation,
        "file": str(path),
        "file_hash": sha256_file(path),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "network_field": "MERLIN_PHYSICAL_ROUTER_FIELD",
        "risk_notes": notes,
        "summary": summary,
        "eamtp_packet": packet,
        "router_login": False,
        "router_modified": False,
        "secret_values_printed": False,
        "cloud_allowed": False,
    }


def to_markdown(result: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Merlin Inventory EAMTP Summary")
    lines.append("")
    lines.append(f"- Decision: `{result.get('decision')}`")
    lines.append(f"- File: `{result.get('file')}`")
    lines.append(f"- File Hash: `{result.get('file_hash','')}`")
    lines.append(f"- Network Field: `{result.get('network_field','')}`")
    lines.append(f"- Router Login: `{result.get('router_login')}`")
    lines.append(f"- Router Modified: `{result.get('router_modified')}`")
    lines.append(f"- Secret Values Printed: `{result.get('secret_values_printed')}`")
    lines.append(f"- Cloud Allowed: `{result.get('cloud_allowed')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(result.get("summary", ""))
    lines.append("")
    lines.append("## Risk Notes")
    lines.append("")
    for n in result.get("risk_notes", []):
        lines.append(f"- {n}")
    lines.append("")
    lines.append("## EAMTP")
    lines.append("")
    pkt = result.get("eamtp_packet", {})
    lines.append(f"- Packet ID: `{pkt.get('packet_id','')}`")
    lines.append(f"- Packet Hash: `{pkt.get('ledger',{}).get('hash','')}`")
    lines.append(f"- Privacy: `{pkt.get('d4_privacy_consent',{}).get('privacy_level','')}`")
    lines.append(f"- Risk: `{pkt.get('d5_risk_governance',{}).get('risk_level','')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="configs/merlin/router_inventory_redacted.local.json")
    parser.add_argument("--out-prefix", default=None)
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(json.dumps({
            "decision": "missing_inventory_file",
            "file": str(path),
            "router_login": False,
            "router_modified": False
        }, ensure_ascii=False, indent=2))
        return 2

    result = build_adapter_result(path)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = args.out_prefix or f"runtime/reports/merlin_inventory_eamtp_{ts}"
    json_path = Path(prefix + ".json")
    md_path = Path(prefix + ".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(result), encoding="utf-8")

    print(json.dumps({
        "decision": result.get("decision"),
        "reasons": result.get("reasons", []),
        "file": str(path),
        "json": str(json_path),
        "markdown": str(md_path),
        "router_login": False,
        "router_modified": False,
        "cloud_allowed": False,
    }, ensure_ascii=False, indent=2))

    return 0 if result.get("decision") in {"allow_low_risk", "pending_review"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
