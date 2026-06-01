#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Readonly Service Health Checker

GET-only local service health summary.
No restart, no kill, no POST, no SSH.
"""

from __future__ import annotations

import datetime as dt
import json
import socket
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "runtime" / "reports"

TARGETS = [
    ("gateway_9002_health", "http://127.0.0.1:9002/health"),
    ("gateway_9002_healthz", "http://127.0.0.1:9002/healthz"),
    ("gateway_8081_health", "http://127.0.0.1:8081/health"),
    ("runtime_api_8091", "http://127.0.0.1:8091/health"),
    ("runtime_core_8099", "http://127.0.0.1:8099/health"),
    ("openai_bridge_8098_models", "http://127.0.0.1:8098/v1/models"),
    ("openwebui_8080", "http://127.0.0.1:8080"),
    ("ollama_11434_tags", "http://127.0.0.1:11434/api/tags"),
]


def check(url: str, timeout: float = 2.0) -> Dict[str, object]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(300).decode("utf-8", errors="replace")
            ms = round((dt.datetime.now(dt.timezone.utc) - started).total_seconds() * 1000)
            return {
                "status": "OK",
                "http_status": r.status,
                "latency_ms": ms,
                "preview": body.replace("\n", " ")[:200],
            }
    except socket.timeout:
        return {"status": "TIMEOUT", "error": "socket_timeout"}
    except urllib.error.HTTPError as e:
        return {"status": "HTTP_ERROR", "http_status": e.code, "error": str(e)}
    except Exception as e:
        return {"status": "FAIL", "error": type(e).__name__ + ":" + str(e)[:200]}


def to_markdown(result: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Service Health Readonly Report")
    lines.append("")
    lines.append(f"- Generated: `{result['generated_at']}`")
    lines.append("- Mode: `GET-only / no restart / no POST / no SSH`")
    lines.append("")
    lines.append("| Service | URL | Status | HTTP | Latency ms | Error / Preview |")
    lines.append("|---|---|---:|---:|---:|---|")
    for row in result["checks"]:  # type: ignore
        lines.append(
            f"| {row['name']} | `{row['url']}` | {row['status']} | "
            f"{row.get('http_status','')} | {row.get('latency_ms','')} | "
            f"{row.get('error', row.get('preview',''))} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    checks = []
    for name, url in TARGETS:
        r = check(url)
        r["name"] = name
        r["url"] = url
        checks.append(r)

    result = {
        "tool": "service_health_readonly",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "GET-only",
        "restart": False,
        "post": False,
        "ssh": False,
        "checks": checks,
    }

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"service_health_readonly_{ts}.json"
    md_path = REPORT_DIR / f"service_health_readonly_{ts}.md"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(result), encoding="utf-8")

    print(json.dumps({
        "decision": "service_health_checked",
        "json": str(json_path),
        "markdown": str(md_path),
        "ok": sum(1 for x in checks if x["status"] == "OK"),
        "total": len(checks),
        "restart": False,
        "ssh": False,
        "post": False,
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
