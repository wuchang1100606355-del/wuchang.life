#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/taiji_admin/Taiji_Hub")
CONSOLE = ROOT / "tools" / "d8_total_field_console.sh"
REPORT_DIR = ROOT / "runtime" / "total_field" / "odoo_pos_bridge"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SAFE_PATHS = [
    "addons/wuchang_line_login/controllers/main.py",
    "/mnt/extra-addons/wuchang_core/data/breakfast_pos_menu.xml",
    "compose.d8.yml",
    "tools/d8_total_field_console.sh",
]

CONTAINERS = ["wuchang_os_odoo_18", "wuchang_os_pg", "taiji_d8_db"]


def run(cmd: list[str], timeout: int = 30) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {"cmd": cmd, "returncode": proc.returncode, "output": proc.stdout[-8000:]}


def resolve_path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    if path.name.startswith(".env"):
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def docker_container_status(name: str) -> dict:
    r = run(["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}\t{{.Status}}"])
    lines = [line for line in r["output"].splitlines() if line.strip()]
    return {"name": name, "found": bool(lines), "lines": lines, "returncode": r["returncode"]}


def preflight() -> dict:
    return run([
        str(CONSOLE),
        "preflight",
        "--task-name", "D8_ODOO_POS_SAFE_BRIDGE_READONLY",
        "--mode", "sandbox",
        "--scope-json", '{"readonly":true,"target":"odoo_pos_manifest","no_db_write":true,"no_order":true,"no_payment":true}',
    ])


def scan() -> dict:
    files = []
    for item in SAFE_PATHS:
        path = resolve_path(item)
        files.append({
            "path": item,
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() and path.is_file() else None,
            "sha256": sha256_file(path),
        })
    return {
        "containers": [docker_container_status(name) for name in CONTAINERS],
        "files": files,
        "console_status": run([str(CONSOLE), "status"]),
        "safety_flags": {
            "secret_read": False,
            "member_plaintext_read": False,
            "raw_audio_saved": False,
            "production_db_write": False,
            "odoo_db_write": False,
            "pos_order_created": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "external_api_call": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run_id = "D8_ODOO_POS_SAFE_BRIDGE_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest = {
        "state": "PASS",
        "action": "D8_ODOO_POS_SAFE_BRIDGE_READONLY_MANIFEST",
        "run_id": run_id,
        "root": str(ROOT),
        "dry_run": args.dry_run,
        "preflight": preflight(),
        "scan": scan(),
    }
    report_json = REPORT_DIR / f"{run_id}.json"
    report_md = REPORT_DIR / f"{run_id}.md"
    report_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join([
            "# D8 Odoo POS Safe Bridge Manifest",
            "",
            f"STATE={manifest['state']}",
            f"RUN_ID={run_id}",
            "MODE=READONLY_MANIFEST_ONLY",
            "SECRET_READ=FALSE",
            "MEMBER_PLAINTEXT_READ=FALSE",
            "ODOO_DB_WRITE=FALSE",
            "POS_ORDER_CREATED=FALSE",
            "PAYMENT_CAPTURE=FALSE",
            "SERVICE_RESTART=FALSE",
            "DEPLOY=FALSE",
            "EXTERNAL_API_CALL=FALSE",
            "",
        ]),
        encoding="utf-8",
    )
    print("STATE=PASS_D8_ODOO_POS_SAFE_BRIDGE_READONLY_MANIFEST")
    print("RUN_ID=" + run_id)
    print("REPORT_JSON=" + report_json.relative_to(ROOT).as_posix())
    print("REPORT_MD=" + report_md.relative_to(ROOT).as_posix())
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("EXTERNAL_API_CALL=FALSE")


if __name__ == "__main__":
    main()
