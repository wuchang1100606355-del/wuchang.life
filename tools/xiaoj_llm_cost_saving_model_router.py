#!/usr/bin/env python3
"""Build a XiaoJ LLM cost-saving model route candidate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PACKAGE = "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/llm_cost_saving_model_router.py"


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
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.llm_cost_saving_model_router", SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_refs(path: str) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("--refs must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XiaoJ LLM cost-saving model route candidate")
    parser.add_argument("--intent", default="", help="Natural-language task intent")
    parser.add_argument("--surface", default="", help="Optional task surface id")
    parser.add_argument("--refs", default="", help="Optional safe refs JSON")
    parser.add_argument("--allow-external-candidate", action="store_true", help="Allow external candidate only when refs are ready")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    packet = service.build_llm_cost_saving_model_router_candidate(
        task_intent=args.intent,
        task_surface=args.surface,
        refs=read_refs(args.refs),
        allow_external_candidate=args.allow_external_candidate,
    )
    print(json.dumps(packet, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if not packet.get("state", "").startswith("HOLD") else 2


if __name__ == "__main__":
    raise SystemExit(main())
