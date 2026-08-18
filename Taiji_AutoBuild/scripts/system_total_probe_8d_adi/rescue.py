from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contract import CRITICAL_FILES, FORBIDDEN_PATTERNS, KDF_ITERATIONS, KDF_NAME, ROOT_DIR, SCHEMA
from .foundation import local_json_get, run_status_check, safe_text_excerpt, sha256_file, utc_now, write_json
from .governance import append_audit, authorize_local_use, verify_human_decision
from .hardware import hardware_fingerprint


def scan_file_forbidden(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                findings.append({"file": str(path.relative_to(ROOT_DIR)), "line": index, "pattern": pattern})
    return findings


def critical_file_manifest() -> list[dict[str, Any]]:
    manifest = []
    for relative in CRITICAL_FILES:
        path = ROOT_DIR / relative
        manifest.append(
            {
                "path": relative,
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else None,
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )
    return manifest


def build_rescue_snapshot(auth: dict[str, Any]) -> dict[str, Any]:
    fingerprint = hardware_fingerprint()
    deployer = ROOT_DIR / "legacy_core" / "wuchang_tailscale_deployer.py"
    forbidden_findings = scan_file_forbidden(deployer)
    preflight_record = ROOT_DIR / "Taiji_Governance" / "deployments" / "tailscale_preflight_record.json"
    progress = ROOT_DIR / "Taiji_Governance" / "progress" / "progress.md"
    worklist = ROOT_DIR / "Taiji_Governance" / "worklist" / "worklist.md"
    architecture = ROOT_DIR / "Taiji_Governance" / "architecture" / "layers_standards.yml"
    return {
        "schema": "taiji.ai_rescue_snapshot.v1",
        "generated_at": utc_now(),
        "purpose": "AI derailment / context-loss rescue anchor",
        "local_authorization": {
            "status": auth["local_authorization"],
            "source": auth["local_authorization_source"],
            "event_id": auth["local_authorization_event_id"],
            "secret_printed": False,
        },
        "safety": {
            "raw_hardware_printed": False,
            "secret_material_printed": False,
            "chatgpt_export_text_included": False,
            "google_private_data_included": False,
            "odoo_member_plaintext_included": False,
            "external_api_called": False,
            "remote_execution": False,
        },
        "hardware_anchor": {
            "fingerprint_sha256": fingerprint["fingerprint_sha256"],
            "signal_count": fingerprint["signal_count"],
            "raw_signals_printed": False,
        },
        "physical_layer": {
            "binding": "local_hardware_fingerprint",
            "signals": [
                {
                    "name": signal["name"],
                    "available": signal["available"],
                    "sha256": signal["sha256"],
                    "raw_printed": False,
                }
                for signal in fingerprint["signals"]
            ],
            "raw_machine_id_printed": False,
            "raw_serial_printed": False,
            "raw_hostname_printed": False,
        },
        "cryptographic_layer": {
            "envelope_schema": SCHEMA,
            "aead": "AES-256-GCM",
            "kdf": KDF_NAME,
            "kdf_iterations": KDF_ITERATIONS,
            "hardware_bound_key_material": True,
            "local_authorization_required_every_use": True,
            "one_time_decrypt_marker_required": True,
            "plaintext_stdout_allowed": False,
            "secret_material_printed": False,
        },
        "governance_mode": {
            "allowed_modes": ["manifest-only", "preflight-only", "local-auth-required"],
            "forbidden_commands": [
                "ssh",
                "scp",
                "systemctl restart",
                "docker compose up",
                "docker compose down",
                "taiji-guarded-run",
                "--execute",
            ],
            "risk_scale": {
                "L0_exact_match": "allow",
                "L1_near": "allow_with_audit",
                "L2_drift": "warn",
                "L3_metric_hazard": "block",
            },
        },
        "runtime_checks": {
            "tailscale_status": run_status_check(["tailscale", "status"]),
            "tailscale_ip": run_status_check(["tailscale", "ip", "-4"]),
            "five_metric_health": local_json_get("http://127.0.0.1:8105/health"),
            "five_metric_policy": local_json_get("http://127.0.0.1:8105/policy"),
            "taiji_metric_preflight_exists": shutil.which("taiji-metric-preflight") is not None,
        },
        "critical_files": critical_file_manifest(),
        "forbidden_scan": {
            "target": str(deployer.relative_to(ROOT_DIR)),
            "findings": forbidden_findings,
            "risk": "L3_metric_hazard" if forbidden_findings else "L0_exact_match",
        },
        "preflight_record": safe_text_excerpt(preflight_record),
        "architecture_profile": safe_text_excerpt(architecture),
        "progress_excerpt": safe_text_excerpt(progress),
        "worklist_excerpt": safe_text_excerpt(worklist),
        "resume_instructions": [
            "Treat this file as a rescue anchor, not a source of secrets.",
            "Do not execute remote deployment from this snapshot.",
            "Resume by reading critical files, then rerun syntax and forbidden-command scans.",
            "If runtime_checks show Five Metric or Tailscale unavailable, keep deployment blocked.",
        ],
    }


def command_rescue_snapshot(args: argparse.Namespace) -> int:
    auth = authorize_local_use(args, "rescue-snapshot")
    decision = verify_human_decision(args, "rescue-snapshot")
    snapshot = build_rescue_snapshot(auth)
    snapshot["human_decision"] = decision
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"ai_rescue_snapshot_{stamp}.json"
    write_json(output, snapshot)
    snapshot_hash = sha256_file(output)
    append_audit(
        Path(args.audit_log),
        {
            "event": "ai_rescue_snapshot",
            "result": "ok",
            "snapshot_path": str(output),
            "snapshot_sha256": snapshot_hash,
            "risk": snapshot["forbidden_scan"]["risk"],
            **auth,
            **decision,
        },
    )
    print(f"rescue_snapshot_written={output.resolve()}")
    print(f"rescue_snapshot_sha256={snapshot_hash}")
    print("raw_hardware_printed=false")
    print("secret_material_printed=false")
    print("external_api_called=false")
    return 0
