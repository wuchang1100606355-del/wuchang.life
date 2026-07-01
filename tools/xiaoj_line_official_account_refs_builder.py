#!/usr/bin/env python3
"""Build a LINE Official Account refs draft from safe refs only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_refs.py"
DEFAULT_INPUT = ROOT / "packets/product_av_ordering_ai/line_official_account_refs_template.json"
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
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.line_official_account_refs", SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"LINE_OFFICIAL_ACCOUNT_REFS_DRAFT_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE Official Account refs draft")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input JSON with refs")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    source = read_json(input_path)
    service = load_service()
    draft = service.build_line_official_account_refs_draft(source.get("refs", source))

    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(draft, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_REFS_BUILDER_REPORT_V1",
        "state": draft["state"],
        "output_path": relative_path(out_path),
        "draft_hash": draft["draft_hash"],
        "draft_warnings": draft["draft_warnings"],
        "side_effects": draft["side_effects"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if draft["state"].startswith("LINE_OFFICIAL_ACCOUNT_REFS_READY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
