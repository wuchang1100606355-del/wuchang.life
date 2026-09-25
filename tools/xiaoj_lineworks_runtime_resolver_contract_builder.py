#!/usr/bin/env python3
"""Build a LINE WORKS runtime resolver contract from safe binding refs only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_runtime_resolver.py"
DEFAULT_REFS = ROOT / "packets/product_av_ordering_ai/lineworks_release_refs_template.json"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/lineworks"
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
    ensure_package_stub(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway",
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway",
    )
    ensure_package_stub(SERVICE_PACKAGE, ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services")
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.lineworks_runtime_resolver", SERVICE)
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
    return DEFAULT_OUT_DIR / f"LINEWORKS_RUNTIME_RESOLVER_CONTRACT_{stamp}.json"


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE WORKS runtime resolver contract")
    parser.add_argument("--refs", default=str(DEFAULT_REFS), help="JSON with connector_refs")
    parser.add_argument("--bindings", default="", help="Optional JSON with runtime_resolver_bindings")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--allow-verified", action="store_true", help="Preserve verified=true only when bindings are safe")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    refs = read_json(args.refs)
    bindings_source = read_json(args.bindings)
    connector_refs = refs.get("connector_refs") if isinstance(refs.get("connector_refs"), dict) else {}
    resolver_bindings = (
        bindings_source.get("runtime_resolver_bindings")
        if isinstance(bindings_source.get("runtime_resolver_bindings"), dict)
        else bindings_source
    )
    contract = service.build_lineworks_runtime_resolver_contract(
        connector_refs=connector_refs,
        resolver_bindings=resolver_bindings,
        allow_verified=args.allow_verified,
    )

    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_REPORT_V1",
        "state": contract["state"],
        "output_path": relative_path(out_path),
        "resolver_contract_hash": contract["resolver_contract_hash"],
        "draft_warnings": contract["draft_warnings"],
        "side_effects": contract["p1_side_effects"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if contract["state"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
