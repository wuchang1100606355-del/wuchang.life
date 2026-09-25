#!/usr/bin/env python3
"""Build a self-contained XiaoJ total product operator bundle.

The bundle is P1-safe: it writes local files only and never reads secrets,
calls external APIs, writes Odoo/POS, captures payment, deploys, or restarts
services.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / "runtime/product_av_ordering_ai/total_product_operator_bundle"
SERVICE_PACKAGE = "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services"
REF_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_ref_collection.py"
HANDOFF_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_handoff.py"
BUNDLE_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_operator_bundle.py"


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_module(module_name: str, path: Path):
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub("Taiji_Odoo.addons.wuchang_cafe_ai_gateway", ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway")
    ensure_package_stub(SERVICE_PACKAGE, ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services")
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.{module_name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, value: dict, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def side_effects_false() -> dict:
    return {
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
    }


def build_readme(bundle_name: str, ref_collection: dict, handoff: dict, *, allow_verified: bool, input_refs_path: str) -> str:
    summary = ref_collection.get("operator_fill_summary", {})
    input_note = input_refs_path or "generated refs-only template"
    lines = [
        "# XiaoJ Total Product Operator Bundle",
        "",
        f"BUNDLE: `{bundle_name}`",
        f"INPUT_REFS: `{input_note}`",
        f"ALLOW_VERIFIED: `{str(allow_verified).lower()}`",
        "",
        "## State",
        "",
        f"- Ref collection: `{ref_collection.get('state', '')}`",
        f"- Handoff: `{handoff.get('state', '')}`",
        f"- Production activation ready: `{str(handoff.get('production_activation_ready') is True).lower()}`",
        f"- Refs ready: `{summary.get('ready_count', 0)}/{summary.get('total_required', 0)}`",
        f"- Refs needing human fill: `{summary.get('needs_human_fill_count', 0)}`",
        "",
        "## Files",
        "",
        "- `ref_template.json`: generated template or copied refs input.",
        "- `ref_collection.json`: normalized draft with `handoff_inputs`.",
        "- `ref_worksheet.md`: human worksheet to fill refs and packet hashes.",
        "- `handoff.json`: operator handoff pack.",
        "- `MANIFEST.json`: file hashes, state, and side-effect boundary.",
        "",
        "## Operator Flow",
        "",
        "1. Open `ref_worksheet.md`.",
        "2. Fill refs in `ref_template.json` or a copied refs input JSON.",
        "3. Do not paste passwords, token values, API keys, member plaintext, resident plaintext, payment data, raw audio, or raw video.",
        "4. Re-run ref collection with `--allow-verified` only after human owner/admin review.",
        "5. Build the handoff pack with the verified ref collection.",
        "",
        "## Commands",
        "",
        "```bash",
        "python3 tools/xiaoj_total_product_ref_collection_builder.py \\",
        "  --input runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle>/ref_template.json \\",
        "  --worksheet-out runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle>/ref_worksheet.md \\",
        "  --pretty",
        "",
        "python3 tools/xiaoj_total_product_operator_bundle.py \\",
        "  --input-refs runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle>/ref_template.json \\",
        "  --allow-verified \\",
        "  --out-dir runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle> \\",
        "  --pretty",
        "",
        "python3 tools/xiaoj_total_product_handoff_pack.py \\",
        "  --ref-collection runtime/product_av_ordering_ai/total_product_operator_bundle/<bundle>/ref_collection.json \\",
        "  --pretty",
        "```",
        "",
        "## P1 Boundary",
        "",
        "All side effects in this bundle are false: no external API calls, no LINE/LINE WORKS send, no Odoo/POS write, no payment capture, no secret read, no member/resident plaintext read, no deploy, and no restart.",
        "",
    ]
    return "\n".join(lines)


def build_bundle(out_dir: Path, pretty: bool, *, input_refs_path: Path | None = None, allow_verified: bool = False) -> dict:
    bundle_service = load_module("total_product_operator_bundle", BUNDLE_SERVICE)

    refs_input = read_json(input_refs_path) if input_refs_path is not None else None
    payload = bundle_service.build_total_product_operator_bundle_payload(
        refs=refs_input,
        allow_verified=allow_verified,
        input_ref=relative_path(input_refs_path) if input_refs_path is not None else "",
        bundle_ref=relative_path(out_dir),
    )
    bundle_files = payload.get("bundle_files", {})
    ref_template = bundle_files["ref_template.json"]["content"]
    ref_collection = bundle_files["ref_collection.json"]["content"]
    worksheet = bundle_files["ref_worksheet.md"]["content"]
    handoff = bundle_files["handoff.json"]["content"]
    readme = bundle_files["README.md"]["content"]

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "ref_template.json", ref_template, pretty)
    write_json(out_dir / "ref_collection.json", ref_collection, pretty)
    (out_dir / "ref_worksheet.md").write_text(worksheet, encoding="utf-8")
    write_json(out_dir / "handoff.json", handoff, pretty)
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    files = ["README.md", "ref_template.json", "ref_collection.json", "ref_worksheet.md", "handoff.json"]
    manifest_seed = {
        "ref_collection_hash": ref_collection.get("draft_hash", ""),
        "handoff_hash": handoff.get("handoff_hash", ""),
        "allow_verified": allow_verified,
        "input_refs_path": relative_path(input_refs_path) if input_refs_path is not None else "",
        "files": files,
    }
    manifest = {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_MANIFEST_V1",
        "state": "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bundle_dir": relative_path(out_dir),
        "input_refs_path": relative_path(input_refs_path) if input_refs_path is not None else "",
        "allow_verified": allow_verified,
        "production_activation_ready": handoff.get("production_activation_ready") is True,
        "handoff_ready_for_operator": handoff.get("handoff_ready_for_operator") is True,
        "ref_collection_state": ref_collection.get("state", ""),
        "handoff_state": handoff.get("state", ""),
        "operator_fill_summary": ref_collection.get("operator_fill_summary", {}),
        "files": {
            name: {
                "path": relative_path(out_dir / name),
                "sha256": file_hash(out_dir / name),
            }
            for name in files
        },
        "side_effects": side_effects_false(),
        "bundle_hash": payload.get("bundle_hash", stable_hash(manifest_seed)),
    }
    write_json(out_dir / "MANIFEST.json", manifest, True)
    return manifest


def default_out_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_ROOT / f"XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_{stamp}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XiaoJ total product operator bundle")
    parser.add_argument("--out-dir", default="", help="Output bundle directory")
    parser.add_argument("--input-refs", default="", help="Optional filled refs JSON to rebuild the bundle")
    parser.add_argument("--allow-verified", action="store_true", help="Preserve verified=true only after human owner/admin review")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON files")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else default_out_dir()
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    input_refs_path = Path(args.input_refs).expanduser() if args.input_refs else None
    if input_refs_path is not None and not input_refs_path.is_absolute():
        input_refs_path = ROOT / input_refs_path
    manifest = build_bundle(out_dir, pretty=args.pretty, input_refs_path=input_refs_path, allow_verified=args.allow_verified)
    summary = {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_CLI_REPORT_V1",
        "state": manifest["state"],
        "bundle_dir": manifest["bundle_dir"],
        "input_refs_path": manifest["input_refs_path"],
        "allow_verified": manifest["allow_verified"],
        "ref_collection_state": manifest["ref_collection_state"],
        "production_activation_ready": manifest["production_activation_ready"],
        "handoff_ready_for_operator": manifest["handoff_ready_for_operator"],
        "needs_human_fill_count": manifest.get("operator_fill_summary", {}).get("needs_human_fill_count", 0),
        "bundle_hash": manifest["bundle_hash"],
        "side_effects": manifest["side_effects"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
