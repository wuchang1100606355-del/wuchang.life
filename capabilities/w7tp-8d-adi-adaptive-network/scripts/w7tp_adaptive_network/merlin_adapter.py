from __future__ import annotations

import json
import re
from typing import Any

from .common import run_command, sha256_text


_SAFE_ALIAS = re.compile(r"^[A-Za-z0-9_.-]+$")


REMOTE_READ_ONLY_SCRIPT = r'''
set -u
printf 'HOSTNAME=%s\n' "$(hostname 2>/dev/null || true)"
for k in productid firmver buildno extendno lan_ipaddr lan_netmask dhcp_enable_x dhcp_start dhcp_end dhcp_dns1_x dhcp_dns2_x dhcp_static_x wan0_state_t wan0_auxstate_t wan0_proto ipv6_service ipv6_prefix ipv6_prefix_length ipv6_rtr_addr ipv6_accept_defrtr ddns_enable_x ddns_server_x http_enable http_lanport https_lanport misc_http_x misc_httpport_x misc_httpsport_x sshd_wan fw_enable_x vts_enable_x lan_ifname lan_ifnames lan1_ipaddr lan1_netmask lan1_ifname lan1_ifnames br1_ifnames; do
  value=$(nvram get "$k" 2>/dev/null || true)
  printf 'NVRAM:%s=%s\n' "$k" "$value"
done
wan=$(nvram get wan0_ipaddr 2>/dev/null || true)
case "$wan" in
  '') wan_scope=UNSET ;;
  10.*|192.168.*|172.16.*|172.17.*|172.18.*|172.19.*|172.2[0-9].*|172.3[01].*) wan_scope=PRIVATE_OR_CGNAT ;;
  100.6[4-9].*|100.[7-9][0-9].*|100.1[01][0-9].*|100.12[0-7].*) wan_scope=CGNAT ;;
  *) wan_scope=PUBLIC_OR_OTHER ;;
esac
printf 'WAN_IPV4_SCOPE=%s\n' "$wan_scope"
rules=$(nvram get vts_rulelist 2>/dev/null || true)
printf 'PORT_FORWARD_SHA256=%s\n' "$(printf '%s' "$rules" | sha256sum | awk '{print $1}')"
printf '%s\n' "$rules" | awk -v RS='<' -F'>' 'NF>=6 {printf "FORWARD:%s|%s|%s|%s|%s\n",$2,$3,$4,$5,$6}'
static=$(nvram get dhcp_staticlist 2>/dev/null || true)
printf 'STATIC_LEASE_SHA256=%s\n' "$(printf '%s' "$static" | sha256sum | awk '{print $1}')"
leases=/var/lib/misc/dnsmasq.leases
if [ -r "$leases" ]; then awk '{printf "LEASE:%s|%s\n",$3,$4}' "$leases"; fi
ip route show 2>/dev/null | sed 's/^/ROUTE4:/'
ip -6 route show 2>/dev/null | sed 's/^/ROUTE6:/'
ip rule show 2>/dev/null | sed 's/^/RULE4:/'
ip -6 rule show 2>/dev/null | sed 's/^/RULE6:/'
ip neigh show 2>/dev/null | sed -n '1,160p' | sed 's/^/NEIGH:/'
brctl show 2>/dev/null | sed -n '1,80p' | sed 's/^/BRIDGE:/'
if [ -x /opt/bin/tailscale ]; then
  printf 'TAILSCALE_CLI=present\n'
  /opt/bin/tailscale ip -4 2>/dev/null | sed 's/^/TAILSCALE_IPV4:/'
  /opt/bin/tailscale ip -6 2>/dev/null | sed 's/^/TAILSCALE_IPV6:/'
  /opt/bin/tailscale status --self 2>/dev/null | sed -n '1,8p' | sed 's/^/TAILSCALE_SELF:/'
else
  printf 'TAILSCALE_CLI=absent\n'
fi
for sensor in /jffs/scripts/w7tp-8dadi-link-sensor.sh /jffs/scripts/w7tp-8dadi-capability-snapshot.sh; do
  if [ -x "$sensor" ]; then
    printf 'SENSOR:%s|present\n' "${sensor##*/}"
    "$sensor" status 2>/dev/null | sed -n '1,40p' | sed "s|^|SENSOR_STATUS:${sensor##*/}:|"
  fi
done
for script in /jffs/scripts/*; do
  [ -f "$script" ] || continue
  printf 'CUSTOM_SCRIPT:%s|%s\n' "${script##*/}" "$(sha256sum "$script" | awk '{print $1}')"
done
'''


def observe_merlin(alias: str) -> dict[str, Any]:
    if not _SAFE_ALIAS.fullmatch(alias):
        return {
            "state": "HOLD_INVALID_ROUTER_ALIAS",
            "reachable": False,
            "router_modified": False,
            "error": "router_alias_failed_allowlist",
        }

    result = run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ConnectTimeout=6",
            alias,
            REMOTE_READ_ONLY_SCRIPT,
        ],
        timeout=15.0,
    )
    parsed = _parse_output(result.get("stdout", ""))
    return {
        "state": "OBSERVED_READ_ONLY" if result.get("returncode") == 0 else "LOCALIZED_UNKNOWN",
        "reachable": result.get("returncode") == 0,
        "router_modified": False,
        "ssh_alias": alias,
        "ssh_identity_policy": "BATCH_MODE_STRICT_HOST_KEY",
        "selected_nvram_only": True,
        "raw_nvram_dump": False,
        "command_status": result.get("status"),
        "duration_ms": result.get("duration_ms"),
        "stdout_sha256": sha256_text(result.get("stdout", "")),
        "stderr_class": "NONE" if not result.get("stderr", "").strip() else "SSH_ERROR",
        **parsed,
    }


def _parse_output(output: str) -> dict[str, Any]:
    scalars: dict[str, str] = {}
    nvram: dict[str, str] = {}
    groups: dict[str, list[Any]] = {
        "port_forwarding_rules": [],
        "leases": [],
        "routes_v4": [],
        "routes_v6": [],
        "rules_v4": [],
        "rules_v6": [],
        "neighbors": [],
        "bridges": [],
        "tailscale_self": [],
        "sensors": [],
        "sensor_status": [],
        "custom_scripts": [],
    }
    prefixes = {
        "ROUTE4:": "routes_v4",
        "ROUTE6:": "routes_v6",
        "RULE4:": "rules_v4",
        "RULE6:": "rules_v6",
        "NEIGH:": "neighbors",
        "BRIDGE:": "bridges",
        "TAILSCALE_SELF:": "tailscale_self",
    }
    for line in output.splitlines():
        if line.startswith("NVRAM:") and "=" in line:
            key, value = line[len("NVRAM:") :].split("=", 1)
            nvram[key] = value
        elif line.startswith("FORWARD:"):
            fields = line[len("FORWARD:") :].split("|")
            if len(fields) >= 5:
                groups["port_forwarding_rules"].append(
                    {
                        "external_port": fields[0],
                        "target": fields[1],
                        "internal_port": fields[2],
                        "protocol": fields[3],
                        "source_filter": fields[4],
                    }
                )
        elif line.startswith("LEASE:"):
            fields = line[len("LEASE:") :].split("|", 1)
            if len(fields) == 2:
                groups["leases"].append({"lan_ip": fields[0], "hostname": fields[1]})
        elif line.startswith("TAILSCALE_IPV4:"):
            scalars["tailscale_ipv4"] = line.split(":", 1)[1]
        elif line.startswith("TAILSCALE_IPV6:"):
            scalars["tailscale_ipv6"] = line.split(":", 1)[1]
        elif line.startswith("SENSOR:"):
            groups["sensors"].append(line[len("SENSOR:") :])
        elif line.startswith("SENSOR_STATUS:"):
            groups["sensor_status"].append(line[len("SENSOR_STATUS:") :])
        elif line.startswith("CUSTOM_SCRIPT:"):
            value = line[len("CUSTOM_SCRIPT:") :]
            name, _, digest = value.partition("|")
            groups["custom_scripts"].append({"name": name, "sha256": digest})
        else:
            matched = False
            for prefix, group in prefixes.items():
                if line.startswith(prefix):
                    groups[group].append(line[len(prefix) :])
                    matched = True
                    break
            if not matched and "=" in line:
                key, value = line.split("=", 1)
                scalars[key.lower()] = value
    return {"nvram": nvram, **scalars, **groups}


def to_redacted_inventory(observation: dict[str, Any]) -> dict[str, Any]:
    nvram = observation.get("nvram", {})
    forwarding = observation.get("port_forwarding_rules", [])
    return {
        "inventory_version": "MERLIN-REDACTED-INVENTORY/0.1",
        "router_identity": {
            "vendor": "ASUS",
            "model": nvram.get("productid", ""),
            "firmware": "Asuswrt-Merlin",
            "firmware_version": ".".join(
                value for value in (nvram.get("firmver"), nvram.get("buildno")) if value
            ),
            "router_role": "EDGE_NETWORK_OBSERVER_CANDIDATE",
        },
        "network_boundary": {
            "lan_subnet": _subnet_hint(nvram.get("lan_ipaddr"), nvram.get("lan_netmask")),
            "dhcp_range": f"{nvram.get('dhcp_start', '')}-{nvram.get('dhcp_end', '')}",
            "wan_type": nvram.get("wan0_proto", ""),
            "wan_scope": observation.get("wan_ipv4_scope", "LOCALIZED_UNKNOWN"),
            "ddns_enabled": nvram.get("ddns_enable_x") == "1",
            "ddns_hostname_redacted": "",
            "remote_admin_from_wan": nvram.get("misc_http_x") == "1",
        },
        "admin_surface": {
            "web_admin_lan_only": nvram.get("misc_http_x") != "1",
            "ssh_enabled": observation.get("reachable", False),
            "http_lan_port": nvram.get("http_lanport", ""),
            "https_lan_port": nvram.get("https_lanport", ""),
            "ssh_scope": "lan_only" if not nvram.get("sshd_wan") else "unknown",
            "ssh_port_forwarding_enabled": None,
            "risk_note": "read-only selected-field observation",
        },
        "wireless_fields": {
            "main_ssids": [],
            "guest_networks": [],
            "wifi_passwords_stored": False,
            "segmentation_note": "br55 and guest interfaces observed; policy binding not inferred",
        },
        "device_fields": {
            "trusted_lan_devices_count": len(observation.get("leases", [])),
            "guest_devices_count": None,
            "merchant_devices_count": None,
            "iot_devices_count": None,
            "mac_addresses_redacted_or_hashed": True,
        },
        "firewall_port_forwarding": {
            "firewall_enabled": nvram.get("fw_enable_x") == "1",
            "port_forwarding_rules": forwarding,
            "wan_exposed_services": [
                f"{rule.get('protocol')}:{rule.get('external_port')}"
                for rule in forwarding
            ],
            "msi_core_exposed_to_wan": False,
            "risk_note": "rule presence is evidence, not approval",
            "rules_sha256": observation.get("port_forward_sha256", ""),
        },
        "vpn": {
            "vpn_enabled": bool(observation.get("tailscale_ipv4")),
            "vpn_types": ["Tailscale"] if observation.get("tailscale_ipv4") else [],
            "peer_count": None,
            "keys_or_secrets_stored": False,
            "member_access_note": "peer identity and policy remain separate",
        },
        "qos_traffic": {
            "qos_enabled": None,
            "traffic_analyzer_enabled": None,
            "xiaoj_priority_plan": "",
            "emergency_traffic_protection_note": "",
        },
        "usb_storage": {
            "usb_attached": None,
            "samba_enabled": None,
            "ftp_enabled": None,
            "media_server_enabled": None,
            "credentials_stored": False,
        },
        "aimesh": {"enabled": None, "node_count": None, "nodes_redacted": []},
        "w7tp_mapping": {
            "field": "MERLIN_PHYSICAL_ROUTER_FIELD",
            "eamtp_allowed": True,
            "cloud_allowed": False,
            "control_mode": "human_review_only",
            "dead_letter_for": [
                "export_router_password",
                "read_private_key",
                "open_unrestricted_wan_ssh",
                "disable_firewall",
                "expose_msi_core_to_wan",
            ],
        },
        "ipv6": {
            "service": nvram.get("ipv6_service", ""),
            "prefix_present": bool(nvram.get("ipv6_prefix")),
            "prefix_length": nvram.get("ipv6_prefix_length", ""),
            "router_address_present": bool(nvram.get("ipv6_rtr_addr")),
        },
        "router_modified": False,
        "authority": "EVIDENCE_SOURCE_NOT_D8_AUTHORITY",
        "operator_notes": "",
        "last_manual_review": "",
    }


def _subnet_hint(address: str | None, netmask: str | None) -> str:
    if address == "192.168.50.1" and netmask == "255.255.255.0":
        return "192.168.50.0/24"
    if address and netmask:
        return f"{address}/{netmask}"
    return "LOCALIZED_UNKNOWN"
