#!/usr/bin/env python3
"""Build a LINE Official Account webhook candidate packet."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_webhook.py"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/line_official_account"
SERVICE_PACKAGE = "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services"


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_service():
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub("Taiji_Odoo.addons.wuchang_cafe_ai_gateway", ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway")
    ensure_package_stub(SERVICE_PACKAGE, ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services")
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.line_official_account_webhook", SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: str) -> dict:
    if not path:
        return {}
    json_path = Path(path).expanduser()
    if not json_path.is_absolute():
        json_path = ROOT / json_path
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{json_path} must contain a JSON object")
    return data


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE_{stamp}.json"


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE Official Account webhook candidate")
    parser.add_argument("--payload", default="", help="Webhook payload JSON")
    parser.add_argument("--headers", default="", help="Optional headers JSON")
    parser.add_argument("--verification", default="", help="Optional signature verification refs JSON")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    candidate = service.build_line_official_account_webhook_candidate(
        webhook_payload=read_json(args.payload),
        headers=read_json(args.headers),
        verification=read_json(args.verification),
    )
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE_REPORT_V1",
        "state": candidate["state"],
        "output_path": relative_path(out_path),
        "packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
        "failure_reasons": candidate.get("local_verifier", {}).get("failure_reasons", []),
        "side_effects": candidate.get("side_effects", {}),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if candidate["state"].startswith("READY_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
