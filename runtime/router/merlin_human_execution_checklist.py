#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merlin Human Execution Checklist

Reads approved Merlin Approval Gate records and emits manual checklist files.

Safety:
- no router login
- no SSH
- no HTTP router API
- no nvram write
- no reboot
- no firewall change
- no credential storage
- no automatic execution
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


ROOT = Path(__file__).resolve().parents[2]
APPROVAL_DIR = ROOT / "runtime" / "merlin_approval_gate"
OUT_DIR = ROOT / "runtime" / "merlin_human_execution_checklist"


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:120]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def latest_approved() -> Optional[Dict[str, Any]]:
    latest = None
    for obj in iter_jsonl(APPROVAL_DIR / "approved_record_only.jsonl"):
        latest = obj
    return latest


def manual_steps_for_intent(intent: str, source_steps: list[str]) -> list[str]:
    common_pre = [
        "確認目前在梅林路由器管理介面內，且操作者為本人或被明確授權者。",
        "確認這是人工承接，不是自動化執行。",
        "不要輸入或保存路由器密碼、API key、token、private key 到 repo、LLM 或 log。",
        "操作前拍照或截圖保存目前設定狀態。",
    ]

    common_post = [
        "操作後不要立即清除紀錄。",
        "若涉及網路中斷風險，先確認可回退路徑。",
        "將實際操作結果手動寫入人工紀錄，不讓程式自動套用。",
    ]

    if intent == "ssh_hardening_plan":
        middle = [
            "前往 系統管理 / System Administration。",
            "檢查 SSH 啟用狀態。",
            "優先將 SSH 管理限制為 LAN 或 VPN 管理，不建議開放 WAN。",
            "確認 SSH Port Forwarding 不對外暴露。",
            "若要變更 SSH 設定，先確認仍保留 Web UI 或本地管理回退通道。",
            "任何變更前先人工確認：不會造成自己被鎖在路由器外。",
        ]
    elif intent == "qos_xiaoj_priority_plan":
        middle = [
            "前往 Adaptive QoS / 智慧流量管理。",
            "確認小J、Gateway、Odoo、Open WebUI、VPN 所在設備與 IP。",
            "只規劃優先權，不降低緊急通訊、一般上網與社區服務可用性。",
            "若需套用 QoS，先以低影響設定開始，觀察再調整。",
        ]
    elif intent == "guest_network_design_plan":
        middle = [
            "前往 Guest Network / 訪客網路。",
            "規劃訪客、會員、商家設備、IoT 設備分區。",
            "不要把 WiFi 連線視為會員身分認證。",
            "會員服務仍需登入、VPN 或其他授權機制。",
        ]
    elif intent == "vpn_member_access_plan":
        middle = [
            "前往 VPN 設定頁。",
            "確認 VPN 只作為受控入口，不直接暴露 MSI 核心服務。",
            "確認外網入口優先經 taiji01 或 VPN 邊界，再進 W7TP Gateway。",
            "不要把 raw PII 或核心記憶場暴露給外網節點。",
        ]
    else:
        middle = source_steps or [
            "此 intent 沒有專用操作清單。",
            "僅依原始操作單內容人工審查。",
            "不得自動套用。"
        ]

    return common_pre + middle + common_post


def build_checklist(record: Dict[str, Any]) -> Dict[str, Any]:
    ticket = record.get("ticket", {})
    source_plan = ticket.get("source_plan", {})
    intent = ticket.get("intent") or source_plan.get("intent") or "unknown"
    ticket_id = ticket.get("ticket_id")
    approval_hash = record.get("approval_record_hash")
    ticket_hash = ticket.get("ticket_hash")

    if record.get("decision") != "approved_record_only" or not record.get("approved"):
        status = "not_approved_no_checklist"
    elif ticket.get("ticket_status") == "rejected_dead_letter":
        status = "dead_letter_no_checklist"
    else:
        status = "manual_checklist_ready"

    source_steps = ticket.get("manual_review_steps") or source_plan.get("steps") or []
    steps = manual_steps_for_intent(intent, source_steps)

    checklist = {
        "generator": "merlin_human_execution_checklist",
        "mode": "manual_checklist_only",
        "created_at": utc_now(),
        "status": status,
        "intent": intent,
        "ticket_id": ticket_id,
        "ticket_hash": ticket_hash,
        "approval_record_hash": approval_hash,
        "auto_execute": False,
        "executable": False,
        "manual_steps": steps,
        "safety": {
            "no_router_login": True,
            "no_ssh": True,
            "no_http_router_api": True,
            "no_nvram_write": True,
            "no_reboot": True,
            "no_firewall_change": True,
            "no_credential_storage": True,
            "manual_only": True
        },
        "source_approval_record": record
    }
    checklist["checklist_hash"] = sha256_obj(checklist)
    return checklist


def to_markdown(checklist: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Merlin Human Execution Checklist")
    lines.append("")
    lines.append(f"- Status: `{checklist['status']}`")
    lines.append(f"- Intent: `{checklist['intent']}`")
    lines.append(f"- Ticket ID: `{checklist.get('ticket_id')}`")
    lines.append(f"- Ticket Hash: `{checklist.get('ticket_hash')}`")
    lines.append(f"- Approval Record Hash: `{checklist.get('approval_record_hash')}`")
    lines.append(f"- Checklist Hash: `{checklist.get('checklist_hash')}`")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No router login by this script")
    lines.append("- No SSH by this script")
    lines.append("- No HTTP admin API call")
    lines.append("- No nvram write")
    lines.append("- No reboot")
    lines.append("- No firewall change")
    lines.append("- No credential storage")
    lines.append("- Manual checklist only")
    lines.append("")
    lines.append("## Manual Steps")
    lines.append("")
    for i, step in enumerate(checklist["manual_steps"], 1):
        lines.append(f"- [ ] {i}. {step}")
    lines.append("")
    lines.append("## Operator Notes")
    lines.append("")
    lines.append("- 操作前後請人工截圖保存。")
    lines.append("- 若設定有中斷風險，先確認回退方式。")
    lines.append("- 若不確定，不執行。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-approved", action="store_true")
    parser.add_argument("--approval-json", default=None)
    args = parser.parse_args()

    if args.approval_json:
        record = json.load(open(args.approval_json, "r", encoding="utf-8"))
    else:
        record = latest_approved()

    if not record:
        print(json.dumps({
            "status": "no_approved_record_found",
            "message": "No approved_record_only entry found.",
            "auto_execute": False,
            "executable": False
        }, ensure_ascii=False, indent=2))
        return 1

    checklist = build_checklist(record)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = f"{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name(checklist['intent'])}_{safe_name(str(checklist.get('ticket_id')))}"
    json_path = OUT_DIR / f"{base}.json"
    md_path = OUT_DIR / f"{base}.md"

    json_path.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(checklist)
    md_path.write_text(md, encoding="utf-8")

    print(json.dumps({
        "status": checklist["status"],
        "intent": checklist["intent"],
        "ticket_id": checklist.get("ticket_id"),
        "checklist_hash": checklist["checklist_hash"],
        "json": str(json_path),
        "markdown": str(md_path),
        "auto_execute": False,
        "executable": False
    }, ensure_ascii=False, indent=2))
    return 0 if checklist["status"] == "manual_checklist_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
