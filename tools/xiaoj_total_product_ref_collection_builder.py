#!/usr/bin/env python3
"""Build/validate XiaoJ total product ref collection draft."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_ref_collection.py"
DEFAULT_INPUT = ROOT / "packets/product_av_ordering_ai/xiaoj_total_product_ref_collection_template.json"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/total_product_ref_collection"
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
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.total_product_ref_collection", SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def resolve_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_{stamp}.json"


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XiaoJ total product ref collection draft")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input ref collection JSON")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--worksheet-out", default="", help="Optional markdown worksheet output path")
    parser.add_argument("--allow-verified", action="store_true", help="Preserve verified=true only when refs and hashes are safe")
    parser.add_argument("--emit-template", action="store_true", help="Write a refs-only input template instead of validating refs")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.emit_template:
        template = service.build_total_product_ref_collection_input_template()
        out_path.write_text(
            json.dumps(template, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary = {
            "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_TEMPLATE_CLI_REPORT_V1",
            "state": template["state"],
            "output_path": relative_path(out_path),
            "ref_groups": [
                "lineworks",
                "line_official_account",
                "merchant_formal_release",
                "association_sovereign_member",
                "resident_property_management",
            ],
            "side_effects": {
                "external_api_call": False,
                "formal_lineworks_send": False,
                "formal_line_message_send": False,
                "official_account_setting_changed": False,
                "formal_member_registration": False,
                "formal_db_write": False,
                "formal_pos_write": False,
                "payment_capture": False,
                "secret_read": False,
                "member_plaintext_read": False,
                "resident_plaintext_read": False,
                "raw_audio_saved": False,
                "raw_video_saved": False,
                "deploy": False,
                "service_restart": False,
            },
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0

    input_path = resolve_path(args.input)
    draft = service.build_total_product_ref_collection_draft(
        read_json(input_path),
        allow_verified=args.allow_verified,
    )
    worksheet_path = Path(args.worksheet_out).expanduser() if args.worksheet_out else None
    if worksheet_path is not None:
        if not worksheet_path.is_absolute():
            worksheet_path = ROOT / worksheet_path
        worksheet_path.parent.mkdir(parents=True, exist_ok=True)
        worksheet_path.write_text(draft.get("operator_fill_worksheet_md", ""), encoding="utf-8")
    out_path.write_text(
        json.dumps(draft, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_CLI_REPORT_V1",
        "state": draft["state"],
        "output_path": relative_path(out_path),
        "allow_verified_input": draft.get("allow_verified_input") is True,
        "ready_for_handoff_candidate": draft.get("ready_for_handoff_candidate") is True,
        "draft_warnings_count": len(draft.get("draft_warnings", [])),
        "human_fill_ready_count": draft.get("operator_fill_summary", {}).get("ready_count", 0),
        "human_fill_needs_count": draft.get("operator_fill_summary", {}).get("needs_human_fill_count", 0),
        "operator_fill_worksheet_present": bool(draft.get("operator_fill_worksheet_md")),
        "operator_fill_worksheet_path": relative_path(worksheet_path) if worksheet_path is not None else "",
        "draft_hash": draft.get("draft_hash", ""),
        "side_effects": draft.get("side_effects", {}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if draft["state"].startswith("TOTAL_PRODUCT_REFS_READY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
