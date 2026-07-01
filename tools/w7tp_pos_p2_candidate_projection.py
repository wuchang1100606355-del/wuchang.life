#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path("/home/taiji_admin/Taiji_Hub")
DEFAULT_SEARCH_ROOT = ROOT / "runtime/sandbox/pos_mvp_autodev_run"
DEFAULT_RUN_DIR = ROOT / "runtime/sandbox/pos_mvp_autodev_run/POS_MVP_P2_CANDIDATE_READER"
TOTAL_FIELD_EVIDENCE_ROOT = ROOT / "runtime/total_field/evidence"
TOTAL_FIELD_INDEX = TOTAL_FIELD_EVIDENCE_ROOT / "POS_MVP_P2_CANDIDATE_READER_INDEX.jsonl"

REQUIRED_FALSE_FLAGS = {
    "formal_db_write": False,
    "formal_pos_write": False,
    "payment_capture": False,
    "service_restart": False,
    "deploy": False,
    "production_release": False,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha_obj(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_latest_candidate(search_root: Path) -> Path:
    candidates = [
        path
        for path in search_root.glob("*/orders/POS_SANDBOX_ORDER_CANDIDATE.json")
        if path.is_file()
    ]
    if not candidates:
        raise SystemExit(f"no POS_SANDBOX_ORDER_CANDIDATE.json under {search_root}")
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, str(path)))


def validate_candidate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, expected in REQUIRED_FALSE_FLAGS.items():
        if candidate.get(key) is not expected:
            errors.append(f"{key.upper()}_NOT_FALSE")
    for key in ["items", "subtotal", "payable_amount", "voice_reply", "rule_refs", "d8_ref"]:
        if key not in candidate:
            errors.append(f"{key.upper()}_MISSING")
    if not isinstance(candidate.get("items"), list) or not candidate.get("items"):
        errors.append("ITEMS_EMPTY")
    if not isinstance(candidate.get("rule_refs"), list) or not candidate.get("rule_refs"):
        errors.append("RULE_REFS_EMPTY")
    return errors


def build_projection(candidate_path: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    discount = candidate.get("selected_discount", candidate.get("discount", 0))
    projection = {
        "schema": "W7TP_POS_P2_UI_PROJECTION_V1",
        "state": "POS_P2_UI_PROJECTION",
        "created_at": now_iso(),
        "source_candidate_path": str(candidate_path.relative_to(ROOT)),
        "source_candidate_hash": sha_obj(candidate),
        "product_name": candidate.get("product_name"),
        "items": candidate.get("items", []),
        "subtotal": candidate.get("subtotal"),
        "discount": discount,
        "payable_amount": candidate.get("payable_amount"),
        "voice_reply": candidate.get("voice_reply"),
        "rule_refs": candidate.get("rule_refs", []),
        "d8_ref": candidate.get("d8_ref"),
        "formal_db_write": False,
        "formal_pos_write": False,
        "payment_capture": False,
        "service_restart": False,
        "deploy": False,
        "production_release": False,
    }
    projection["projection_hash"] = sha_obj(projection)
    return projection


def build_confirm_dry_run(projection: dict[str, Any]) -> dict[str, Any]:
    confirm = {
        "schema": "W7TP_POS_P2_HUMAN_CONFIRM_GATE_V1",
        "state": "CONFIRM_DRY_RUN",
        "created_at": now_iso(),
        "source_projection_hash": projection["projection_hash"],
        "source_candidate_hash": projection["source_candidate_hash"],
        "human_required": True,
        "human_confirm_gate": "DRY_RUN_ONLY",
        "formal_db_write": False,
        "formal_pos_write": False,
        "payment_capture": False,
        "service_restart": False,
        "deploy": False,
        "production_release": False,
        "next_allowed_action": "HOLD_FOR_HUMAN_REVIEW",
    }
    confirm["confirm_hash"] = sha_obj(confirm)
    return confirm


def render_projection_html(projection: dict[str, Any], confirm: dict[str, Any]) -> str:
    item_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('sku', '')))}</td>"
        f"<td>{escape(str(item.get('name', '')))}</td>"
        f"<td>{escape(str(item.get('qty', '')))}</td>"
        f"<td>{escape(str(item.get('unit_price', '')))}</td>"
        f"<td>{escape(str(item.get('line_total', '')))}</td>"
        f"<td>{escape(str(item.get('class', '')))}</td>"
        "</tr>"
        for item in projection["items"]
    )
    rules = "".join(f"<li>{escape(str(rule))}</li>" for rule in projection["rule_refs"])
    return f"""<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>W7TP POS P2 Candidate Projection</title>
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: #11181d; color: #f7f2e8; }}
  main {{ max-width: 1120px; margin: 0 auto; padding: 24px; }}
  header, section {{ border: 1px solid #33424a; border-radius: 8px; padding: 16px; margin-bottom: 14px; background: #182229; }}
  h1, h2 {{ margin: 0 0 12px; letter-spacing: 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ border-bottom: 1px solid #33424a; padding: 8px; text-align: left; }}
  .amounts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
  .box {{ border: 1px solid #3a4b54; border-radius: 8px; padding: 12px; }}
  .ok {{ color: #82d89a; font-weight: 700; }}
  .hold {{ color: #f2c45d; font-weight: 700; }}
</style>
<main data-state="POS_P2_UI_PROJECTION" data-confirm-state="{escape(confirm['state'])}">
  <header>
    <h1>W7TP POS P2 Candidate Projection</h1>
    <p class="ok">FORMAL_DB_WRITE=false FORMAL_POS_WRITE=false PAYMENT_CAPTURE=false</p>
    <p class="hold">Human confirm gate: {escape(confirm['state'])}</p>
  </header>
  <section>
    <h2>items / {escape(str(projection.get('product_name')))}</h2>
    <table>
      <thead><tr><th>sku</th><th>item</th><th>qty</th><th>unit</th><th>line</th><th>class</th></tr></thead>
      <tbody>{item_rows}</tbody>
    </table>
  </section>
  <section class="amounts">
    <div class="box">subtotal<br><strong>{escape(str(projection['subtotal']))}</strong></div>
    <div class="box">discount<br><strong>{escape(str(projection['discount']))}</strong></div>
    <div class="box">payable_amount<br><strong>{escape(str(projection['payable_amount']))}</strong></div>
  </section>
  <section>
    <h2>voice_reply</h2>
    <p>{escape(str(projection.get('voice_reply')))}</p>
  </section>
  <section>
    <h2>rule_refs</h2>
    <ul>{rules}</ul>
    <p>d8_ref: {escape(str(projection.get('d8_ref')))}</p>
  </section>
</main>
</html>
"""


def write_outputs(run_dir: Path, projection: dict[str, Any], confirm: dict[str, Any], html: str) -> dict[str, str]:
    paths = {
        "projection_json": run_dir / "projection/POS_P2_UI_PROJECTION.json",
        "confirm_json": run_dir / "confirm/POS_P2_CONFIRM_DRY_RUN.json",
        "projection_html": run_dir / "ui/pos_p2_candidate_projection.html",
        "evidence_json": run_dir / "evidence/POS_P2_CANDIDATE_READER_EVIDENCE.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["projection_json"].write_text(json.dumps(projection, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["confirm_json"].write_text(json.dumps(confirm, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["projection_html"].write_text(html, encoding="utf-8")
    evidence = {
        "schema": "W7TP_POS_P2_EVIDENCE_SEAL_V1",
        "state": "PASS_POS_P2_CANDIDATE_READER",
        "created_at": now_iso(),
        "projection_hash": projection["projection_hash"],
        "confirm_hash": confirm["confirm_hash"],
        "changed_runtime_only": True,
        "safety": {key: False for key in REQUIRED_FALSE_FLAGS},
    }
    evidence["evidence_hash"] = sha_obj(evidence)
    paths["evidence_json"].write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return {key: str(path.relative_to(ROOT)) for key, path in paths.items()}


def write_total_field_evidence(result: dict[str, Any], projection: dict[str, Any], confirm: dict[str, Any]) -> dict[str, str]:
    seal_dir = TOTAL_FIELD_EVIDENCE_ROOT / "TOTAL_FIELD_SEAL_POS_MVP_P2_CANDIDATE_READER"
    seal_dir.mkdir(parents=True, exist_ok=True)
    seal = {
        "schema": "W7TP_TOTAL_FIELD_POS_MVP_P2_CANDIDATE_READER_SEAL_V1",
        "state": "PASS_POS_P2_CANDIDATE_READER",
        "created_at": now_iso(),
        "candidate_path": result["candidate_path"],
        "projection_hash": projection["projection_hash"],
        "confirm_hash": confirm["confirm_hash"],
        "payable_amount": projection["payable_amount"],
        "human_confirm_gate": "CONFIRM_DRY_RUN",
        "runtime_output_root": "runtime/sandbox/pos_mvp_autodev_run",
        "formal_db_write": False,
        "formal_pos_write": False,
        "payment_capture": False,
        "service_restart": False,
        "deploy": False,
        "production_release": False,
        "secret_read": False,
        "member_plaintext_read": False,
    }
    seal["seal_hash"] = sha_obj(seal)
    seal_path = seal_dir / "TOTAL_FIELD_POS_MVP_P2_CANDIDATE_READER_SEAL.json"
    seal_path.write_text(json.dumps(seal, ensure_ascii=False, indent=2), encoding="utf-8")
    index_row = {
        "created_at": seal["created_at"],
        "state": seal["state"],
        "seal_hash": seal["seal_hash"],
        "seal_path": str(seal_path.relative_to(ROOT)),
        "candidate_path": result["candidate_path"],
        "payable_amount": projection["payable_amount"],
        "human_confirm_gate": "CONFIRM_DRY_RUN",
    }
    TOTAL_FIELD_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with TOTAL_FIELD_INDEX.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_row, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "total_field_seal": str(seal_path.relative_to(ROOT)),
        "total_field_index": str(TOTAL_FIELD_INDEX.relative_to(ROOT)),
    }


def run(search_root: Path, run_dir: Path) -> dict[str, Any]:
    candidate_path = find_latest_candidate(search_root)
    candidate = load_json(candidate_path)
    errors = validate_candidate(candidate)
    if errors:
        raise SystemExit("candidate validation failed: " + ",".join(errors))
    projection = build_projection(candidate_path, candidate)
    confirm = build_confirm_dry_run(projection)
    html = render_projection_html(projection, confirm)
    outputs = write_outputs(run_dir, projection, confirm, html)
    result = {
        "state": "PASS_POS_P2_CANDIDATE_READER",
        "candidate_path": str(candidate_path.relative_to(ROOT)),
        "outputs": outputs,
        "safety": {key: False for key in REQUIRED_FALSE_FLAGS},
    }
    result["outputs"].update(write_total_field_evidence(result, projection, confirm))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--search-root", default=os.environ.get("POS_P2_SEARCH_ROOT", str(DEFAULT_SEARCH_ROOT)))
    parser.add_argument("--run-dir", default=os.environ.get("POS_P2_RUN_DIR", str(DEFAULT_RUN_DIR)))
    args = parser.parse_args()
    result = run(Path(args.search_root), Path(args.run_dir))
    print("STATE=" + result["state"])
    print("CANDIDATE=" + result["candidate_path"])
    for key, path in result["outputs"].items():
        print(f"{key.upper()}={path}")
    print("CONFIRM_STATE=CONFIRM_DRY_RUN")
    print("FORMAL_DB_WRITE=false")
    print("FORMAL_POS_WRITE=false")
    print("PAYMENT_CAPTURE=false")
    print("SERVICE_RESTART=false")
    print("DEPLOY=false")
    print("PRODUCTION_RELEASE=false")
    for key in ["total_field_seal", "total_field_index"]:
        print(f"{key.upper()}={result['outputs'][key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
