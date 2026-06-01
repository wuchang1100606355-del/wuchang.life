#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Any


PATTERNS = {
    "cloud_nodes": r"CLOUD_VMS|雲端",
    "hybrid_nodes": r"HYBRID_VMS|區網|暗網|Tailscale|IPv6|IPv4",
    "hot_memory": r"RAM_CORE|tmpfs|RAM Disk|記憶體摺疊",
    "warm_state": r"HOT_DISK|data_core",
    "sync": r"rsync|delta_sync|同步",
    "merlin": r"MERLIN|iptables|firewall-start|梅林|QoS|TOS",
    "schedule": r"crontab|cron|每 15 分鐘",
}

DANGERS = {
    "sudo": r"\bsudo\b",
    "fstab_write": r"/etc/fstab|tee -a /etc/fstab",
    "mount_tmpfs": r"mount\s+-t\s+tmpfs",
    "ssh_copy_id": r"ssh-copy-id",
    "root_ssh": r"root@",
    "strict_hostkey_disabled": r"StrictHostKeyChecking=no",
    "rsync_delete": r"rsync .*--delete|rsync .* -.*delete",
    "crontab_write": r"crontab\s+-|crontab\s+",
    "iptables_apply": r"\biptables\b",
    "chmod_exec": r"chmod\s+\+x",
    "private_key_generation": r"ssh-keygen",
}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_arrays(text: str) -> Dict[str, List[str]]:
    found = {}
    for name in ["CLOUD_VMS", "HYBRID_VMS"]:
        m = re.search(rf"declare\s+-a\s+{name}=\((.*?)\)", text, re.S)
        if not m:
            m = re.search(rf"{name}=\((.*?)\)", text, re.S)
        if m:
            items = []
            for line in m.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                q = re.search(r'"([^"]+)"', line)
                if q:
                    val = q.group(1)
                    # redact exact addresses but preserve path type
                    if "|" in val:
                        items.append("HYBRID_NODE_REDACTED|FALLBACK_REDACTED")
                    else:
                        items.append("CLOUD_NODE_REDACTED")
            found[name] = items
    return found


def classify(text: str) -> Dict[str, Any]:
    signals = {}
    for k, pat in PATTERNS.items():
        signals[k] = bool(re.search(pat, text, re.I))

    dangers = {}
    for k, pat in DANGERS.items():
        hits = re.findall(pat, text, re.I)
        dangers[k] = len(hits)

    dead = [k for k, n in dangers.items() if n > 0 and k in {
        "ssh_copy_id",
        "root_ssh",
        "strict_hostkey_disabled",
        "rsync_delete",
        "crontab_write",
        "fstab_write",
        "iptables_apply"
    }]

    pending = [k for k, v in signals.items() if v]

    decision = "pending_review"
    if dead:
        decision = "dead_letter_for_direct_execution"

    return {
        "decision": decision,
        "architecture_signals": signals,
        "dangerous_commands": dangers,
        "dead_letter_reasons": dead,
        "pending_review_topics": pending,
    }


def to_markdown(result: Dict[str, Any]) -> str:
    lines = []
    lines.append("# HA Mesh Legacy Script Analysis")
    lines.append("")
    lines.append(f"- Decision: `{result['decision']}`")
    lines.append(f"- File: `{result['file']}`")
    lines.append(f"- File Hash: `{result['file_hash']}`")
    lines.append(f"- Script Executed: `false`")
    lines.append("")
    lines.append("## Useful Architecture Signals")
    lines.append("")
    for k, v in result["architecture_signals"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Dangerous Direct Commands")
    lines.append("")
    for k, v in result["dangerous_commands"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Dead-letter If Directly Executed")
    lines.append("")
    for r in result["dead_letter_reasons"]:
        lines.append(f"- {r}")
    if not result["dead_letter_reasons"]:
        lines.append("- none")
    lines.append("")
    lines.append("## W7TP Conversion")
    lines.append("")
    lines.append("- Convert LAN-first / IPv6 fallback to redacted node inventory.")
    lines.append("- Convert RAM/disk idea to hot/warm memory fields.")
    lines.append("- Convert rsync to job manifest + human-reviewed sync.")
    lines.append("- Convert Merlin firewall/QoS to Merlin Intent Driver plan-only ticket.")
    lines.append("- Do not execute sudo, SSH, rsync, crontab, fstab, iptables.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out-prefix", default=None)
    args = parser.parse_args()

    path = Path(args.file)
    text = read_text(path)

    result = classify(text)
    result.update({
        "analyzer": "ha_mesh_script_analyzer",
        "mode": "dry_run_analyzer_only",
        "file": str(path),
        "file_hash": sha256_text(text),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "arrays_redacted": extract_arrays(text),
        "script_executed": False,
        "ssh_executed": False,
        "sudo_executed": False,
        "router_modified": False,
        "credentials_printed": False
    })

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = args.out_prefix or f"runtime/reports/ha_mesh_script_analysis_{ts}"
    json_path = Path(prefix + ".json")
    md_path = Path(prefix + ".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(result), encoding="utf-8")

    print(json.dumps({
        "decision": result["decision"],
        "dead_letter_reasons": result["dead_letter_reasons"],
        "pending_review_topics": result["pending_review_topics"],
        "json": str(json_path),
        "markdown": str(md_path),
        "script_executed": False
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
