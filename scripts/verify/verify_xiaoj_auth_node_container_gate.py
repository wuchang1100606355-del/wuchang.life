#!/usr/bin/env python3
"""Read-only XiaoJ auth and node/container gate verifier.

This verifier observes only public/local status:
- local HTTP route status codes
- docker container names/status/ports from `docker ps`
- non-secret Total Field manifests/reports

It does not read `.env`, docker inspect output, Odoo config, database rows,
quarantine originals, member plaintext, OAuth secrets, or payment data.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NODE_MANIFEST = ROOT / "runtime/total_field/node_container_scope/TOTAL_FIELD_NODE_CONTAINER_MANIFEST_20260624.json"
RISK_MATRIX = ROOT / "docs/total_field/TOTAL_FIELD_NODE_CONTAINER_MANIFEST_AND_RISK_MATRIX.md"
SCOPE_DOC = ROOT / "docs/total_field/TOTAL_FIELD_ALL_NODES_AND_CONTAINERS_SCOPE.md"
AUTH_GAP = ROOT / "docs/total_field/XIAOJ_AV_ORDERING_LOCAL_BRAIN_AUTH_TOTAL_FIELD_GAP_MAP.md"
MARKET_PACKET = ROOT / "docs/product/XIAOJ_AV_ORDERING_MARKET_COMPETITIVENESS_AND_STICKINESS_PACKET.md"


SAFETY_FALSE_FLAGS = [
    "SECRET_READ",
    "MEMBER_PLAINTEXT_READ",
    "RAW_AUDIO_SAVED",
    "PRODUCTION_DB_WRITE",
    "ODOO_DB_WRITE",
    "ODOO_MODULE_UPGRADE",
    "POS_ORDER_CREATED",
    "PAYMENT_CAPTURE",
    "SERVICE_RESTART",
    "CONTAINER_MUTATION",
    "DEPLOY",
    "PRODUCTION_RELEASE",
    "EXTERNAL_API_CALL",
    "EMBEDDING_GENERATED",
    "ODOO_FILES_TOUCHED",
    "LINE_LOGIN_FILES_TOUCHED",
]


EXPECTED_CONTAINERS = {
    "taiji_d8_db",
    "wuchang_os_odoo_18",
    "wuchang_os_pg",
    "quarantine_wuchang_os_pg_20260508_200520",
}


ROUTES = {
    "web_signup": ("/web/signup", {200}),
    "xiaoj_ordering": ("/wuchang/xiaoj/ordering", {200, 302, 303}),
    "pos_ui": ("/pos/ui", {200, 302, 303}),
    "line_login": ("/line/login", {200, 302, 303}),
    "line_callback": ("/line/callback", {200, 302, 303, 400}),
    "google_login": ("/google/member/login", {200, 302, 303}),
    "google_welcome": ("/google/member/welcome", {200, 302, 303}),
    "member_register_start": ("/wuchang/member/register/start", {200, 302, 303}),
}


@dataclass(frozen=True)
class HttpResult:
    name: str
    route: str
    url: str
    status: int | None
    expected: list[int]
    ok: bool
    error: str | None = None


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        fail(f"json_invalid:{path.relative_to(ROOT)}:{exc}")


def docker_ps() -> list[dict[str, str]]:
    cmd = ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        fail(f"docker_ps_unavailable:{exc}")
    if proc.returncode != 0:
        fail("docker_ps_failed")
    rows: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t", maxsplit=3)
        if len(parts) == 4:
            rows.append({"name": parts[0], "image": parts[1], "status": parts[2], "ports": parts[3]})
    return rows


def http_status(base_url: str, name: str, route: str, expected: set[int]) -> HttpResult:
    url = base_url.rstrip("/") + route
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status = int(response.status)
            return HttpResult(name, route, url, status, sorted(expected), status in expected)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        return HttpResult(name, route, url, status, sorted(expected), status in expected, f"HTTPError:{status}")
    except Exception as exc:  # noqa: BLE001 - verifier should record transport errors compactly
        return HttpResult(name, route, url, None, sorted(expected), False, type(exc).__name__)


def verify_required_docs() -> None:
    required = [NODE_MANIFEST, RISK_MATRIX, SCOPE_DOC, AUTH_GAP, MARKET_PACKET]
    for path in required:
        read_text(path)
    matrix = read_text(RISK_MATRIX)
    for needle in [
        "LINE/Google auth",
        "runtime routes previously observed as HTTP 404",
        "CONTAINER_MUTATION=FALSE",
        "XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1",
    ]:
        if needle not in matrix:
            fail(f"risk_matrix_missing:{needle}")


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(NODE_MANIFEST)
    scope = manifest.get("scope", {})
    if scope.get("total_field") != "ALL_NODES_AND_CONTAINERS":
        fail("manifest_scope_not_all_nodes_and_containers")
    if scope.get("runtime_mutation_authority") is not False:
        fail("manifest_runtime_mutation_authority_not_false")
    safety = manifest.get("safety_flags", {})
    for flag in SAFETY_FALSE_FLAGS:
        if safety.get(flag) is not False:
            fail(f"safety_flag_not_false:{flag}")
    if safety.get("D8_LOCAL_DB_WRITE") is not True:
        fail("d8_local_db_write_not_true")
    names = {item.get("name") for item in manifest.get("observed_containers", [])}
    missing = EXPECTED_CONTAINERS - names
    if missing:
        fail("manifest_missing_container:" + ",".join(sorted(missing)))
    route_gates = manifest.get("xiaoj_route_gates", {})
    for route_name in ["line_login", "line_callback", "google_login", "google_welcome"]:
        if route_gates.get(route_name, {}).get("status") != "FAIL_RUNTIME":
            fail(f"manifest_route_gate_not_fail_runtime:{route_name}")
    return manifest


def build_report(base_url: str) -> dict[str, Any]:
    verify_required_docs()
    manifest = verify_manifest()
    containers = docker_ps()
    observed_names = {item["name"] for item in containers}
    missing_running = sorted(EXPECTED_CONTAINERS - observed_names)
    http_results = [
        http_status(base_url, name, route, expected)
        for name, (route, expected) in ROUTES.items()
    ]
    route_gate_ready = all(result.ok for result in http_results)
    container_gate_ready = not missing_running
    state = "PASS_XIAOJ_AUTH_NODE_CONTAINER_GATE" if route_gate_ready and container_gate_ready else "HOLD_XIAOJ_AUTH_ROUTE_GATE"
    if missing_running:
        state = "HOLD_NODE_CONTAINER_GATE"
    return {
        "state": state,
        "action": "VERIFY_XIAOJ_AUTH_NODE_CONTAINER_GATE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(ROOT),
        "base_url": base_url,
        "manifest": str(NODE_MANIFEST.relative_to(ROOT)),
        "risk_matrix": str(RISK_MATRIX.relative_to(ROOT)),
        "expected_containers": sorted(EXPECTED_CONTAINERS),
        "observed_containers": containers,
        "missing_running_containers": missing_running,
        "http_results": [asdict(item) for item in http_results],
        "ready": {
            "container_gate": container_gate_ready,
            "route_gate": route_gate_ready,
            "line_google_auth": all(
                result.ok
                for result in http_results
                if result.name in {"line_login", "line_callback", "google_login", "google_welcome"}
            ),
        },
        "next_land_gate": manifest.get("next_land_gate", "XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1"),
        "safety_flags": {
            "SECRET_READ": False,
            "MEMBER_PLAINTEXT_READ": False,
            "RAW_AUDIO_SAVED": False,
            "D8_LOCAL_DB_WRITE": True,
            "PRODUCTION_DB_WRITE": False,
            "ODOO_DB_WRITE": False,
            "ODOO_MODULE_UPGRADE": False,
            "POS_ORDER_CREATED": False,
            "PAYMENT_CAPTURE": False,
            "SERVICE_RESTART": False,
            "CONTAINER_MUTATION": False,
            "DEPLOY": False,
            "PRODUCTION_RELEASE": False,
            "EXTERNAL_API_CALL": False,
            "EMBEDDING_GENERATED": False,
            "ODOO_FILES_TOUCHED": False,
            "LINE_LOGIN_FILES_TOUCHED": False,
            "DO_NOT_TOUCH_AGENTS_MD": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify XiaoJ auth and node/container gate in read-only mode.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8069")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = build_report(args.base_url)
    if args.report:
        path = args.report if args.report.is_absolute() else ROOT / args.report
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"STATE={report['state']}")
    print("ACTION=VERIFY_XIAOJ_AUTH_NODE_CONTAINER_GATE")
    print(f"BASE_URL={report['base_url']}")
    print(f"CONTAINER_GATE={'PASS' if report['ready']['container_gate'] else 'HOLD'}")
    print(f"ROUTE_GATE={'PASS' if report['ready']['route_gate'] else 'HOLD'}")
    print(f"LINE_GOOGLE_AUTH={'PASS' if report['ready']['line_google_auth'] else 'HOLD'}")
    print(f"NEXT_LAND_GATE={report['next_land_gate']}")
    if args.report:
        print(f"REPORT={path.relative_to(ROOT)}")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("CONTAINER_MUTATION=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
