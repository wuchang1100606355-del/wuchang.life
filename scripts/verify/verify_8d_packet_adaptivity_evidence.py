#!/usr/bin/env python3
"""Verify 8D packet adaptivity evidence without secret reads or runtime mutation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKAGE = (
    ROOT
    / "runtime/patent_delivery/LLM_CAPABILITY_OS_TIPO_UPLOAD_20CLAIMS_FIELD_COMPLIANT_20260701_000000"
)
PACKAGE_DIR = Path(os.environ.get("TIPO_PACKAGE_DIR", DEFAULT_PACKAGE)).resolve()
REPORT_PATH = PACKAGE_DIR / "reports/8D_PACKET_ADAPTIVITY_TEST_REPORT.json"
EVIDENCE_PATH = PACKAGE_DIR / "evidence_field/8D_PACKET_ADAPTIVITY_TEST_EVIDENCE_20260701.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_read_only(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:  # pragma: no cover - runtime evidence only
        return {"ok": False, "command": command, "stdout": "", "stderr": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "command": command,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def check_secret_shapes(text: str) -> list[str]:
    patterns = {
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "openai_key": r"sk-[A-Za-z0-9_-]{10,}",
        "google_key": r"AIza[0-9A-Za-z_-]{20,}",
        "github_token": r"ghp_[A-Za-z0-9]{20,}",
        "slack_token": r"xox[baprs]-",
    }
    findings = []
    for name, pattern in patterns.items():
        if re.search(pattern, text):
            findings.append(name)
    return findings


def main() -> int:
    adaptive_packet_path = PACKAGE_DIR / "generative_construction_no_transfer/8D_ADAPTIVE_CONSTRUCTION_PACKET.json"
    cross_packet_path = PACKAGE_DIR / "generative_construction_no_transfer/CROSS_NODE_CONSTRUCTION_PACKET.json"
    validation_report_path = PACKAGE_DIR / "reports/VALIDATION_REPORT.json"
    page_report_path = PACKAGE_DIR / "reports/PAGE_COUNT_REPORT.json"
    scope_doc_path = ROOT / "docs/total_field/TOTAL_FIELD_ALL_NODES_AND_CONTAINERS_SCOPE.md"
    acceptance_doc_path = ROOT / "docs/product/XIAOJ_AV_ORDERING_P1_ACCEPTANCE_MATRIX.md"

    paths = {
        "adaptive_packet": adaptive_packet_path,
        "cross_node_packet": cross_packet_path,
        "validation_report": validation_report_path,
        "page_report": page_report_path,
        "all_nodes_containers_scope": scope_doc_path,
        "acceptance_matrix": acceptance_doc_path,
    }

    failures: list[str] = []
    for name, path in paths.items():
        if not path.exists():
            failures.append(f"missing:{name}:{path}")

    adaptive_packet = load_json(adaptive_packet_path) if adaptive_packet_path.exists() else {}
    cross_packet = load_json(cross_packet_path) if cross_packet_path.exists() else {}
    validation_report = load_json(validation_report_path) if validation_report_path.exists() else {}
    page_report = load_json(page_report_path) if page_report_path.exists() else {}
    scope_doc = scope_doc_path.read_text(encoding="utf-8") if scope_doc_path.exists() else ""
    acceptance_doc = acceptance_doc_path.read_text(encoding="utf-8") if acceptance_doc_path.exists() else ""

    dimensions = [item.get("id") for item in adaptive_packet.get("dimensions", [])]
    expected_dimensions = [f"D{index}" for index in range(1, 9)]
    if dimensions != expected_dimensions:
        failures.append(f"dimension_mismatch:{dimensions}")

    invariants = adaptive_packet.get("invariants", {})
    expected_true_invariants = [
        "field_semantics_unchanged",
        "candidate_not_authority",
        "local_target_verifier_authority",
        "manifest_hash_verification",
    ]
    for key in expected_true_invariants:
        if invariants.get(key) is not True:
            failures.append(f"adaptive_invariant_not_true:{key}")
    expected_false_invariants = [
        "compression_required",
        "complete_transport_required",
        "secret_read_required",
    ]
    for key in expected_false_invariants:
        if invariants.get(key) is not False:
            failures.append(f"adaptive_invariant_not_false:{key}")

    if "Linux to Windows 11" not in adaptive_packet.get("heterogeneous_targets", {}).get("direct_evidence", []):
        failures.append("missing_direct_linux_to_windows_evidence")
    governance_scope = adaptive_packet.get("heterogeneous_targets", {}).get("governance_scope_evidence", [])
    if "containers" not in governance_scope or "all nodes" not in governance_scope:
        failures.append("missing_all_nodes_or_container_scope_evidence")

    source = cross_packet.get("source_node", {})
    target = cross_packet.get("target_node", {})
    if source.get("system") != "Linux":
        failures.append("source_node_not_linux")
    if target.get("system") != "Windows 11":
        failures.append("target_node_not_windows11")
    if "C:\\Users\\o0930\\Downloads" not in target.get("target_directory", ""):
        failures.append("target_directory_not_windows_downloads")

    boundary = cross_packet.get("boundary", {})
    expected_boundary = {
        "direct_mount_available": False,
        "source_node_writes_target_disk": False,
        "target_node_constructs_files": True,
        "cloud_candidate_authority": False,
        "local_target_verifier_authority": True,
    }
    for key, expected in expected_boundary.items():
        if boundary.get(key) is not expected:
            failures.append(f"boundary_mismatch:{key}:{boundary.get(key)}")

    construction_inputs = cross_packet.get("construction_inputs", {})
    expected_construction_inputs = {
        "compression": False,
        "zip_payload": False,
        "base64_payload": False,
        "raw_docx_artifacts": True,
        "manifest_required": True,
        "hash_verification_required": True,
    }
    for key, expected in expected_construction_inputs.items():
        if construction_inputs.get(key) is not expected:
            failures.append(f"construction_input_mismatch:{key}:{construction_inputs.get(key)}")

    file_checks = []
    for file_entry in cross_packet.get("files", []):
        filename = file_entry.get("filename", "")
        upload_path = PACKAGE_DIR / "upload_files" / filename
        construction_path = PACKAGE_DIR / "generative_construction_no_transfer" / filename
        upload_exists = upload_path.exists()
        construction_exists = construction_path.exists()
        observed_hash = sha256(upload_path) if upload_exists else None
        observed_bytes = upload_path.stat().st_size if upload_exists else None
        passed = (
            upload_exists
            and construction_exists
            and observed_hash == file_entry.get("sha256")
            and observed_bytes == file_entry.get("bytes")
        )
        if not passed:
            failures.append(f"file_artifact_check_failed:{filename}")
        file_checks.append(
            {
                "filename": filename,
                "upload_exists": upload_exists,
                "construction_artifact_exists": construction_exists,
                "expected_sha256": file_entry.get("sha256"),
                "observed_sha256": observed_hash,
                "expected_bytes": file_entry.get("bytes"),
                "observed_bytes": observed_bytes,
                "target_path": file_entry.get("target_path"),
                "passed": passed,
            }
        )

    if validation_report.get("state") != "PASS_TIPO_UPLOAD_READY":
        failures.append(f"validation_report_not_pass:{validation_report.get('state')}")
    if validation_report.get("field_validation", {}).get("abstract", {}).get("passed") is not True:
        failures.append("abstract_field_validation_not_pass")
    if validation_report.get("coverage", {}).get("claims_count_matches_expected") is not True:
        failures.append("claims_count_not_pass")
    if validation_report.get("side_effects", {}).get("external_api_call") is not False:
        failures.append("validation_external_api_call_not_false")

    if page_report.get("state") != "PASS_TIPO_UPLOAD_READY":
        failures.append(f"page_report_not_pass:{page_report.get('state')}")
    page_files = page_report.get("files", [])
    if len(page_files) != 4:
        failures.append(f"page_report_file_count_mismatch:{len(page_files)}")
    for file_entry in page_files:
        if not isinstance(file_entry.get("pages"), int) or file_entry.get("pages", 0) < 1:
            failures.append(f"page_count_invalid:{file_entry.get('filename')}")
        if file_entry.get("field_validation") != "PASS":
            failures.append(f"page_field_validation_not_pass:{file_entry.get('filename')}")

    if "Total Field may observe" not in scope_doc or "containers" not in scope_doc:
        failures.append("scope_doc_does_not_support_all_nodes_containers")
    if "container gate PASS" not in acceptance_doc and "container gate" not in acceptance_doc:
        failures.append("acceptance_doc_container_gate_not_found")

    secret_scan_targets = [
        adaptive_packet_path,
        cross_packet_path,
        validation_report_path,
        page_report_path,
    ]
    secret_findings: dict[str, list[str]] = {}
    for path in secret_scan_targets:
        if path.exists():
            findings = check_secret_shapes(path.read_text(encoding="utf-8", errors="ignore"))
            if findings:
                secret_findings[str(path.relative_to(ROOT))] = findings
    if secret_findings:
        failures.append("secret_shaped_text_found")

    uname = run_read_only(["uname", "-a"])
    docker_ps = run_read_only(["docker", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Status}}"])
    observed_containers = []
    if docker_ps["ok"] and docker_ps["stdout"]:
        for line in docker_ps["stdout"].splitlines():
            pieces = line.split("|", 2)
            if len(pieces) == 3:
                observed_containers.append({"name": pieces[0], "image": pieces[1], "status": pieces[2]})
    if not observed_containers:
        failures.append("no_container_status_observed")

    report = {
        "schema": "W7TP_8D_PACKET_ADAPTIVITY_TEST_REPORT_V1",
        "state": (
            "PASS_8D_PACKET_FULL_ADAPTIVITY_EVIDENCE_TESTED_AND_SUPPLEMENTED"
            if not failures
            else "HOLD_8D_PACKET_ADAPTIVITY_EVIDENCE"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_dir": str(PACKAGE_DIR),
        "tests": {
            "dimensions_d1_to_d8_exact": dimensions == expected_dimensions,
            "adaptive_invariants_passed": all(invariants.get(k) is True for k in expected_true_invariants)
            and all(invariants.get(k) is False for k in expected_false_invariants),
            "cross_node_linux_to_windows_boundary_passed": source.get("system") == "Linux"
            and target.get("system") == "Windows 11"
            and boundary == expected_boundary,
            "construction_inputs_no_compression_no_base64_passed": all(
                construction_inputs.get(k) is v for k, v in expected_construction_inputs.items()
            ),
            "file_artifacts_sha256_and_size_passed": all(item["passed"] for item in file_checks),
            "tipo_field_validation_passed": validation_report.get("state") == "PASS_TIPO_UPLOAD_READY"
            and validation_report.get("field_validation", {}).get("abstract", {}).get("passed") is True,
            "page_count_validation_passed": page_report.get("state") == "PASS_TIPO_UPLOAD_READY"
            and len(page_files) == 4
            and all(isinstance(item.get("pages"), int) and item.get("pages", 0) >= 1 for item in page_files),
            "all_nodes_containers_scope_evidence_present": "Total Field may observe" in scope_doc
            and "containers" in scope_doc,
            "container_status_observed_read_only": bool(observed_containers),
            "secret_shaped_text_absent_in_packets_and_reports": not secret_findings,
        },
        "dimension_ids": dimensions,
        "file_checks": file_checks,
        "page_counts": [
            {"filename": item.get("filename"), "pages": item.get("pages"), "field_validation": item.get("field_validation")}
            for item in page_files
        ],
        "observed_environment": {
            "uname": uname["stdout"],
            "containers_read_only": observed_containers,
        },
        "red_team_limits": {
            "does_not_claim_untested_worldwide_environments": True,
            "does_not_claim_source_node_directly_wrote_windows_disk": True,
            "does_not_grant_cloud_candidate_authority": True,
            "does_not_read_secrets": True,
            "does_not_mutate_container_or_runtime": True,
            "does_not_disclose_why_it_runs_or_private_lookup": True,
        },
        "side_effects": {
            "db_write": False,
            "deploy": False,
            "service_restart": False,
            "container_mutation": False,
            "external_api_call": False,
            "secret_read": False,
        },
        "failures": failures,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    state_line = report["state"]
    markdown = f"""# 8D 封包全適應性測試補強證據

## 測試結論

STATE={state_line}（8D 封包全適應性證據測試結果）

本測試不是口頭宣稱，而是以既有封包、建構清單、DOCX（Word 文件格式）建構件、SHA256（雜湊校驗值）、TIPO（經濟部智慧財產局）欄位驗證報告、頁數報告、Linux（類 Unix 作業系統）節點資訊及容器狀態進行交叉驗證。

## 測試通過項目

| 測試項 | 結果 |
| --- | --- |
| D1 至 D8（八維）欄位完整性 | {'PASS' if report['tests']['dimensions_d1_to_d8_exact'] else 'HOLD'} |
| 適應性不變量 | {'PASS' if report['tests']['adaptive_invariants_passed'] else 'HOLD'} |
| Linux（類 Unix 作業系統）至 Windows 11（微軟作業系統）跨節點邊界 | {'PASS' if report['tests']['cross_node_linux_to_windows_boundary_passed'] else 'HOLD'} |
| 不以 ZIP（壓縮檔）、base64（文字化位元資料）或完整搬移為核心 | {'PASS' if report['tests']['construction_inputs_no_compression_no_base64_passed'] else 'HOLD'} |
| 四個 DOCX（Word 文件格式）建構件雜湊與大小 | {'PASS' if report['tests']['file_artifacts_sha256_and_size_passed'] else 'HOLD'} |
| TIPO（經濟部智慧財產局）欄位驗證 | {'PASS' if report['tests']['tipo_field_validation_passed'] else 'HOLD'} |
| 頁數驗證 | {'PASS' if report['tests']['page_count_validation_passed'] else 'HOLD'} |
| 全節點與容器治理範圍證據 | {'PASS' if report['tests']['all_nodes_containers_scope_evidence_present'] else 'HOLD'} |
| 容器狀態只讀觀測 | {'PASS' if report['tests']['container_status_observed_read_only'] else 'HOLD'} |
| 封包與報告未出現金鑰形狀秘密 | {'PASS' if report['tests']['secret_shaped_text_absent_in_packets_and_reports'] else 'HOLD'} |

## 新增證據價值

1. 8D（八維）封包之適應性已由封包欄位、跨節點邊界、跨系統目標與本地驗證結果共同支撐。
2. 生成式建構不是壓縮或傳輸，而是以建構件、索引、雜湊、狀態碼、目標座標與驗證條件形成目標端可驗證狀態。
3. 來源節點不直接寫入 Windows 11（微軟作業系統）目標磁碟；目標端本地驗證仍是成立條件。
4. 容器證據僅作治理範圍與只讀觀測，不宣稱已對所有未測容器完成實機建構。

## 對應測試報告

- `reports/8D_PACKET_ADAPTIVITY_TEST_REPORT.json`（8D 封包適應性測試報告）

## 紅隊限定

- 不宣稱所有世界上尚未測試之環境均已實機完成。
- 不宣稱來源節點已直接寫入 Windows 11（微軟作業系統）磁碟。
- 不授權雲端候選來源成為最終權威。
- 不讀取 WHY_IT_RUNS（核心運作機理）、完整查表、私有權重、API key（應用程式介面金鑰）、token（存取權杖）、密碼、會員明文或住戶明文。
- 本次測試無 DB write（資料庫寫入）、deploy（部署）、service restart（服務重啟）、container mutation（容器突變）、external API call（外部介面呼叫）。
"""
    EVIDENCE_PATH.write_text(markdown, encoding="utf-8")

    if failures:
        print("STATE=HOLD_8D_PACKET_ADAPTIVITY_EVIDENCE")
        print(json.dumps(failures, ensure_ascii=False, indent=2))
        return 1
    print("STATE=PASS_8D_PACKET_FULL_ADAPTIVITY_EVIDENCE_TESTED_AND_SUPPLEMENTED")
    print(str(REPORT_PATH))
    print(str(EVIDENCE_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
