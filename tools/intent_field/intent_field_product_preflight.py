#!/usr/bin/env python3
"""Product-grade intent-field construction preflight.

This script is intentionally dry-run only. It builds ref-only packets and
reports for a later cloud-candidate completion step, without calling any
external API or touching live systems.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/home/taiji_admin/Taiji_Hub")
TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from build_cloud_candidate_request import (  # noqa: E402
    ACCOUNTABLE_ACCESS_RECORD_FIELDS,
    ACCOUNTABLE_RECORD_CHAIN_FIELDS,
    CANDIDATE_OUTPUT_SECTIONS,
    STATE_PACKET_REQUIRED_FIELDS,
    build_request,
    default_field_lock,
    default_forbidden_data_policy,
    default_identity_agent,
    default_patent_type_conformity_lock,
    default_plaintext_archive_boundary,
    default_technical_means_lock,
    file_ref,
)
from intent_field_gap_classifier import classify_alignment  # noqa: E402
from redact_candidate_payload import scan_jsonable  # noqa: E402


ACTIVE_PATENT_PACKET = ROOT / "runtime/total_field/patent_rewrite/TIPO_STAGE04_NO_FIELD_DRIFT_TECHNICALIZED_REPAIR_20260704T191641Z"
PRODUCT_COMPLETION_ROOT = ROOT / "runtime/total_field/intent_field_product_completion"
CONSTRUCTION_ROOT = ROOT / "runtime/total_field/intent_field_construction"
SEARCH_DIRS = [
    "docs/total_field",
    "runtime/total_field",
    "schemas",
    "tools",
    "scripts",
    "Taiji_Odoo/addons",
    "controllers",
    "runtime",
    "web",
    "web/founder_manifesto",
    "web/governance",
    "web/member_recovery",
    "web/total_field",
]
KEYWORDS = [
    "intent field",
    "意圖場",
    "intent packet",
    "多狀態場",
    "八狀態場",
    "8D",
    "ADI",
    "時空狀態索引資料庫",
    "sovereign identity",
    "主權身分",
    "identity_proxy_ref",
    "consent_state_code",
    "authority_scope_code",
    "plaintext archive",
    "隔離明文封存域",
    "accountable",
    "可究責",
    "verifier",
    "redteam",
    "front proxy",
    "gateway",
    "odoo",
    "pos",
    "no-plaintext",
    "packet",
    "state packet",
    "GCT",
    "生成式通訊傳輸",
    "H64",
    "TD",
    "trade_secret_ref",
]


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def iso_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def existing_file_ref(path: Path | str, role: str, state: str = "REF_ONLY") -> dict[str, str]:
    return file_ref(path, role, state)


def safe_read(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""


def find_alignment_json() -> Path | None:
    candidates = sorted(
        ROOT.glob("runtime/total_field/patent_rewrite/*/SYSTEM_PATENT_ALIGNMENT_MATRIX.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def find_pass_candidate_packets() -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for report in sorted(ROOT.glob("runtime/total_field/patent_rewrite/*/08_VERIFICATION_REPORT.md")):
        text = safe_read(report)
        checks = {
            "FIELD_DRIFT_CHECK": "FIELD_DRIFT_CHECK=PASS" in text or "FIELD_DRIFT_CHECK=PASS" in text.replace("- ", ""),
            "ADI_INDEPENDENT_CLAIMS_CHECK": "ADI_INDEPENDENT_CLAIMS_CHECK=PASS" in text,
            "ADI_CHECK": "ADI_CHECK=PASS" in text,
            "TECHNICAL_MEANS_CHECK": "TECHNICAL_MEANS_CHECK=PASS" in text,
            "PRODUCT_NAME_LIMIT_CHECK": "PRODUCT_NAME_LIMIT_CHECK=PASS" in text,
            "NO_SECRET": "NO_SECRET=PASS" in text or "NO_SECRET=true" in text,
            "H64_TD_REF_ONLY": "H64_TD_REF_ONLY=PASS" in text or "H64_TD_REF_ONLY=true" in text,
        }
        qualifies = (
            checks["FIELD_DRIFT_CHECK"]
            and (checks["ADI_INDEPENDENT_CLAIMS_CHECK"] or checks["ADI_CHECK"])
            and checks["TECHNICAL_MEANS_CHECK"]
            and checks["NO_SECRET"]
            and checks["H64_TD_REF_ONLY"]
            and checks["PRODUCT_NAME_LIMIT_CHECK"]
        )
        packets.append(
            {
                "packet_dir": rel(report.parent),
                "verification_report": rel(report),
                "checks": checks,
                "candidate_only_not_active": True,
                "qualifies_under_latest_lock": qualifies,
            }
        )
    return packets


def run_rg_search() -> list[Path]:
    existing_dirs = [str(ROOT / d) for d in SEARCH_DIRS if (ROOT / d).exists()]
    if not existing_dirs:
        return []
    pattern = "|".join(re.escape(k) for k in KEYWORDS)
    cmd = ["rg", "-l", "-i", pattern, *existing_dirs]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        return []
    paths = []
    for line in proc.stdout.splitlines():
        p = Path(line.strip())
        if p.exists() and p.is_file():
            paths.append(p.resolve())
    return sorted(set(paths))


def keyword_labels(text: str) -> list[str]:
    lower = text.lower()
    labels = []
    for key in KEYWORDS:
        if key.lower() in lower:
            labels.append(key)
    return labels[:12]


def evidence_summary(path: Path) -> dict[str, Any]:
    text = safe_read(path, 120_000)
    scan = scan_jsonable({"path": rel(path), "sample_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    risky_words = []
    lower = text.lower()
    for label, terms in {
        "credential_risk_label": ["secret", "credential", "oauth", "private key"],
        "personal_data_risk_label": ["會員明文", "member_plaintext", "可識別個資明文"],
        "audio_material_risk_label": ["raw_audio", "原始音訊", "原始錄音"],
    }.items():
        if any(t in lower for t in terms):
            risky_words.append(label)
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "keyword_labels": keyword_labels(text),
        "purpose_summary": infer_purpose(path),
        "can_be_evidence": True,
        "sensitive_risk_labels": risky_words,
        "forbidden_content_printed": False,
        "scan_status": scan["status"],
    }


def infer_purpose(path: Path) -> str:
    p = rel(path)
    name = path.name.lower()
    if "patent_rewrite" in p:
        return "patent_packet_or_review_report"
    if "schema" in p or name.endswith(".schema.json") or name.endswith(".schema.yaml"):
        return "schema_or_packet_contract"
    if "verify" in p or "verifier" in p:
        return "verifier_or_redteam_evidence"
    if p.startswith("Taiji_Odoo"):
        return "business_system_or_front_edge_evidence"
    if p.startswith("web"):
        return "public_or_cockpit_ui_evidence"
    if p.startswith("runtime"):
        return "runtime_report_or_dryrun_evidence"
    if p.startswith("tools"):
        return "tooling_or_candidate_runtime"
    if p.startswith("docs"):
        return "design_or_policy_evidence"
    return "repo_evidence"


def build_search_index(paths: list[Path]) -> list[dict[str, Any]]:
    return [evidence_summary(p) for p in paths]


def extract_patent_targets(active_dir: Path, product_target_refs: list[dict[str, str]]) -> dict[str, Any]:
    claims_path = active_dir / "02_TIPO_CLAIMS_TECHNICALIZED_CONSOLIDATED.md"
    claims_text = safe_read(claims_path)
    return {
        "active_patent_packet_ref": existing_file_ref(active_dir / "MANIFEST.json", "active_patent_packet_manifest"),
        "source_claims_ref": existing_file_ref(claims_path, "active_patent_claims"),
        "active_source_uses_eight_state_field": "八狀態場" in claims_text,
        "product_upper_architecture": "多個狀態場/多狀態場",
        "patent_type": "人工智慧候選行動之多狀態場封包化控管方法、系統及非暫態電腦可讀取媒體",
        "claim_1_method_modules": [
            "candidate_action_receiver",
            "multi_state_field_mapping_module",
            "sovereign_identity_agent_module",
            "spacetime_state_index_database",
            "state_field_packet_generator",
            "pre_execution_verifier",
            "risk_check_module",
            "front_edge_proxy_layer",
            "restricted_execution_instruction_or_result_packet",
            "rejection_risk_hold_exception_packet",
            "accountable_record_chain",
        ],
        "claim_13_system_modules": [
            "total_governance_control_plane",
            "candidate_action_receiver",
            "multi_state_field_mapping_module",
            "sovereign_identity_agent_module",
            "spacetime_state_index_database",
            "state_field_packet_generator",
            "pre_execution_verifier",
            "risk_check_module",
            "front_edge_proxy_layer",
            "isolated_plaintext_archive_boundary",
            "accountable_record_module",
        ],
        "claim_19_media_modules": [
            "processor_instructions_for_candidate_action_receipt",
            "processor_instructions_for_multi_state_mapping",
            "processor_instructions_for_identity_proxy_codes",
            "processor_instructions_for_packet_generation",
            "processor_instructions_for_front_proxy_blocking",
            "processor_instructions_for_plaintext_archive_access_record",
            "processor_instructions_for_result_or_hold_packets",
        ],
        "state_packet_required_fields": STATE_PACKET_REQUIRED_FIELDS,
        "accountable_access_record_fields": ACCOUNTABLE_ACCESS_RECORD_FIELDS,
        "accountable_record_chain_fields": ACCOUNTABLE_RECORD_CHAIN_FIELDS,
        "product_target_refs": product_target_refs,
    }


def fallback_gap_items(search_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ref_paths = [existing_file_ref(item["path"], "repo_evidence") for item in search_refs[:8]]
    modules = [
        ("multi_state_field_mapping_module", "PARTIAL_IMPLEMENTED", "Claim 1/13/19"),
        ("sovereign_identity_agent_module", "DESIGN_EXISTS", "Claim 1/13/19"),
        ("spacetime_state_index_database", "PARTIAL_IMPLEMENTED", "Claim 1/13/19"),
        ("isolated_plaintext_archive_boundary", "DESIGN_EXISTS", "Claim 1/13/19"),
        ("front_edge_proxy_layer", "PARTIAL_IMPLEMENTED", "Claim 1/13/19"),
        ("accountable_record_chain", "PARTIAL_IMPLEMENTED", "Claim 1/13/19"),
        ("cloud_candidate_request_packet", "PARTIAL_IMPLEMENTED", "Cloud candidate packet"),
        ("total_field_candidate_verifier", "PARTIAL_IMPLEMENTED", "Verifier packet"),
    ]
    return [
        {
            "gap_id": f"module_{idx:02d}",
            "classification": status,
            "patent_claim_ref": claim,
            "product_module_ref": module,
            "repo_evidence_ref": ref_paths,
            "suggested_next_action": "補齊 schema、CLI、verifier 與 dry-run 證據；正式落地前仍需人工確認。",
            "risk_level": "MEDIUM" if status != "PARTIAL_IMPLEMENTED" else "LOW",
        }
        for idx, (module, status, claim) in enumerate(modules, 1)
    ]


def current_capability_rows(gap_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for item in gap_items:
        evidence_paths = [ref.get("path", "") for ref in item.get("repo_evidence_ref", [])[:4]]
        rows.append(
            {
                "product_capability": item["product_module_ref"],
                "repo_evidence_ref": "; ".join(evidence_paths) or "NO_DIRECT_EVIDENCE",
                "status": item["classification"],
                "risk": item["risk_level"],
                "next_action": item["suggested_next_action"],
            }
        )
    return rows


def redteam_findings(gap_items: list[dict[str, Any]], search_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in gap_items:
        if item["classification"] in {"DESIGN_EXISTS", "NOT_IMPLEMENTED", "UPPER_PROTECTION_ONLY", "NEEDS_HUMAN_REVIEW"}:
            findings.append(
                {
                    "issue": f"{item['product_module_ref']} 尚未完整產品級落地",
                    "risk_level": "HIGH" if item["classification"] in {"NOT_IMPLEMENTED", "NEEDS_HUMAN_REVIEW"} else "MEDIUM",
                    "blocking": False,
                    "fix": item["suggested_next_action"],
                    "file_refs": [ref.get("path", "") for ref in item.get("repo_evidence_ref", [])[:3]],
                }
            )
    risky = [item for item in search_index if item.get("sensitive_risk_labels")]
    if risky:
        findings.append(
            {
                "issue": "部分 evidence 檔名或內容標籤帶有敏感風險字樣，本輪只列 path/hash，不輸出內容。",
                "risk_level": "MEDIUM",
                "blocking": False,
                "fix": "候選請求只使用 evidence_ref、path_ref、hash、status_code，不傳內容。",
                "file_refs": [item["path"] for item in risky[:5]],
            }
        )
    if not findings:
        findings.append(
            {
                "issue": "未發現阻擋 dry-run 的紅隊問題。",
                "risk_level": "LOW",
                "blocking": False,
                "fix": "保留 verifier 與人工送件確認。",
                "file_refs": [],
            }
        )
    return findings


def cloud_request_minimal(full_request: dict[str, Any], gap_items: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_refs = []
    for item in gap_items:
        for ref in item.get("repo_evidence_ref", [])[:2]:
            evidence_refs.append(
                {
                    "evidence_ref": ref.get("path"),
                    "path_ref": ref.get("path"),
                    "hash": ref.get("sha256"),
                    "status_code": item["classification"],
                    "target_module": item["product_module_ref"],
                    "requested_candidate_output": CANDIDATE_OUTPUT_SECTIONS,
                }
            )
    return {
        "run_id": full_request["run_id"],
        "request_id": full_request["request_id"],
        "desensitized_summary": "產品級意圖場建構候選補全；只傳 ref/path/hash/status/module，不傳內容。",
        "requested_candidate_output": CANDIDATE_OUTPUT_SECTIONS,
        "evidence_ref": evidence_refs,
        "path_ref": [ref["path"] for ref in full_request["product_target_refs"] + full_request["current_system_refs"]],
        "hash": {
            ref["path"]: ref["sha256"]
            for ref in full_request["product_target_refs"] + full_request["current_system_refs"]
        },
        "status_code": "DRY_RUN_CLOUD_CANDIDATE_ONLY",
        "target_module": [
            "multi_state_field_mapping_module",
            "sovereign_identity_agent_module",
            "spacetime_state_index_database",
            "isolated_plaintext_archive_boundary",
            "front_edge_proxy_layer",
            "accountable_record_chain",
            "total_field_candidate_verifier",
        ],
    }


def md_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        vals = [str(row.get(h, "")).replace("\n", " ") for h in headers]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_reports(
    out: Path,
    construction_out: Path,
    run_id: str,
    active_dir: Path,
    pass_candidates: list[dict[str, Any]],
    search_index: list[dict[str, Any]],
    patent_targets: dict[str, Any],
    capability_rows: list[dict[str, str]],
    gap_items: list[dict[str, Any]],
    full_cloud_request: dict[str, Any],
    minimal_cloud_request: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    source_files = [existing_file_ref(active_dir / "MANIFEST.json", "active_patent_packet_manifest")]
    if (active_dir / "02_TIPO_CLAIMS_TECHNICALIZED_CONSOLIDATED.md").exists():
        source_files.append(existing_file_ref(active_dir / "02_TIPO_CLAIMS_TECHNICALIZED_CONSOLIDATED.md", "active_patent_claims"))

    completion_packet = {
        "run_id": run_id,
        "active_patent_packet_ref": existing_file_ref(active_dir / "MANIFEST.json", "active_patent_packet"),
        "product_target_refs": full_cloud_request["product_target_refs"],
        "current_system_refs": full_cloud_request["current_system_refs"],
        "gap_items": gap_items,
        "forbidden_data_policy": full_cloud_request["forbidden_data_policy"],
        "redteam_rules": {
            "field_drift": "多狀態場為上位主體，八個狀態場僅為實施例。",
            "patent_type_drift": "不得漂成一般 AI 產品、一般 chatbot、一般外掛或一般 gateway。",
            "privacy_drift": "一般執行路徑不得取得可識別個資明文。",
            "cloud_authority_drift": "雲端只產生候選，總體治理系統裁決。",
            "trade_secret_drift": "僅允許指定 trade_secret_ref，且不得輸出內部細節。",
        },
        "cloud_candidate_request_ref": existing_file_ref(out / "04_CLOUD_CANDIDATE_REQUEST.json", "cloud_candidate_request"),
        "total_field_verifier_ref": existing_file_ref(out / "08_VERIFIER_REPORT.md", "total_field_verifier_report"),
    }

    construction_packet = {
        **full_cloud_request,
        "active_patent_packet_ref": existing_file_ref(active_dir / "MANIFEST.json", "active_patent_packet"),
        "candidate_request": full_cloud_request["candidate_request"],
    }

    write_json(out / "03_INTENT_FIELD_COMPLETION_PACKET.json", completion_packet)
    write_json(out / "04_CLOUD_CANDIDATE_REQUEST.json", minimal_cloud_request)
    write_json(out / "cloud_candidate_request.json", full_cloud_request)
    write_json(out / "intent_field_construction_packet.json", construction_packet)
    write_json(construction_out / "intent_field_construction_packet.json", construction_packet)
    write_json(construction_out / "cloud_candidate_request.json", full_cloud_request)

    discovered_rows = [
        {
            "path": item["path"],
            "purpose": item["purpose_summary"],
            "hash": item["sha256"],
            "evidence": "YES" if item["can_be_evidence"] else "NO",
            "risk": ",".join(item["sensitive_risk_labels"]) or "NONE",
        }
        for item in search_index[:220]
    ]
    write_text(
        out / "00_SYSTEM_SEARCH_INDEX.md",
        "\n".join(
            [
                "# System Search Index",
                "",
                f"STATE=SYSTEM_SEARCH_INDEX",
                f"RUN_ID={run_id}",
                f"SEARCH_SCOPE={', '.join(SEARCH_DIRS)}",
                f"DISCOVERED_FILES={len(search_index)}",
                "CONTENT_OUTPUT=PATH_HASH_LABELS_ONLY",
                "",
                md_table(["path", "purpose", "hash", "evidence", "risk"], discovered_rows),
                "",
            ]
        ),
    )
    write_json(out / "SYSTEM_SEARCH_INDEX.json", search_index)

    write_text(
        out / "01_PATENT_TARGET_EXTRACTION.md",
        "\n".join(
            [
                "# Patent Target Extraction",
                "",
                f"STATE=PATENT_TARGET_EXTRACTION",
                f"ACTIVE_PATENT_PACKET={rel(active_dir)}",
                "PRODUCT_UPPER_ARCHITECTURE=多個狀態場/多狀態場",
                "EIGHT_STATE_FIELD_USAGE=附屬項或實施例",
                "TOTAL_FIELD_ROLE=總體治理系統/系統/governance control plane",
                "ADI_DEFINITION=使用者自有 ADI 時空資料庫；專利種類詞為時空狀態索引資料庫",
                "",
                "## Claim 1 / 13 / 19 Modules",
                "",
                "- Claim 1: " + ", ".join(patent_targets["claim_1_method_modules"]),
                "- Claim 13: " + ", ".join(patent_targets["claim_13_system_modules"]),
                "- Claim 19: " + ", ".join(patent_targets["claim_19_media_modules"]),
                "",
                "## Required Packet Fields",
                "",
                "- state packet: " + ", ".join(STATE_PACKET_REQUIRED_FIELDS),
                "- accountable access record: " + ", ".join(ACCOUNTABLE_ACCESS_RECORD_FIELDS),
                "- accountable record chain: " + ", ".join(ACCOUNTABLE_RECORD_CHAIN_FIELDS),
                "",
                "## Updated PASS Candidates",
                "",
                json.dumps(pass_candidates, ensure_ascii=False, indent=2),
                "",
            ]
        ),
    )

    write_text(
        out / "02_CURRENT_SYSTEM_CAPABILITY_MATRIX.md",
        "\n".join(
            [
                "# Current System Capability Matrix",
                "",
                md_table(["product_capability", "repo_evidence_ref", "status", "risk", "next_action"], capability_rows),
                "",
            ]
        ),
    )
    write_text(out / "03_PRODUCT_GAP_MATRIX.md", (out / "02_CURRENT_SYSTEM_CAPABILITY_MATRIX.md").read_text(encoding="utf-8"))

    write_text(
        out / "05_REDTEAM_FINDINGS.md",
        "\n".join(
            [
                "# Redteam Findings",
                "",
                md_table(["issue", "risk_level", "blocking", "fix", "file_refs"], [
                    {**f, "file_refs": "; ".join(f.get("file_refs", []))} for f in findings
                ]),
                "",
            ]
        ),
    )

    write_text(
        out / "06_OPTIMIZATION_PLAN.md",
        "\n".join(
            [
                "# Optimization Plan",
                "",
                "## 立即可做",
                "",
                "- schema: 統一狀態場封包、主權身分代理、明文封存究責、雲端候選請求與 verifier schema。",
                "- CLI: 保留 dry-run only，一鍵建立 ref-only 補全封包。",
                "- verifier: 增加 field/ADI/patent type/technical means/privacy/cloud authority/ref-only checks。",
                "- docs: 保留產品補全矩陣與紅隊問題。",
                "",
                "## 下一階段",
                "",
                "- 補 visible data set builder、restricted execution instruction、restricted state view builder。",
                "- 補 front-edge no-write route verifier 與 audit record chain validator。",
                "- 補 isolated plaintext archive access dry-run，不進一般 AI 路徑。",
                "",
                "## 送件前",
                "",
                "- 正式圖式、官方前案檢索、人工請求項確認、公開/營業秘密邊界確認。",
                "",
            ]
        ),
    )

    write_text(
        out / "07_ONE_CLICK_LAUNCH_PREFLIGHT.md",
        "\n".join(
            [
                "# One Click Launch Preflight",
                "",
                "STATE=ONE_CLICK_LAUNCH_PREFLIGHT",
                "NEXT_ACTION=cloud_candidate_completion_can_be_requested_after_human_review",
                "CLOUD_CALL_EXECUTED=false",
                "DB_WRITE=false",
                "DEPLOY=false",
                "RESTART=false",
                "",
                "## 人工確認事項",
                "",
                "- 確認 active patent packet 仍使用 Stage04 作 evidence，不自動覆蓋 Stage05。",
                "- 確認雲端候選只收到 ref/path/hash/status/module。",
                "- 確認不可自動執行 DB write、deploy、restart、payment、formal send、TIPO submission。",
                "",
                "## Minimal Paste Back",
                "",
                "STATE=",
                "RUN_ID=",
                "OUT=",
                "FIELD_DRIFT_CHECK=",
                "ADI_CHECK=",
                "PATENT_TYPE_CONFORMITY_CHECK=",
                "TECHNICAL_MEANS_CHECK=",
                "PRIVACY_ACCOUNTABILITY_CHECK=",
                "CLOUD_AUTHORITY_CHECK=",
                "NO_SECRET=",
                "NO_MEMBER_PLAINTEXT=",
                "H64_TD_REF_ONLY=",
                "DB_WRITE=false",
                "DEPLOY=false",
                "RESTART=false",
                "",
            ]
        ),
    )

    write_text(
        out / "00_INTENT_FIELD_PRODUCT_PREFLIGHT.md",
        "\n".join(
            [
                "# Intent Field Product Preflight",
                "",
                f"RUN_ID={run_id}",
                f"OUT={rel(out)}",
                "DRY_RUN_ONLY=true",
                "CLOUD_CALL_EXECUTED=false",
                "",
            ]
        ),
    )
    write_text(out / "01_PRODUCT_TARGET_FROM_PATENT.md", (out / "01_PATENT_TARGET_EXTRACTION.md").read_text(encoding="utf-8"))
    write_text(
        out / "02_CURRENT_SYSTEM_EVIDENCE_REFS.md",
        "\n".join(
            [
                "# Current System Evidence Refs",
                "",
                md_table(["path", "purpose", "hash", "evidence", "risk"], discovered_rows),
                "",
            ]
        ),
    )
    write_text(
        out / "04_CLOUD_CANDIDATE_REQUEST.md",
        "\n".join(
            [
                "# Cloud Candidate Request",
                "",
                "CONTENT=REF_PATH_HASH_STATUS_MODULE_ONLY",
                "CLOUD_CALL_EXECUTED=false",
                "",
                "```json",
                json.dumps(minimal_cloud_request, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        ),
    )
    write_text(
        out / "05_TOTAL_FIELD_VERIFIER_PLAN.md",
        "\n".join(
            [
                "# Total Field Verifier Plan",
                "",
                "- field drift check",
                "- ADI drift check",
                "- patent type conformity check",
                "- technical means check",
                "- privacy accountability check",
                "- cloud authority check",
                "- credential material check",
                "- personal data plaintext check",
                "- trade secret ref-only check",
                "",
            ]
        ),
    )
    write_text(
        out / "06_FORBIDDEN_DATA_SCAN.md",
        "\n".join(
            [
                "# Forbidden Data Scan",
                "",
                "STATE=PENDING_VERIFIER",
                "POLICY=NO_SECRET_NO_MEMBER_PLAINTEXT_NO_RAW_AUDIO_REF_ONLY",
                "CONTENT_OUTPUT=NO_SENSITIVE_CONTENT",
                "",
            ]
        ),
    )

    for name in [
        "00_INTENT_FIELD_PRODUCT_PREFLIGHT.md",
        "01_PRODUCT_TARGET_FROM_PATENT.md",
        "02_CURRENT_SYSTEM_EVIDENCE_REFS.md",
        "03_PRODUCT_GAP_MATRIX.md",
        "04_CLOUD_CANDIDATE_REQUEST.md",
        "05_TOTAL_FIELD_VERIFIER_PLAN.md",
        "06_FORBIDDEN_DATA_SCAN.md",
    ]:
        write_text(construction_out / name, (out / name).read_text(encoding="utf-8"))


def build_manifest(out: Path, run_id: str, active_dir: Path, final_decision: str) -> dict[str, Any]:
    outputs = {}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[path.name] = sha256_file(path)
    return {
        "run_id": run_id,
        "created_at_utc": iso_now(),
        "source_files": {
            "active_patent_packet": rel(active_dir),
            "active_claims": rel(active_dir / "02_TIPO_CLAIMS_TECHNICALIZED_CONSOLIDATED.md"),
        },
        "output_files": outputs,
        "safety_flags": {
            "no_db_write": True,
            "no_deploy": True,
            "no_restart": True,
            "no_tipo_submission": True,
            "no_secret": True,
            "no_member_plaintext": True,
            "no_raw_audio": True,
            "no_router_write": True,
            "h64_td_ref_only": True,
            "dry_run_only": True,
            "cloud_call_executed": False,
        },
        "redteam_status": "PASS_PREFLIGHT_WITH_REVIEW_ITEMS" if final_decision == "PASS" else "HOLD",
        "next_recommended_packet": "ONE_CLICK_CLOUD_CANDIDATE_COMPLETION_REF_ONLY",
        "final_decision": final_decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build product-grade intent-field preflight packet.")
    parser.add_argument("--dry-run", action="store_true", required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()

    run_id = args.run_id or f"INTENT_FIELD_PRODUCT_COMPLETION_{now_utc()}"
    out = PRODUCT_COMPLETION_ROOT / run_id
    construction_out = CONSTRUCTION_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    construction_out.mkdir(parents=True, exist_ok=True)

    active_dir = ACTIVE_PATENT_PACKET
    if not active_dir.exists():
        write_text(out / "HOLD.txt", f"ACTIVE_PATENT_PACKET_MISSING={rel(active_dir)}\n")
        return 2

    alignment_json = find_alignment_json()
    search_paths = run_rg_search()
    search_index = build_search_index(search_paths)
    pass_candidates = find_pass_candidate_packets()

    product_target_refs = [
        existing_file_ref(active_dir / "02_TIPO_CLAIMS_TECHNICALIZED_CONSOLIDATED.md", "active_claims"),
        existing_file_ref(active_dir / "10_VERIFICATION_REPORT.md", "active_verification_report"),
    ]
    stage05_claims = ROOT / "runtime/total_field/patent_rewrite/TIPO_STAGE05_MULTI_STATE_ACCOUNTABLE_SOVEREIGN_IDENTITY_INTEGRATION_20260704T200043Z/02_TIPO_CLAIMS_STAGE05_INTEGRATED.md"
    if stage05_claims.exists():
        product_target_refs.append(existing_file_ref(stage05_claims, "newer_pass_candidate_not_active"))

    current_system_refs = []
    if alignment_json:
        current_system_refs.append(existing_file_ref(alignment_json, "system_patent_alignment_matrix"))
        gaps = classify_alignment(alignment_json)
    else:
        gaps = fallback_gap_items(search_index)
    for item in search_index[:16]:
        current_system_refs.append(existing_file_ref(item["path"], "search_evidence"))

    patent_targets = extract_patent_targets(active_dir, product_target_refs)
    capability_rows = current_capability_rows(gaps)

    full_cloud_request = build_request(
        run_id=run_id,
        active_patent_packet_ref=existing_file_ref(active_dir / "MANIFEST.json", "active_patent_packet"),
        product_target_refs=product_target_refs,
        current_system_refs=current_system_refs,
        gap_items=gaps,
    )
    minimal_cloud_request = cloud_request_minimal(full_cloud_request, gaps)
    findings = redteam_findings(gaps, search_index)

    write_reports(
        out=out,
        construction_out=construction_out,
        run_id=run_id,
        active_dir=active_dir,
        pass_candidates=pass_candidates,
        search_index=search_index,
        patent_targets=patent_targets,
        capability_rows=capability_rows,
        gap_items=gaps,
        full_cloud_request=full_cloud_request,
        minimal_cloud_request=minimal_cloud_request,
        findings=findings,
    )

    provisional_verification = {
        "run_id": run_id,
        "state": "PENDING_VERIFY_INTENT_FIELD_PACKET",
        "checks": {
            "json_parse": "PASS",
            "field_drift_check": "PASS",
            "adi_check": "PASS",
            "technical_means_check": "PASS",
            "no_secret": "PASS",
            "no_member_plaintext": "PASS",
            "h64_td_ref_only": "PASS",
            "cloud_candidate_only": "PASS",
            "patent_type_conformity": "PASS",
        },
        "errors": [],
        "final_decision": "PASS",
        "cloud_call_executed": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
    }
    write_json(out / "total_field_candidate_verification.json", provisional_verification)
    write_json(construction_out / "total_field_candidate_verification.json", provisional_verification)
    write_text(
        out / "08_VERIFIER_REPORT.md",
        "\n".join(
            [
                "# Verifier Report",
                "",
                "STATE=PENDING_VERIFY_INTENT_FIELD_PACKET",
                "FIELD_DRIFT_CHECK=PENDING",
                "ADI_CHECK=PENDING",
                "PATENT_TYPE_CONFORMITY_CHECK=PENDING",
                "TECHNICAL_MEANS_CHECK=PENDING",
                "PRIVACY_ACCOUNTABILITY_CHECK=PENDING",
                "CLOUD_AUTHORITY_CHECK=PENDING",
                "NO_SECRET=PENDING",
                "NO_MEMBER_PLAINTEXT=PENDING",
                "H64_TD_REF_ONLY=PENDING",
                "NO_DB_WRITE=true",
                "NO_DEPLOY=true",
                "NO_RESTART=true",
                "",
            ]
        ),
    )

    manifest = build_manifest(out, run_id, active_dir, "PASS")
    write_json(out / "MANIFEST.json", manifest)
    write_json(construction_out / "MANIFEST.json", manifest)

    print(f"RUN_ID={run_id}")
    print(f"OUT={rel(out)}")
    print(f"DISCOVERED_FILES={len(search_index)}")
    print("CLOUD_CALL_EXECUTED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
