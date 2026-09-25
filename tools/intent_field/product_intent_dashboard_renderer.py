#!/usr/bin/env python3
"""Render product intent dry-run data into static HTML reports."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any


SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(api[_-]?key|secret|token|password|db_password)\s*[:=]\s*['\"][^'\"]{8,}",
    re.IGNORECASE,
)
MEMBER_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render static product intent dry-run dashboard.")
    parser.add_argument("--p0", required=True, help="P0 output directory.")
    parser.add_argument("--p1", required=True, help="P1 output directory.")
    parser.add_argument("--out", required=True, help="P2 output directory.")
    parser.add_argument("--dry-run", action="store_true", required=True, help="Required dry-run switch.")
    return parser.parse_args()


def utc_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if SECRET_PATTERN.search(text) or MEMBER_ID_PATTERN.search(text):
        return "[redacted_ref_only]"
    return text


def e(value: Any) -> str:
    return html.escape(safe_text(value), quote=True)


def badge(value: str) -> str:
    css = "pass" if value == "PASS" else "hold" if value == "HOLD" else "neutral"
    return f'<span class="badge {css}">{e(value)}</span>'


def row(label: str, value: Any) -> str:
    return f"<tr><th>{e(label)}</th><td>{e(value)}</td></tr>"


def rows(items: list[tuple[str, Any]]) -> str:
    return "\n".join(row(label, value) for label, value in items)


def case_summary(case: dict[str, Any]) -> dict[str, Any]:
    request = case.get("request", {})
    packet = case.get("state_packet", {})
    output = case.get("dry_run_output", {})
    record = case.get("accountability_record", {})
    return {
        "intent_text_preview": safe_text(request.get("raw_intent_text", "")),
        "intent_text_ref": request.get("intent_text_ref", ""),
        "intent_request_id": packet.get("intent_request_id", ""),
        "candidate_action_id": packet.get("candidate_action_id", ""),
        "state_packet_id": packet.get("state_packet_id", ""),
        "spacetime_index_ref": packet.get("spacetime_index_ref", ""),
        "identity_proxy_ref": packet.get("identity_proxy_ref", ""),
        "authority_scope_code": packet.get("authority_scope_code", ""),
        "consent_state_code": packet.get("consent_state_code", ""),
        "verifier_result": case.get("verifier_result", {}).get("result", ""),
        "hold_reason_code": case.get("verifier_result", {}).get("hold_reason_code", ""),
        "front_edge_proxy": output.get("front_edge_proxy", ""),
        "restricted_execution_instruction_ref": output.get("restricted_execution_instruction_ref", ""),
        "hold_packet_ref": output.get("hold_packet_ref", ""),
        "accountability_record": {
            "candidate_action_id": record.get("candidate_action_id", ""),
            "state_packet_id": record.get("state_packet_id", ""),
            "previous_record_hash": record.get("previous_record_hash", ""),
            "current_record_hash": record.get("current_record_hash", ""),
            "verifier_result": record.get("verifier_result", ""),
            "execution_result": record.get("execution_result", ""),
        },
        "db_write": False,
        "deploy": False,
        "restart": False,
    }


def build_dashboard_data(p0_dir: Path, p1_dir: Path) -> dict[str, Any]:
    pass_case = load_json(p0_dir / "pass_case.json")
    hold_case = load_json(p0_dir / "hold_case.json")
    dashboard_state = load_json(p1_dir / "dashboard_state.json")
    pass_summary = case_summary(pass_case)
    hold_summary = case_summary(hold_case)
    packet = pass_case["state_packet"]

    return {
        "run_id": "PRODUCT_INTENT_STATIC_DASHBOARD_" + utc_stamp(),
        "source_p0": str(p0_dir),
        "source_p1": str(p1_dir),
        "intent_input": {
            "intent_text_preview": pass_summary["intent_text_preview"],
            "intent_text_ref": pass_summary["intent_text_ref"],
        },
        "intent_request_id": dashboard_state["intent_request_id"],
        "candidate_action_id": dashboard_state["candidate_action_id"],
        "state_packet_id": dashboard_state["state_packet_id"],
        "multi_state_field_status": dashboard_state["multi_state_field_status"],
        "spacetime_index_ref_status": dashboard_state["spacetime_index_ref_status"],
        "sovereign_identity_proxy_status": dashboard_state["sovereign_identity_proxy_status"],
        "plaintext_archive_boundary_status": dashboard_state["plaintext_archive_boundary_status"],
        "front_proxy_status": dashboard_state["front_proxy_status"],
        "verifier_result": dashboard_state["verifier_result"],
        "hold_reason_code": dashboard_state["hold_reason_code"],
        "redteam_reason": dashboard_state["redteam_reason"],
        "accountability_chain_summary": dashboard_state["accountability_chain_summary"],
        "cpu_only_no_gpu_evidence_status": dashboard_state["cpu_only_no_gpu_evidence_status"],
        "state_packet_summary": {
            "multi_state_field_codes": packet.get("multi_state_field_codes", []),
            "state_field_relation_table": packet.get("state_field_relation_table", []),
            "spacetime_index_ref": packet.get("spacetime_index_ref", ""),
            "identity_proxy_ref": packet.get("identity_proxy_ref", ""),
            "authority_scope_code": packet.get("authority_scope_code", ""),
            "consent_state_code": packet.get("consent_state_code", ""),
            "mask_code": packet.get("mask_code", ""),
            "permission_code": packet.get("permission_code", ""),
            "state_code": packet.get("state_code", ""),
            "risk_code": packet.get("risk_code", ""),
        },
        "pass_case": pass_summary,
        "hold_case": hold_summary,
        "db_write": False,
        "deploy": False,
        "restart": False,
    }


STYLE = """
body {
  margin: 0;
  font-family: Arial, "Noto Sans TC", sans-serif;
  color: #1f2933;
  background: #f6f7f4;
}
.shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 18px 40px;
}
header {
  border-bottom: 1px solid #d8ddd3;
  padding-bottom: 18px;
  margin-bottom: 18px;
}
h1 {
  font-size: 28px;
  line-height: 1.2;
  margin: 0 0 8px;
  letter-spacing: 0;
}
h2 {
  font-size: 18px;
  margin: 0 0 12px;
  letter-spacing: 0;
}
.subtle {
  color: #5d6a61;
  line-height: 1.55;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}
.panel {
  background: #ffffff;
  border: 1px solid #dfe4dc;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(20, 31, 25, 0.05);
}
.wide {
  grid-column: 1 / -1;
}
.badge {
  display: inline-block;
  min-width: 58px;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}
.pass {
  color: #14532d;
  background: #dcfce7;
  border: 1px solid #86efac;
}
.hold {
  color: #7c2d12;
  background: #ffedd5;
  border: 1px solid #fdba74;
}
.neutral {
  color: #334155;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
}
table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
th, td {
  padding: 8px 0;
  border-bottom: 1px solid #eef1ec;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
th {
  width: 34%;
  color: #56635a;
  font-weight: 700;
}
.mono {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;
}
.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}
"""


def html_doc(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="shell">
    {body}
  </main>
</body>
</html>
"""


def render_dashboard(data: dict[str, Any]) -> str:
    packet = data["state_packet_summary"]
    account = data["accountability_chain_summary"]
    status_items = [
        ("多狀態場", data["multi_state_field_status"]),
        ("ADI ref", data["spacetime_index_ref_status"]),
        ("主權身分代理", data["sovereign_identity_proxy_status"]),
        ("明文封存邊界", data["plaintext_archive_boundary_status"]),
        ("前緣代理層", data["front_proxy_status"]),
        ("CPU-only/no-GPU", data["cpu_only_no_gpu_evidence_status"]),
    ]
    status_html = "\n".join(f"<div>{e(label)} {badge(value)}</div>" for label, value in status_items)
    relation_json = json.dumps(packet["state_field_relation_table"], ensure_ascii=False, indent=2)
    body = f"""
<header>
  <h1>產品意圖場 Dry-Run Dashboard</h1>
  <div class="subtle">STATIC_UI_ONLY=true · DB_WRITE=false · DEPLOY=false · RESTART=false</div>
</header>
<section class="grid">
  <div class="panel wide">
    <h2>總覽</h2>
    <div class="status-row">{status_html}</div>
  </div>
  <div class="panel">
    <h2>意圖與候選</h2>
    <table>{rows([
      ("intent", data["intent_input"]["intent_text_preview"]),
      ("intent_request_id", data["intent_request_id"]),
      ("candidate_action_id", data["candidate_action_id"]),
      ("state_packet_id", data["state_packet_id"]),
    ])}</table>
  </div>
  <div class="panel">
    <h2>Verifier</h2>
    <table>{rows([
      ("verifier_result", data["verifier_result"]),
      ("hold_reason_code", data["hold_reason_code"]),
      ("risk_code", packet["risk_code"]),
      ("state_code", packet["state_code"]),
    ])}</table>
  </div>
  <div class="panel">
    <h2>Ref Boundary</h2>
    <table>{rows([
      ("spacetime_index_ref", packet["spacetime_index_ref"]),
      ("identity_proxy_ref", packet["identity_proxy_ref"]),
      ("authority_scope_code", packet["authority_scope_code"]),
      ("consent_state_code", packet["consent_state_code"]),
      ("mask_code", packet["mask_code"]),
    ])}</table>
  </div>
  <div class="panel">
    <h2>可究責紀錄鏈</h2>
    <table>{rows([
      ("candidate_action_id", account["candidate_action_id"]),
      ("state_packet_id", account["state_packet_id"]),
      ("previous_record_hash", account["previous_record_hash"]),
      ("current_record_hash", account["current_record_hash"]),
      ("verifier_result", account["verifier_result"]),
    ])}</table>
  </div>
  <div class="panel wide">
    <h2>狀態場關係表</h2>
    <pre class="mono">{e(relation_json)}</pre>
  </div>
</section>
"""
    return html_doc("Product Intent Dry-Run Dashboard", body)


def render_case_report(title: str, case: dict[str, Any]) -> str:
    record = case["accountability_record"]
    body = f"""
<header>
  <h1>{e(title)}</h1>
  <div class="subtle">dry-run report · DB_WRITE=false · DEPLOY=false · RESTART=false</div>
</header>
<section class="grid">
  <div class="panel">
    <h2>Case</h2>
    <table>{rows([
      ("intent", case["intent_text_preview"]),
      ("intent_request_id", case["intent_request_id"]),
      ("candidate_action_id", case["candidate_action_id"]),
      ("state_packet_id", case["state_packet_id"]),
    ])}</table>
  </div>
  <div class="panel">
    <h2>Decision</h2>
    <table>{rows([
      ("verifier_result", case["verifier_result"]),
      ("hold_reason_code", case["hold_reason_code"]),
      ("front_edge_proxy", case["front_edge_proxy"]),
      ("restricted_execution_instruction_ref", case["restricted_execution_instruction_ref"]),
      ("hold_packet_ref", case["hold_packet_ref"]),
    ])}</table>
  </div>
  <div class="panel wide">
    <h2>Accountability</h2>
    <table>{rows([
      ("candidate_action_id", record["candidate_action_id"]),
      ("state_packet_id", record["state_packet_id"]),
      ("previous_record_hash", record["previous_record_hash"]),
      ("current_record_hash", record["current_record_hash"]),
      ("execution_result", record["execution_result"]),
    ])}</table>
  </div>
</section>
"""
    return html_doc(title, body)


def render_redteam(data: dict[str, Any]) -> str:
    reasons = data.get("redteam_reason", [])
    items = "".join(f"<tr><td>{e(reason)}</td><td>{badge('HOLD')}</td></tr>" for reason in reasons)
    if not items:
        items = "<tr><td>none</td><td>" + badge("PASS") + "</td></tr>"
    body = f"""
<header>
  <h1>Redteam HOLD Summary</h1>
  <div class="subtle">HOLD reason display only; no executable action is produced.</div>
</header>
<section class="panel">
  <table><tr><th>reason</th><th>status</th></tr>{items}</table>
</section>
"""
    return html_doc("Redteam Summary", body)


def render_accountability(data: dict[str, Any]) -> str:
    account = data["accountability_chain_summary"]
    body = f"""
<header>
  <h1>Accountability Chain Summary</h1>
  <div class="subtle">hash-chain summary for dry-run evidence only.</div>
</header>
<section class="panel">
  <table>{rows([
    ("candidate_action_id", account["candidate_action_id"]),
    ("state_packet_id", account["state_packet_id"]),
    ("previous_record_hash", account["previous_record_hash"]),
    ("current_record_hash", account["current_record_hash"]),
    ("verifier_result", account["verifier_result"]),
  ])}</table>
</section>
"""
    return html_doc("Accountability Summary", body)


def write_outputs(data: dict[str, Any], out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "dashboard_data.json": json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        "dashboard.html": render_dashboard(data),
        "pass_case_report.html": render_case_report("PASS Case Report", data["pass_case"]),
        "hold_case_report.html": render_case_report("HOLD Case Report", data["hold_case"]),
        "redteam_summary.html": render_redteam(data),
        "accountability_summary.html": render_accountability(data),
    }
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    return sorted(files)


def main() -> int:
    args = parse_args()
    data = build_dashboard_data(Path(args.p0), Path(args.p1))
    files = write_outputs(data, Path(args.out))
    summary = {
        "state": "PRODUCT_INTENT_FIELD_DRY_RUN_P2_RENDER",
        "run_id": data["run_id"],
        "out": args.out,
        "files": files,
        "static_ui_only": True,
        "db_write": False,
        "deploy": False,
        "restart": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
