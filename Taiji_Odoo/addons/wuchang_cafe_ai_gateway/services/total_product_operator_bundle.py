"""Total XiaoJ product operator bundle service.

This service builds the same refs-only operator bundle payload used by the
local CLI, but keeps it in memory for Odoo/API use. It performs no file writes,
external API calls, DB writes, message sends, POS writes, payment captures,
secret reads, or member/resident plaintext reads.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .total_product_handoff import build_total_product_operator_handoff
from .total_product_ref_collection import (
    build_total_product_ref_collection_draft,
    build_total_product_ref_collection_input_template,
)


DEFAULT_LINE_OFFICIAL_ACCOUNT_INTENT = (
    "幫我把 LINE 官方帳號設定成咖啡館會員客服模式；新朋友加入先歡迎並詢問是否領用會員小J；"
    "促銷只發給已同意會員；付款、訂單、個資不得由 LLM 自行判定；設定完成後給我核定，不要直接生效。"
)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _reject_unsafe_label(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if (
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)channel_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
    ):
        raise ValueError(f"secret-shaped or plaintext-shaped material is not allowed in total product bundle:{label}")
    return text


def build_total_product_operator_bundle_readme(
    *,
    bundle_name: str,
    ref_collection: dict,
    handoff: dict,
    allow_verified: bool,
    input_ref: str,
) -> str:
    summary = ref_collection.get("operator_fill_summary", {})
    input_note = input_ref or "generated refs-only template"
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


def _handoff_from_ref_collection(ref_collection: dict, *, input_ref: str) -> dict:
    handoff_inputs = ref_collection.get("handoff_inputs", {})
    if not isinstance(handoff_inputs, dict):
        handoff_inputs = {}
    return build_total_product_operator_handoff(
        formal_release_refs=handoff_inputs.get("formal_release_refs", {}),
        lineworks_refs=handoff_inputs.get("lineworks_refs", {}),
        line_official_account_refs=handoff_inputs.get("line_official_account_refs", {}),
        line_official_account_intent=DEFAULT_LINE_OFFICIAL_ACCOUNT_INTENT,
        lineworks_probe={},
        input_ref=input_ref,
    )


def build_total_product_operator_bundle_payload(
    *,
    refs: dict | None = None,
    allow_verified: bool = False,
    input_ref: str = "",
    bundle_ref: str = "",
) -> dict:
    """Build an in-memory total product operator bundle candidate."""

    input_ref = _reject_unsafe_label(input_ref, "input_ref")
    bundle_ref = _reject_unsafe_label(bundle_ref, "bundle_ref")
    refs_input = refs if isinstance(refs, dict) else build_total_product_ref_collection_input_template()
    ref_collection = build_total_product_ref_collection_draft(refs_input, allow_verified=allow_verified)
    handoff = _handoff_from_ref_collection(
        ref_collection,
        input_ref=input_ref or "total_product_operator_bundle_payload",
    )
    bundle_name = bundle_ref.rsplit("/", 1)[-1] if bundle_ref else "XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_API_PAYLOAD"
    readme = build_total_product_operator_bundle_readme(
        bundle_name=bundle_name,
        ref_collection=ref_collection,
        handoff=handoff,
        allow_verified=allow_verified,
        input_ref=input_ref,
    )
    bundle_files = {
        "README.md": {"kind": "text", "content": readme},
        "ref_template.json": {"kind": "json", "content": refs_input},
        "ref_collection.json": {"kind": "json", "content": ref_collection},
        "ref_worksheet.md": {"kind": "text", "content": ref_collection.get("operator_fill_worksheet_md", "")},
        "handoff.json": {"kind": "json", "content": handoff},
    }
    bundle_seed = {
        "ref_collection_hash": ref_collection.get("draft_hash", ""),
        "handoff_hash": handoff.get("handoff_hash", ""),
        "allow_verified": allow_verified,
        "input_ref": input_ref,
        "bundle_ref": bundle_ref,
        "bundle_file_names": sorted(bundle_files),
    }
    return {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_PAYLOAD_V1",
        "state": "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bundle_ref": bundle_ref,
        "input_ref": input_ref,
        "allow_verified": allow_verified,
        "production_activation_ready": handoff.get("production_activation_ready") is True,
        "handoff_ready_for_operator": handoff.get("handoff_ready_for_operator") is True,
        "ref_collection_state": ref_collection.get("state", ""),
        "handoff_state": handoff.get("state", ""),
        "operator_fill_summary": ref_collection.get("operator_fill_summary", {}),
        "bundle_files": bundle_files,
        "side_effects": side_effects_false(),
        "bundle_hash": stable_hash(bundle_seed),
    }
