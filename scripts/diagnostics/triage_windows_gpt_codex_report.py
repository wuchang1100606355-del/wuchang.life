#!/usr/bin/env python3
"""Triage Windows GPT/Codex diagnostic reports without reading secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_bool(value: Any) -> bool:
    return bool(value)


def initial_command_present(report: dict[str, Any], name: str) -> bool:
    return as_bool(report.get("commands", {}).get(name, {}).get("present"))


def command_present(report: dict[str, Any], name: str) -> bool:
    post_repair = report.get("post_repair_commands", {})
    if name in post_repair:
        return as_bool(post_repair.get(name, {}).get("present"))
    return initial_command_present(report, name)


def env_present(report: dict[str, Any], name: str) -> bool:
    for item in report.get("environment", []):
        if item.get("name") == name:
            return as_bool(item.get("present"))
    return False


def proxy_present(report: dict[str, Any]) -> bool:
    for item in report.get("environment", []):
        if "proxy" in str(item.get("name", "")).lower() and item.get("present"):
            return True
    registry = report.get("proxy", {}).get("registry_current_user", {})
    return bool(registry.get("ok") and registry.get("proxy_enable"))


def codex_candidate_paths(report: dict[str, Any]) -> list[str]:
    candidates = report.get("codex_local_state", {}).get("executable_candidates", [])
    paths: list[str] = []
    for item in candidates:
        if item.get("exists"):
            paths.append(str(item.get("path", "")))
    return [path for path in paths if path]


def load_nested_network_report(report: dict[str, Any], base_dir: Path) -> tuple[dict[str, Any] | None, str]:
    latest = report.get("network_diagnostics", {}).get("latest_report", {})
    report_path = latest.get("report_path")
    if not report_path:
        return None, "no nested network report path"
    path = Path(report_path)
    if not path.is_absolute():
        path = base_dir / path
    if not path.exists():
        return None, f"nested network report not readable: {path}"
    try:
        return read_json(path), str(path)
    except Exception as exc:  # pragma: no cover - diagnostic script
        return None, f"nested network report parse failed: {exc}"


def endpoint_summary(network_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not network_report:
        return []
    rows: list[dict[str, Any]] = []
    for endpoint in network_report.get("endpoints", []):
        dns_ok = bool(endpoint.get("dns", {}).get("ok"))
        tcp_ok = bool(endpoint.get("tcp_443", {}).get("tcp_test_succeeded"))
        tls_ok = bool(endpoint.get("tls", {}).get("ok"))
        https = endpoint.get("https_head", {})
        status = https.get("status_code")
        rows.append(
            {
                "name": endpoint.get("name"),
                "host": endpoint.get("host"),
                "dns_ok": dns_ok,
                "tcp_443_ok": tcp_ok,
                "tls_ok": tls_ok,
                "https_status": status,
                "https_ok": bool(https.get("ok")),
            }
        )
    return rows


def classify(report: dict[str, Any], network_report: dict[str, Any] | None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    user_path_repair = report.get("user_path_repair", {})
    codex_initial_present = initial_command_present(report, "codex")
    codex_effective_present = command_present(report, "codex")

    if user_path_repair.get("changed"):
        if codex_effective_present:
            findings.append(
                {
                    "code": "CODEX_USER_PATH_UPDATED_AND_VISIBLE",
                    "severity": "INFO",
                    "meaning": "Codex candidate directory was appended to the current user's PATH and is visible to the diagnostic process.",
                    "next_step": "Rerun readiness; restart already-open Windows terminals only if they still cannot see codex.",
                }
            )
        else:
            findings.append(
                {
                    "code": "CODEX_USER_PATH_UPDATED_BUT_NOT_VISIBLE",
                    "severity": "HIGH",
                    "meaning": "Codex candidate directory was appended to the current user's PATH, but codex is still not visible to the diagnostic process.",
                    "next_step": "Check whether the candidate file is launchable, blocked, or a non-command shim; restart the shell and rerun diagnostics.",
                }
            )
    if (not codex_effective_present) and (not user_path_repair.get("changed")):
        candidates = codex_candidate_paths(report)
        if candidates:
            findings.append(
                {
                    "code": "CODEX_EXISTS_BUT_NOT_IN_PATH",
                    "severity": "HIGH",
                    "meaning": "Codex executable candidates exist, but codex is not discoverable in PATH.",
                    "next_step": f"Add the executable directory to PATH or launch directly. First candidate: {candidates[0]}",
                }
            )
        else:
            findings.append(
                {
                    "code": "CODEX_CLI_NOT_IN_PATH",
                    "severity": "HIGH",
                    "meaning": "Codex command is not discoverable in PATH and no common executable candidate was found.",
                    "next_step": "Repair or reinstall Codex CLI before debugging API behavior.",
                }
            )
    elif codex_effective_present and not codex_initial_present:
        findings.append(
            {
                "code": "CODEX_BECAME_VISIBLE_AFTER_REPAIR",
                "severity": "INFO",
                "meaning": "Codex was not visible in the initial PATH snapshot but is visible after repair logic.",
                "next_step": "Use the post-repair readiness report as the current state authority.",
            }
        )
    if not command_present(report, "node"):
        findings.append(
            {
                "code": "NODE_MISSING",
                "severity": "MEDIUM",
                "meaning": "Node.js is not discoverable; npm-based Codex tools or docs helpers may fail.",
                "next_step": "Repair Node.js/npm if this Windows Codex setup depends on npm.",
            }
        )
    if not env_present(report, "OPENAI_API_KEY"):
        findings.append(
            {
                "code": "OPENAI_API_KEY_NOT_VISIBLE",
                "severity": "MEDIUM",
                "meaning": "OPENAI_API_KEY name is not visible in process, user, or machine environment.",
                "next_step": "Configure the key in the same Windows user/session used by Codex if API-backed operation is required.",
            }
        )
    if proxy_present(report):
        findings.append(
            {
                "code": "PROXY_CONFIGURATION_PRESENT",
                "severity": "MEDIUM",
                "meaning": "Proxy values are present in environment or current-user Windows proxy settings.",
                "next_step": "Compare WinHTTP, browser, npm, and process proxy values; test clean proxy wrapper.",
            }
        )

    for endpoint in endpoint_summary(network_report):
        host = str(endpoint.get("host"))
        status = endpoint.get("https_status")
        if not endpoint["dns_ok"]:
            findings.append(
                {
                    "code": "DNS_FAILURE",
                    "severity": "HIGH",
                    "meaning": f"{host} DNS resolution failed.",
                    "next_step": "Fix DNS/VPN/router resolver path before changing Codex configuration.",
                }
            )
        elif not endpoint["tcp_443_ok"]:
            findings.append(
                {
                    "code": "TCP_443_FAILURE",
                    "severity": "HIGH",
                    "meaning": f"{host} TCP 443 failed after DNS succeeded.",
                    "next_step": "Check firewall, VPN, router, ISP, or endpoint security blocking 443.",
                }
            )
        elif not endpoint["tls_ok"]:
            findings.append(
                {
                    "code": "TLS_HANDSHAKE_FAILURE",
                    "severity": "HIGH",
                    "meaning": f"{host} TLS handshake failed after TCP succeeded.",
                    "next_step": "Check TLS inspection, security software, or certificate interception.",
                }
            )
        elif host == "api.openai.com" and status == 401:
            findings.append(
                {
                    "code": "OPENAI_API_REACHABLE_AUTH_REQUIRED",
                    "severity": "INFO",
                    "meaning": "OpenAI API endpoint is reachable; 401 means authentication is required.",
                    "next_step": "Continue with credential/session configuration, not network repair.",
                }
            )
        elif host in {"chatgpt.com", "auth.openai.com"} and status == 403:
            findings.append(
                {
                    "code": "CHATGPT_WEB_CHALLENGE",
                    "severity": "MEDIUM",
                    "meaning": f"{host} is reachable but returned a challenge/403.",
                    "next_step": "Test clean Edge profile; compare VPN/proxy reputation and browser profile state.",
                }
            )

    if not findings:
        findings.append(
            {
                "code": "NO_OBVIOUS_FAILURE_IN_REPORT",
                "severity": "INFO",
                "meaning": "The report did not expose a clear DNS/TCP/TLS/Codex/PATH/API-key failure.",
                "next_step": "Capture the exact Windows error message and rerun diagnostics from the failing shell.",
            }
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="WINDOWS_GPT_CODEX_REPAIR_REPORT.json")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    report_path = args.report.resolve()
    report = read_json(report_path)
    out_dir = args.out_dir.resolve() if args.out_dir else report_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    network_report, network_report_note = load_nested_network_report(report, report_path.parent)
    findings = classify(report, network_report)

    triage = {
        "schema": "TAIJI_WINDOWS_GPT_CODEX_TRIAGE_V1",
        "state": "TRIAGE_COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(report_path),
        "source_report_sha256": sha256(report_path),
        "nested_network_report": network_report_note,
        "side_effects": {
            "installs_packages": False,
            "changes_network_settings": False,
            "reads_secret_values": False,
            "external_api_mutation": False,
        },
        "findings": findings,
    }

    json_path = out_dir / "WINDOWS_GPT_CODEX_TRIAGE_SUMMARY.json"
    text_path = out_dir / "WINDOWS_GPT_CODEX_TRIAGE_SUMMARY.txt"
    seal_path = out_dir / "TRIAGE_EVIDENCE_SEAL.txt"

    json_path.write_text(json.dumps(triage, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "TAIJI_WINDOWS_GPT_CODEX_TRIAGE_V1",
        f"generated_at_utc={triage['generated_at_utc']}",
        f"source_report={report_path}",
        "",
        "findings:",
    ]
    for finding in findings:
        lines.append(f"- {finding['severity']} {finding['code']}: {finding['meaning']} Next: {finding['next_step']}")
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    seal_lines = [
        "schema=TAIJI_WINDOWS_GPT_CODEX_TRIAGE_SEAL_V1",
        f"generated_at_utc={datetime.now(timezone.utc).isoformat()}",
        f"source_report={report_path}",
        f"source_report_sha256={sha256(report_path)}",
        f"triage_json={json_path}",
        f"triage_json_sha256={sha256(json_path)}",
        f"triage_text={text_path}",
        f"triage_text_sha256={sha256(text_path)}",
        "side_effects.installs_packages=false",
        "side_effects.changes_network_settings=false",
        "side_effects.reads_secret_values=false",
        "side_effects.external_api_mutation=false",
    ]
    seal_path.write_text("\n".join(seal_lines) + "\n", encoding="utf-8")

    print("STATE=TRIAGE_COMPLETE")
    print(f"TRIAGE_JSON={json_path}")
    print(f"TRIAGE_TEXT={text_path}")
    print(f"SEAL={seal_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
