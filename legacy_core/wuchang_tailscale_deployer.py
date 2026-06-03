# -*- coding: utf-8 -*-
"""Taiji Tailnet deployment manifest generator.

This module intentionally does not perform live deployment.

Former versions of this file attempted direct SSH deployment and key-file
distribution. That behavior is forbidden under the current governance model.
The safe replacement emits non-sensitive manifests that can be reviewed by
Taiji Gateway, Metric Translation Gateway, Five Metric Gate, and audit tooling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
EDGE_GATEWAY_SOURCE = ROOT_DIR / "legacy_core" / "taiji_unified_gateway_edge.py"
DEFAULT_OUTPUT = ROOT_DIR / "Taiji_Governance" / "deployments" / "tailscale_deployment_manifest.json"
DEFAULT_ROLLBACK = ROOT_DIR / "Taiji_Governance" / "deployments" / "tailscale_rollback_plan.md"
DEFAULT_AUDIT = ROOT_DIR / "Taiji_Governance" / "logs" / "deployment_audit.jsonl"
DEFAULT_PREFLIGHT = ROOT_DIR / "Taiji_Governance" / "deployments" / "tailscale_preflight_record.json"
KNOWN_HOSTS = Path.home() / ".ssh" / "known_hosts"


NODE_ROSTER: list[dict[str, Any]] = [
    {
        "identity": "TDI-NODE-vpn-server-01",
        "name": "taiji01",
        "tailscale_ipv4": "100.71.224.18",
        "role": "vpn_subnet_router",
        "approved_routes": ["192.168.50.0/24"],
        "deployment_state": "manifest_ready",
    },
    {
        "identity": "TDI-NODE-admin-msi",
        "name": "msi",
        "tailscale_ipv4": "100.107.187.77",
        "role": "admin_workstation",
        "deployment_state": "inventory_confirmed",
    },
    {
        "identity": "TDI-NODE-display-02",
        "name": "customer-display-02",
        "tailscale_ipv4": "pending",
        "role": "customer_display",
        "deployment_state": "inventory_required",
    },
    {
        "identity": "TDI-NODE-sunmi-pos",
        "name": "sunmi-pos",
        "tailscale_ipv4": "pending",
        "role": "point_of_sale",
        "deployment_state": "inventory_required",
    },
]


FORBIDDEN_ACTIONS = [
    "copy_service_account_json",
    "copy_oauth_token",
    "copy_api_key",
    "direct_gemini_api_call",
    "direct_google_api_call",
    "direct_router_mutation",
    "direct_vpn_acl_mutation",
    "ssh_without_gateway_guard",
]


HOST_ALLOWLIST = {
    "100.71.224.18",  # taiji01
    "100.107.187.77",  # msi
}


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> dict[str, Any]:
    source_hash = sha256_file(EDGE_GATEWAY_SOURCE)
    return {
        "schema": "taiji.tailnet.deployment_manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "manifest_only_no_live_deploy",
        "site": "liaoguo_cafe_main_store",
        "source_artifact": {
            "path": str(EDGE_GATEWAY_SOURCE.relative_to(ROOT_DIR)),
            "exists": EDGE_GATEWAY_SOURCE.exists(),
            "sha256": source_hash,
        },
        "nodes": NODE_ROSTER,
        "required_gates": [
            "Taiji Gateway",
            "Metric Translation Gateway",
            "Five Metric Gate",
            "taiji-metric-preflight",
            "approved_external_deployment_control",
            "audit_jsonl",
            "sha256_baseline",
            "rollback_plan",
        ],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "secret_material": {
            "service_account_json": "not_in_manifest",
            "oauth_token": "not_in_manifest",
            "api_key": "not_in_manifest",
            "odoo_member_plaintext": "not_in_manifest",
            "chatgpt_export_text": "not_in_manifest",
        },
        "execution": {
            "live_deploy_enabled": False,
            "reason": "This tool is limited to manifest generation and local preflight checks.",
            "default_mode": "manifest-only",
            "preflight_only": True,
            "live_execute_path": "forbidden",
        },
    }


def write_rollback_plan(path: Path, manifest_path: Path) -> None:
    body = f"""# Tailnet Rollback Plan

Generated: {datetime.now(timezone.utc).isoformat()}
Manifest: `{manifest_path}`

This plan contains no secrets.

## Rollback Principles

1. Do not delete data volumes automatically.
2. Stop only services that were started by an approved guarded deployment.
3. Restore previous systemd units from a recorded baseline.
4. Revert router and VPN changes only from their approved admin consoles or
   guarded automation path.
5. Record every rollback step in audit jsonl.

## Current Status

No live deployment was performed by this manifest generator, so no runtime
rollback command is required from this script.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def run_local_check(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output_stored": False,
    }


def local_json_get(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = response.read().decode("utf-8")
        return {"ok": True, "json": json.loads(payload)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def write_audit_event(path: Path, event: dict[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        event.setdefault("actor", "wuchang_tailscale_deployer")
        event.setdefault("secret_material", "not_accessed")
        event.setdefault("external_api", "not_called")
        event.setdefault("live_deploy", "not_executed")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def allowed_target_hosts() -> set[str]:
    return set(HOST_ALLOWLIST)


def check_targets() -> list[dict[str, Any]]:
    allowlist = allowed_target_hosts()
    results: list[dict[str, Any]] = []
    for node in NODE_ROSTER:
        host = str(node.get("tailscale_ipv4", "pending"))
        result = {
            "identity": node["identity"],
            "name": node["name"],
            "host": host,
            "in_allowlist": host in allowlist,
            "risk": "L0_exact_match" if host in allowlist else "L2_drift",
        }
        if host == "pending":
            result["reason"] = "target_identity_pending"
        results.append(result)
    return results


def check_gcp_key_path() -> dict[str, Any]:
    configured = bool(os.environ.get("GCP_KEY_PATH"))
    if not configured:
        return {"configured": False, "exists": False, "content_read": False}
    path = Path(os.environ["GCP_KEY_PATH"]).expanduser()
    return {
        "configured": True,
        "exists": path.exists(),
        "content_read": False,
        "path_printed": False,
    }


def run_preflight(
    manifest_path: Path,
    rollback_path: Path,
    audit_path: Path,
    preflight_path: Path,
) -> int:
    manifest = build_manifest()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_rollback_plan(rollback_path, manifest_path)

    checks: dict[str, Any] = {
        "schema": "taiji.tailnet.preflight_record.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "preflight_local_only",
        "allow": True,
        "risk": "L0_exact_match",
        "hazards": [],
        "remote_execution": "not_performed",
        "secret_material": "not_accessed",
    }

    checks["tailscale_status"] = run_local_check(["tailscale", "status"])
    checks["tailscale_ip"] = run_local_check(["tailscale", "ip", "-4"])
    if not checks["tailscale_status"]["ok"] or not checks["tailscale_ip"]["ok"]:
        checks["allow"] = False
        checks["risk"] = "L2_drift"
        checks["hazards"].append("tailscale_local_check_failed")

    checks["target_hosts"] = check_targets()
    for target in checks["target_hosts"]:
        if not target["in_allowlist"] and target["host"] != "pending":
            checks["allow"] = False
            checks["risk"] = "L3_metric_hazard"
            checks["hazards"].append(f"target_not_allowlisted:{target['name']}")

    checks["known_hosts"] = {"exists": KNOWN_HOSTS.exists(), "path_printed": False}
    if not KNOWN_HOSTS.exists():
        checks["allow"] = False
        if checks["risk"] != "L3_metric_hazard":
            checks["risk"] = "L2_drift"
        checks["hazards"].append("known_hosts_missing")

    checks["gcp_key_path"] = check_gcp_key_path()
    checks["five_metric_health"] = local_json_get("http://127.0.0.1:8105/health")
    checks["five_metric_policy"] = local_json_get("http://127.0.0.1:8105/policy")
    policy_json = checks["five_metric_policy"].get("json", {})
    checks["policy_locked"] = policy_json.get("policy_locked") is True or policy_json.get("locked") is True
    if not checks["five_metric_health"]["ok"] or not checks["five_metric_policy"]["ok"] or not checks["policy_locked"]:
        checks["allow"] = False
        checks["risk"] = "L3_metric_hazard"
        checks["hazards"].append("five_metric_policy_not_locked_or_unreachable")

    checks["taiji_metric_preflight"] = {"exists": shutil.which("taiji-metric-preflight") is not None}
    if not checks["taiji_metric_preflight"]["exists"]:
        checks["allow"] = False
        if checks["risk"] != "L3_metric_hazard":
            checks["risk"] = "L2_drift"
        checks["hazards"].append("taiji_metric_preflight_missing")

    audit_event = {
        "event": "tailscale_preflight",
        "mode": "preflight_local_only",
        "result": "allow" if checks["allow"] else "block",
        "risk": checks["risk"],
        "hazards": checks["hazards"],
    }
    checks["audit_writable"] = write_audit_event(audit_path, audit_event)
    if not checks["audit_writable"]:
        checks["allow"] = False
        if checks["risk"] != "L3_metric_hazard":
            checks["risk"] = "L2_drift"
        checks["hazards"].append("audit_log_not_writable")

    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    preflight_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"preflight_record_written={preflight_path}")
    print(f"allow={str(checks['allow']).lower()}")
    print(f"risk={checks['risk']}")
    print("remote_execution=false")
    print("secret_material_printed=false")
    return 0 if checks["allow"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a safe Tailnet deployment manifest.")
    parser.add_argument("--mode", choices=["manifest-only", "preflight"], default="manifest-only")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rollback-output", type=Path, default=DEFAULT_ROLLBACK)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--preflight-output", type=Path, default=DEFAULT_PREFLIGHT)
    args = parser.parse_args()

    if args.mode == "preflight":
        return run_preflight(args.output, args.rollback_output, args.audit_output, args.preflight_output)

    manifest = build_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_rollback_plan(args.rollback_output, args.output)
    print(f"manifest_written={args.output}")
    print(f"rollback_written={args.rollback_output}")
    print("live_deploy_executed=false")
    print("secret_material_written=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
