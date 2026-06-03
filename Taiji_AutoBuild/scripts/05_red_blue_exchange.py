#!/usr/bin/env python3
"""Local red/blue design hardening exchange.

Red/blue review is allowed. Cloud plaintext is not.
Red/blue review is for system design and packaging review, not daily runtime.

This tool is local-only: it does not call OpenAI, Google, Gemini, Vertex AI, or
any external API. It avoids secret directories and does not store raw source
excerpts in the report. Findings contain file path, line number, rule, risk, and
line SHA256 only.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import platform
import re
import socket
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = ROOT_DIR / "Taiji_Governance" / "red_blue_exchange"
DEFAULT_AUDIT = ROOT_DIR / "Taiji_Governance" / "logs" / "red_blue_exchange_audit.jsonl"
DECISION_SCHEMA = "taiji.human_decision_receipt.v1"
LOCAL_AUTH_MIN_LENGTH = 8

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "keys",
    "archive/secrets_backup",
    "Taiji_Odoo/odoo_data",
    "Taiji_Odoo/postgres_data",
}

CONTROL_ONLY_FILES = {
    "Taiji_AutoBuild/scripts/04_system_total_probe.py",
    "Taiji_AutoBuild/scripts/05_red_blue_exchange.py",
}

SCAN_SUFFIXES = {".py", ".sh", ".ps1", ".yml", ".yaml", ".Modelfile"}

RED_RULES = [
    {
        "id": "direct_remote_execution",
        "risk": "L3_metric_hazard",
        "patterns": [r"StrictHostKeyChecking=no", r"cat\s+.*\|\s*ssh\b", r"\bscp\b", r"systemctl\s+restart"],
        "blue_action": "Remove direct remote execution; require manifest-only/preflight-only plus human decision and Gateway policy.",
    },
    {
        "id": "live_compose_mutation",
        "risk": "L3_metric_hazard",
        "patterns": [r"docker\s+compose\s+up", r"docker\s+compose\s+down"],
        "blue_action": "Convert compose actions into reviewed deployment plans; do not run from scripts.",
    },
    {
        "id": "direct_cloud_ai_call",
        "risk": "L3_metric_hazard",
        "patterns": [r"genai\.Client", r"Gemini API", r"GOOGLE_APPLICATION_CREDENTIALS"],
        "blue_action": "Route cloud AI through Taiji Gateway / Audit / Policy; never send plaintext private context to cloud.",
    },
    {
        "id": "plaintext_credential_surface",
        "risk": "L3_metric_hazard",
        "patterns": [r"POSTGRES_PASSWORD\s*=", r"PASSWORD\s*=", r"client_secret", r"private_key"],
        "blue_action": "Move credential material to an approved secret boundary; report names and hashes only.",
    },
    {
        "id": "wide_bind_surface",
        "risk": "L2_drift",
        "patterns": [r"host\s*=\s*[\"']0\.0\.0\.0[\"']", r"0\.0\.0\.0:"],
        "blue_action": "Bind to 127.0.0.1 by default or require Gateway/VPN ACL proof.",
    },
    {
        "id": "execute_mode_surface",
        "risk": "L2_drift",
        "patterns": [r"--execute", r"taiji-guarded-run"],
        "blue_action": "Prefer manifest-only/preflight-only; keep live execution outside repo tools.",
    },
]

RISK_ORDER = {"L0_exact_match": 0, "L1_near": 1, "L2_drift": 2, "L3_metric_hazard": 3}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hardware_fingerprint() -> str:
    candidates = {
        "etc_machine_id": Path("/etc/machine-id"),
        "dbus_machine_id": Path("/var/lib/dbus/machine-id"),
        "dmi_product_uuid": Path("/sys/class/dmi/id/product_uuid"),
        "dmi_product_serial": Path("/sys/class/dmi/id/product_serial"),
        "dmi_board_serial": Path("/sys/class/dmi/id/board_serial"),
    }
    parts: list[str] = []
    for name, path in candidates.items():
        try:
            data = path.read_bytes().strip()
        except OSError:
            continue
        if data:
            parts.append(f"{name}={sha256_bytes(data)}")
    platform_blob = "\n".join(
        [platform.system(), platform.release(), platform.machine(), str(os.cpu_count() or ""), socket.gethostname()]
    ).encode("utf-8")
    parts.append(f"platform_runtime={sha256_bytes(platform_blob)}")
    return sha256_bytes("\n".join(sorted(parts)).encode("utf-8"))


def read_secret(env_name: str | None, file_path: Path | None, label: str) -> tuple[str, str]:
    if env_name:
        value = os.environ.get(env_name)
        if not value:
            raise SystemExit(f"missing {label} env: {env_name}")
        secret = value
        source = "env"
    elif file_path:
        secret = Path(file_path).read_text(encoding="utf-8").rstrip("\n")
        source = "file"
    else:
        if not sys.stdin.isatty():
            raise SystemExit(f"{label} requires env, file, or interactive TTY")
        secret = getpass.getpass(f"{label}: ")
        source = "tty"
    if len(secret) < LOCAL_AUTH_MIN_LENGTH:
        raise SystemExit(f"{label} is too short")
    return secret, source


def authorize_local_use(args: argparse.Namespace) -> dict[str, Any]:
    secret, source = read_secret(args.local_auth_env, args.local_auth_file, "local authorization")
    event_id = sha256_bytes(f"{hardware_fingerprint()}\0red-blue\0{secret}\0{utc_now()}".encode("utf-8"))[:24]
    return {
        "local_authorization": "passed",
        "local_authorization_source": source,
        "local_authorization_event_id": event_id,
        "local_authorization_secret_printed": False,
    }


def human_decision_id(payload: dict[str, Any]) -> str:
    clone = dict(payload)
    clone.pop("decision_id", None)
    data = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(data)


def verify_human_decision(path: Path, purpose: str) -> dict[str, Any]:
    receipt = json.loads(Path(path).read_text(encoding="utf-8"))
    if receipt.get("schema") != DECISION_SCHEMA:
        raise SystemExit("invalid human decision receipt schema")
    if receipt.get("hardware_fingerprint_sha256") != hardware_fingerprint():
        raise SystemExit("human decision receipt hardware mismatch")
    if receipt.get("decision") != "allow":
        raise SystemExit("human decision does not allow this action")
    scope = receipt.get("scope")
    if scope not in {purpose, "all"}:
        raise SystemExit(f"human decision scope mismatch: {scope}")
    expires_at = receipt.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        raise SystemExit("human decision receipt expired")
    if receipt.get("decision_id") != human_decision_id(receipt):
        raise SystemExit("human decision receipt integrity check failed")
    return {
        "human_decision": "passed",
        "human_decision_id": receipt["decision_id"],
        "human_decision_scope": scope,
        "human_decision_secret_printed": False,
    }


def append_audit(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts", utc_now())
    event.setdefault("actor", "red_blue_exchange")
    event.setdefault("external_api_called", False)
    event.setdefault("cloud_plaintext_sent", False)
    event.setdefault("secret_material_printed", False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT_DIR).as_posix()
    if rel in CONTROL_ONLY_FILES:
        return True
    return any(rel == item or rel.startswith(f"{item}/") for item in EXCLUDED_DIRS)


def iter_scan_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT_DIR.rglob("*"):
        if not path.is_file() or is_excluded(path):
            continue
        if path.suffix in SCAN_SUFFIXES or path.name.endswith(".Modelfile"):
            files.append(path)
    return sorted(files)


def red_team_pass(files: list[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(ROOT_DIR).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rule in RED_RULES:
                if any(re.search(pattern, line) for pattern in rule["patterns"]):
                    findings.append(
                        {
                            "rule": rule["id"],
                            "risk": rule["risk"],
                            "file": rel,
                            "line": lineno,
                            "line_sha256": sha256_bytes(line.encode("utf-8")),
                            "evidence_plaintext_stored": False,
                            "blue_action": rule["blue_action"],
                        }
                    )
    return findings


def blue_team_pass(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for finding in findings:
        item = grouped.setdefault(
            finding["rule"],
            {
                "rule": finding["rule"],
                "max_risk": finding["risk"],
                "finding_count": 0,
                "affected_files": set(),
                "action": finding["blue_action"],
            },
        )
        item["finding_count"] += 1
        item["affected_files"].add(finding["file"])
        if RISK_ORDER[finding["risk"]] > RISK_ORDER[item["max_risk"]]:
            item["max_risk"] = finding["risk"]
    return [
        {
            "rule": item["rule"],
            "max_risk": item["max_risk"],
            "finding_count": item["finding_count"],
            "affected_files": sorted(item["affected_files"]),
            "recommended_action": item["action"],
        }
        for item in sorted(grouped.values(), key=lambda x: (RISK_ORDER[x["max_risk"]], x["rule"]), reverse=True)
    ]


def exchange_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    if not findings:
        return {"risk": "L0_exact_match", "finding_count": 0}
    max_risk = max((item["risk"] for item in findings), key=lambda risk: RISK_ORDER[risk])
    return {"risk": max_risk, "finding_count": len(findings)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    finally:
        tmp = Path(tmp_name)
        if tmp.exists():
            tmp.unlink()


def build_report(auth: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    files = iter_scan_files()
    findings = red_team_pass(files)
    blue = blue_team_pass(findings)
    summary = exchange_summary(findings)
    return {
        "schema": "taiji.red_blue_exchange_report.v1",
        "generated_at": utc_now(),
        "mode": "local_design_review_red_blue_exchange_no_cloud_plaintext",
        "authority_context": {
            "red_blue_team_available": True,
            "use_scope": "system_design_only_not_daily_runtime",
            "runtime_use_allowed": False,
            "automation_allowed": False,
            "cloud_plaintext_available": False,
            "service_account_applicability": "metadata_only_not_accessed",
            "external_ai_called": False,
            "google_api_called": False,
            "openai_api_called": False,
        },
        "local_authorization": auth,
        "human_decision": decision,
        "scan_scope": {
            "root": str(ROOT_DIR),
            "file_count": len(files),
            "excluded_dirs": sorted(EXCLUDED_DIRS),
            "secret_contents_read": False,
            "plaintext_evidence_stored": False,
        },
        "red_team_round": {"round": 1, "findings": findings},
        "blue_team_round": {"round": 1, "mitigations": blue},
        "summary": summary,
        "packaging_gate": {
            "ready_to_land": summary["risk"] in {"L0_exact_match", "L1_near"},
            "design_review_only": True,
            "daily_runtime_use_allowed": False,
            "cloud_plaintext_must_remain_disabled": True,
            "required_before_landing": [
                "Remove or isolate L3 direct cloud and live deployment paths.",
                "Move credentials out of compose/scripts into approved secret boundary.",
                "Bind public services to localhost or prove Gateway/VPN ACL.",
                "Keep manifest-only/preflight-only as default.",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local design-only red/blue exchange without cloud plaintext.")
    parser.add_argument("--local-auth-env")
    parser.add_argument("--local-auth-file", type=Path)
    parser.add_argument("--human-decision", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    auth = authorize_local_use(args)
    decision = verify_human_decision(args.human_decision, "red-blue-exchange")
    report = build_report(auth, decision)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(args.output_dir) / f"red_blue_exchange_{stamp}.json"
    write_json(output, report)
    report_hash = sha256_file(output)
    append_audit(
        Path(args.audit_log),
        {
            "event": "red_blue_exchange",
            "result": "completed",
            "report": str(output),
            "report_sha256": report_hash,
            "risk": report["summary"]["risk"],
            "finding_count": report["summary"]["finding_count"],
            **auth,
            **decision,
        },
    )
    print(f"red_blue_exchange_report={output.resolve()}")
    print(f"red_blue_exchange_sha256={report_hash}")
    print(f"risk={report['summary']['risk']}")
    print(f"finding_count={report['summary']['finding_count']}")
    print("red_blue_team_available=true")
    print("use_scope=system_design_only_not_daily_runtime")
    print("cloud_plaintext_sent=false")
    print("external_ai_called=false")
    print("secret_material_printed=false")
    return 0 if report["summary"]["risk"] != "L3_metric_hazard" else 2


if __name__ == "__main__":
    raise SystemExit(main())
