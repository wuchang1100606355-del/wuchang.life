#!/usr/bin/env python3
"""Classify patent-to-system gaps for intent-field construction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path("/home/taiji_admin/Taiji_Hub")
VALID_CLASSIFICATIONS = {
    "IMPLEMENTED",
    "PARTIAL_IMPLEMENTED",
    "DESIGN_EXISTS",
    "NOT_IMPLEMENTED",
    "UPPER_PROTECTION_ONLY",
    "NEEDS_HUMAN_REVIEW",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_ref(path_value: str, role: str = "repo_evidence", state: str = "REF_ONLY") -> dict[str, str]:
    path = Path(path_value)
    full = path if path.is_absolute() else ROOT / path
    if not full.exists() or not full.is_file():
        return {"path": path_value, "sha256": "0" * 64, "role": role, "state": "MISSING"}
    rel = str(full.relative_to(ROOT)) if full.is_relative_to(ROOT) else str(full)
    return {"path": rel, "sha256": sha256_file(full), "role": role, "state": state}


def risk_for(classification: str) -> str:
    if classification in {"NOT_IMPLEMENTED", "NEEDS_HUMAN_REVIEW"}:
        return "HIGH"
    if classification in {"DESIGN_EXISTS", "UPPER_PROTECTION_ONLY"}:
        return "MEDIUM"
    if classification == "PARTIAL_IMPLEMENTED":
        return "MEDIUM"
    return "LOW"


def module_ref_for(row: dict[str, Any]) -> str:
    text = " ".join(str(row.get(k, "")) for k in ("patent_scope", "gap", "recommendation"))
    if "前緣代理" in text or "API" in text:
        return "front_edge_proxy_layer"
    if "時空" in text or "ADI" in text or "可見資料集合" in text:
        return "spacetime_state_index_database"
    if "封包" in text or "狀態場" in text:
        return "state_field_packet_runtime"
    if "雜湊" in text or "可稽核" in text:
        return "accountable_record_chain"
    if "明文" in text or "遮罩" in text:
        return "isolated_plaintext_archive_boundary"
    if "外部模型" in text or "candidate" in text:
        return "cloud_candidate_boundary"
    return "total_governance_control_plane"


def classify_alignment(alignment_json: Path) -> list[dict[str, Any]]:
    data = json.loads(alignment_json.read_text(encoding="utf-8"))
    rows = data.get("claim_rows", [])
    gaps: list[dict[str, Any]] = []
    for row in rows:
        classification = str(row.get("status", "NEEDS_HUMAN_REVIEW"))
        if classification not in VALID_CLASSIFICATIONS:
            classification = "NEEDS_HUMAN_REVIEW"
        evidence = [file_ref(p) for p in row.get("evidence_paths", [])]
        claim = row.get("claim", "unknown")
        gaps.append(
            {
                "gap_id": f"claim_{claim}",
                "classification": classification,
                "patent_claim_ref": f"Claim {claim}",
                "product_module_ref": module_ref_for(row),
                "repo_evidence_ref": evidence,
                "suggested_next_action": row.get("recommendation") or row.get("gap") or "需人工確認下一步。",
                "risk_level": risk_for(classification),
            }
        )
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify system-patent alignment gaps.")
    parser.add_argument("alignment_json")
    parser.add_argument("--output")
    args = parser.parse_args()

    gaps = classify_alignment(Path(args.alignment_json))
    text = json.dumps(gaps, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
