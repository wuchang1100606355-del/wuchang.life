#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.router.w7tp_causal_event_builder import build_packet


SIGNALS = {
    "causal_chain": r"因果鏈|causal chain|causal ledger",
    "dag": r"\bDAG\b|有向無環圖",
    "partial_order": r"偏序|partial order|happens-before",
    "vector_clock": r"向量時鐘|vector clock",
    "crdt": r"\bCRDT\b|無衝突複製",
    "byzantine_crdt": r"拜占庭|Byzantine",
    "compressed_clock": r"互質|中國剩餘定理|CRT|compressed clock|coprime",
    "narwhal_tusk": r"Narwhal|Tusk|HotStuff",
    "tcg_gnn": r"TCG|GNN|圖神經網路|時空因果圖",
    "redteam": r"紅隊|攻擊向量|double spending|雙重支付|偽造|拓撲欺騙"
}

DANGERS = {
    "double_spend": r"雙重支付|double spending",
    "forged_vector_clock": r"偽造.*向量時鐘|forged vector clock",
    "unsafe_lww": r"最後寫入者勝出|LWW",
    "topology_spoof": r"拓撲欺騙|虛假因果|偽造.*因果",
    "causal_dos": r"資源耗竭|DoS|payload",
    "raw_pii_cloud": r"個資上雲|raw PII"
}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def analyze_text(text: str, source: str) -> Dict[str, Any]:
    signals = {k: bool(re.search(p, text, re.I)) for k, p in SIGNALS.items()}
    dangers = {k: len(re.findall(p, text, re.I)) for k, p in DANGERS.items()}

    summary_parts = [k for k, v in signals.items() if v]
    danger_parts = [k for k, n in dangers.items() if n > 0]

    summary = (
        "Causal ledger source analysis. "
        "Signals=" + ",".join(summary_parts) + ". "
        "Dangers=" + ",".join(danger_parts) + "."
    )

    packet = build_packet(
        event_type="causal_audit",
        source_field="uploaded_text_or_local_file",
        summary=summary,
        parent_event_hashes=[],
        privacy_level="redacted",
        cloud_allowed=False,
        clock_mode="compressed_coprime_clock_plan" if signals.get("compressed_clock") else "vector_clock_redacted",
        crdt_mode="byzantine_aware_plan" if signals.get("byzantine_crdt") else ("state_based_plan" if signals.get("crdt") else "none")
    )

    return {
        "analyzer": "causal_ledger_text_analyzer",
        "source": source,
        "source_hash": sha256_text(text),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "signals": signals,
        "danger_counts": dangers,
        "recommended_layer": "W7TP_CAUSAL_LEDGER_LAYER",
        "recommended_decision": packet["policy"]["decision"],
        "recommended_risk": packet["risk"],
        "packet": packet,
        "script_executed": False,
        "cloud_upload": False,
        "odoo_write": False,
        "financial_settlement": False
    }


def to_markdown(result: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Causal Ledger Text Analysis")
    lines.append("")
    lines.append(f"- Recommended Layer: `{result['recommended_layer']}`")
    lines.append(f"- Decision: `{result['recommended_decision']}`")
    lines.append(f"- Risk: `{result['recommended_risk']['level']}`")
    lines.append(f"- Source Hash: `{result['source_hash']}`")
    lines.append(f"- Cloud Upload: `false`")
    lines.append(f"- Odoo Write: `false`")
    lines.append(f"- Financial Settlement: `false`")
    lines.append("")
    lines.append("## Signals")
    lines.append("")
    for k, v in result["signals"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Danger Counts")
    lines.append("")
    for k, v in result["danger_counts"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Packet")
    lines.append("")
    pkt = result["packet"]
    lines.append(f"- Event ID: `{pkt['event_id']}`")
    lines.append(f"- Event Hash: `{pkt['ledger']['event_hash']}`")
    lines.append(f"- Clock Mode: `{pkt['causal']['clock_mode']}`")
    lines.append(f"- CRDT Mode: `{pkt['causal']['crdt_mode']}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--out-prefix", default=None)
    args = parser.parse_args()

    path = Path(args.file)
    text = path.read_text(encoding="utf-8", errors="replace")
    result = analyze_text(text, str(path))

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = args.out_prefix or f"runtime/reports/causal_ledger_text_analysis_{ts}"
    json_path = Path(prefix + ".json")
    md_path = Path(prefix + ".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(result), encoding="utf-8")

    print(json.dumps({
        "decision": result["recommended_decision"],
        "risk": result["recommended_risk"],
        "json": str(json_path),
        "markdown": str(md_path),
        "event_id": result["packet"]["event_id"],
        "event_hash": result["packet"]["ledger"]["event_hash"]
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
