#!/usr/bin/env python3
"""Build XiaoJ total product operator handoff pack."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_handoff.py"
DEFAULT_CONFIG = ROOT / "packets/product_av_ordering_ai/xiaoj_merchant_productization_readiness_template.json"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/total_product_handoff"
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
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.total_product_handoff", SERVICE)
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
    return DEFAULT_OUT_DIR / f"XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_{stamp}.json"


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XiaoJ total product operator handoff pack")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Merchant productization readiness input JSON")
    parser.add_argument("--ref-collection", default="", help="Optional total product ref collection draft JSON")
    parser.add_argument("--out", default="", help="Output report path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    config_path = resolve_path(args.config)
    config = read_json(config_path)
    input_ref = str(config_path)
    if args.ref_collection:
        ref_collection_path = resolve_path(args.ref_collection)
        ref_collection = read_json(ref_collection_path)
        handoff_inputs = ref_collection.get("handoff_inputs") if isinstance(ref_collection.get("handoff_inputs"), dict) else {}
        formal_release_refs = handoff_inputs.get("formal_release_refs") if isinstance(handoff_inputs.get("formal_release_refs"), dict) else {}
        lineworks_refs = handoff_inputs.get("lineworks_refs") if isinstance(handoff_inputs.get("lineworks_refs"), dict) else {}
        line_official_refs = (
            handoff_inputs.get("line_official_account_refs")
            if isinstance(handoff_inputs.get("line_official_account_refs"), dict)
            else {}
        )
        input_ref = str(ref_collection_path)
    else:
        formal_release_refs = config.get("formal_release_refs") if isinstance(config.get("formal_release_refs"), dict) else {}
        lineworks_refs = read_json(resolve_path(config.get("lineworks_refs_path", "")))
        line_official_refs = read_json(resolve_path(config.get("line_official_account_refs_path", "")))
    service = load_service()
    pack = service.build_total_product_operator_handoff(
        formal_release_refs=formal_release_refs,
        lineworks_refs=lineworks_refs,
        line_official_account_refs=line_official_refs,
        line_official_account_intent=config.get("line_official_account_intent", ""),
        lineworks_probe=config.get("lineworks_probe") if isinstance(config.get("lineworks_probe"), dict) else {},
        input_ref=input_ref,
    )
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_CLI_REPORT_V1",
        "state": pack["state"],
        "output_path": relative_path(out_path),
        "handoff_ready_for_operator": pack.get("handoff_ready_for_operator") is True,
        "production_activation_ready": pack.get("production_activation_ready") is True,
        "operator_next_actions": pack.get("merchant_productization", {}).get("operator_next_actions", []),
        "handoff_hash": pack.get("handoff_hash", ""),
        "side_effects": pack.get("side_effects", {}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if pack["state"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
