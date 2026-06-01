#!/usr/bin/env python3
"""Local-only metric predictive alert scanner.

The scanner emits proactive L1/L2/L3 developer prompts without reading secret
file contents, entering containers, calling cloud APIs, or mutating services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT_DIR / "Taiji_Governance" / "logs" / "metric_predictive_alert_report.json"
SCHEMA = "taiji.metric_predictive_alert_report.v1"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "archive",
    "data",
    "keys",
    "Taiji_Odoo/odoo_data",
    "Taiji_Odoo/postgres_data",
}

TEXT_SUFFIXES = {
    ".py",
    ".sh",
    ".ps1",
    ".yml",
    ".yaml",
    ".md",
    ".json",
    ".toml",
    ".txt",
    ".html",
}

PATTERNS = [
    {
        "id": "remote_execution",
        "risk": "L3_metric_hazard",
        "regex": r"\bssh\b|\bscp\b|StrictHostKeyChecking=no|systemctl\s+restart|docker\s+compose\s+(up|down)\b|taiji-guarded-run|--execute",
        "prompt": "偵測到遠端執行或 live mutation pattern；必須改成 manifest/preflight/rollback。",
        "safe_next_action": "移到設計窗產生 patch proposal，不執行 live command。",
        "recommended_solution": "將 live command 拆成 deployment manifest、preflight report、rollback plan 與 human decision packet。",
        "impact_assessment": {
            "benefit": "阻擋未授權 production mutation，保留審查與回滾能力。",
            "cost": "需要額外維護 manifest/preflight 流程。",
            "risk": "若未完成 Gateway/Five Metric runtime，仍只能停留在部署準備窗。",
            "rollback": "保留舊腳本但封鎖執行路徑，回復以 patch revert 為準。",
        },
    },
    {
        "id": "direct_cloud_api",
        "risk": "L3_metric_hazard",
        "regex": r"google\.generativeai|from\s+google\s+import\s+genai|generativelanguage\.googleapis\.com|googleapiclient\.discovery|from\s+google\.oauth2\s+import\s+service_account",
        "prompt": "偵測到 direct Google/Gemini/Workspace API pattern；必須改走 Gateway policy stub。",
        "safe_next_action": "保持本地設計，不呼叫外部 API。",
        "recommended_solution": "建立 Google Workspace request manifest，將 Odoo 無敏資料映射、scope、用途與 rollback 交給 Gateway/Five Metric 判斷。",
        "impact_assessment": {
            "benefit": "保留 Google 作為無敏帳戶權限管理系統，避免雲端明文與 service account 外洩。",
            "cost": "需要先完成 Gateway policy stub 與 scope manifest。",
            "risk": "Domain-wide delegation 若誤用仍是高風險，預設不得啟用。",
            "rollback": "保留 direct call 為 legacy hazard，不接入 runtime。",
        },
    },
    {
        "id": "shell_execution_surface",
        "risk": "L2_drift",
        "regex": r"create_subprocess_shell|os\.system|\bPopen\b|subprocess\.run",
        "prompt": "偵測到本地 shell execution surface；需確認是否只讀、可回滾、無 secret。",
        "safe_next_action": "補 command allowlist、timeout、audit 與測試。",
        "recommended_solution": "用固定 command list、timeout、no-shell、redacted output 與 audit record 包住本地命令。",
        "impact_assessment": {
            "benefit": "保留本地自動化能力，同時降低命令注入與誤執行。",
            "cost": "每個命令需要明確 allowlist 與測試。",
            "risk": "若命令可寫系統或讀 secret，需提升到 L3 阻擋。",
            "rollback": "移除或停用該命令入口。",
        },
    },
    {
        "id": "wide_bind",
        "risk": "L2_drift",
        "regex": r"0\.0\.0\.0|host\s*=\s*[\"']0\.0\.0\.0[\"']",
        "prompt": "偵測到 wide bind pattern；需確認是否受 VPN/Gateway/ACL 保護。",
        "safe_next_action": "優先收斂到 127.0.0.1 或補 Gateway/VPN proof。",
        "recommended_solution": "預設改為 localhost binding；若必須公開，補 VPN ACL、Gateway proof 與 exposure audit。",
        "impact_assessment": {
            "benefit": "減少未授權網路暴露面。",
            "cost": "部分跨設備 UI 需改走 Gateway 或 VPN。",
            "risk": "WebUI/Odoo 類服務若外露可能造成帳號或資料風險。",
            "rollback": "回復原 port mapping 前需重新通過 exposure review。",
        },
    },
    {
        "id": "finance_accounting_window",
        "risk": "L2_drift",
        "regex": r"基金池|補償|收入項|碳權|分潤|付款|轉帳|tax|accounting|payment|revenue|carbon",
        "prompt": "偵測到財務/基金池語意；必須切入會計師精準分窗。",
        "safe_next_action": "只產生 accounting review packet，不作付款或正式會計結論。",
        "recommended_solution": "建立會計師審核包，列出憑證 metadata、用途、受益人、工作證據、衝突揭露與待審問題。",
        "impact_assessment": {
            "benefit": "保留合理補償與基金池存活計算，同時避免 AI 作正式會計判斷。",
            "cost": "需要會計師或合格會計專業審核。",
            "risk": "未審核前不得形成付款、稅務或投資結論。",
            "rollback": "回到非正式 proposal，撤回任何未審核輸出。",
        },
    },
    {
        "id": "public_asset_privatization",
        "risk": "L3_metric_hazard",
        "regex": r"公益.*私人|基金池.*私人|private_account|private profit|提款|私人帳戶",
        "prompt": "偵測到公益資產私有化語意；視為 compromised principal 或 polluted intent。",
        "safe_next_action": "阻擋並切回只讀治理窗，寫入去明文化 audit。",
        "recommended_solution": "停止該 session 的敏感動作，要求重新提出公益目的、補償規則、利害關係揭露與人類決策。",
        "impact_assessment": {
            "benefit": "保護公益資產與基金池不被未授權私有化。",
            "cost": "可能延後補償或收入項設計，需要額外審查。",
            "risk": "若不阻擋，會破壞度規不變式與社區信任。",
            "rollback": "撤回該意圖相關 proposal，保留去明文化 audit。",
        },
    },
]

CREDENTIAL_NAME_PATTERNS = [
    re.compile(r".*service.*account.*\.json$", re.IGNORECASE),
    re.compile(r".*credential.*", re.IGNORECASE),
    re.compile(r".*client_secret.*", re.IGNORECASE),
    re.compile(r".*oauth.*", re.IGNORECASE),
    re.compile(r".*key.*\.json$", re.IGNORECASE),
    re.compile(r"^\.env$", re.IGNORECASE),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def is_excluded(path: Path) -> bool:
    try:
        relative = rel(path)
    except ValueError:
        return True
    parts = relative.split("/")
    if parts and parts[0] in {".git", ".venv", "__pycache__", "archive", "data", "keys"}:
        return True
    return any(relative == item or relative.startswith(f"{item}/") for item in EXCLUDED_DIRS)


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT_DIR.rglob("*"):
        if path.is_dir() or is_excluded(path):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return sorted(files)


def scan_patterns() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    compiled = [(item, re.compile(item["regex"], re.IGNORECASE)) for item in PATTERNS]
    for path in iter_text_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            for rule, regex in compiled:
                if regex.search(line):
                    findings.append(
                        {
                            "risk": rule["risk"],
                            "signal_family": rule["id"],
                            "file": rel(path),
                            "line": line_no,
                            "line_sha256": sha256_text(line),
                            "evidence_plaintext_included": False,
                            "proactive_message": rule["prompt"],
                            "recommended_solution": rule["recommended_solution"],
                            "impact_assessment": rule["impact_assessment"],
                            "safe_next_action": rule["safe_next_action"],
                        }
                    )
    return findings


def scan_credential_names() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in ROOT_DIR.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        relative = rel(path)
        if any(pattern.match(name) for pattern in CREDENTIAL_NAME_PATTERNS) or relative.startswith("keys/"):
            findings.append(
                {
                    "risk": "L3_metric_hazard",
                    "signal_family": "secret_risk",
                    "file": relative,
                    "content_read": False,
                    "proactive_message": "偵測到 credential-like 檔名；不得讀取或輸出內容，應移出 repo 或隔離。",
                    "recommended_solution": "將 credential-like 檔移出版本化 repo，保留 `.env.example` 與 secret boundary 文件；本工具只保存檔名風險。",
                    "impact_assessment": {
                        "benefit": "降低 service account、token、private key 被誤讀或提交的風險。",
                        "cost": "需要重新設定本機 secret path 與部署前檢查。",
                        "risk": "移動 secret 前需確認 runtime 不依賴 repo 內路徑。",
                        "rollback": "只回復非敏感路徑設定，不回寫 secret 明文。",
                    },
                    "safe_next_action": "建立 secret boundary 與 .env.example；只保存非敏感路徑狀態。",
                }
            )
    return findings


def docker_ps_scan(timeout: float = 2.0) -> dict[str, Any]:
    command = ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__, "findings": []}
    if proc.returncode != 0:
        return {"available": False, "returncode": proc.returncode, "stderr_stored": False, "findings": []}
    findings: list[dict[str, Any]] = []
    for row in proc.stdout.splitlines():
        parts = row.split("\t")
        if len(parts) < 4:
            continue
        name, image, status, ports = parts[0], parts[1], parts[2], parts[3]
        if "0.0.0.0:" in ports or "[::]:" in ports:
            findings.append(
                {
                    "risk": "L2_drift",
                    "signal_family": "container_exposure",
                    "container": name,
                    "image": image,
                    "status": status,
                    "ports": ports,
                    "proactive_message": "容器 host port 暴露在非 localhost；需確認 VPN/Gateway/ACL 邊界。",
                    "recommended_solution": "將服務收斂到 localhost、VPN-only 或 Gateway；若維持 host 暴露，補 ACL proof 與風險接受紀錄。",
                    "impact_assessment": {
                        "benefit": "降低未授權 UI/API 存取風險。",
                        "cost": "跨節點使用者可能需要透過 VPN 或 Gateway 進入。",
                        "risk": "公開 AI UI 或管理面會增加 session 與資料外洩風險。",
                        "rollback": "恢復原 port 前重新執行 exposure review。",
                    },
                    "safe_next_action": "收斂到 127.0.0.1 或補 allowlist/ACL proof。",
                }
            )
    return {"available": True, "findings": findings}


def aggregate_risk(findings: list[dict[str, Any]]) -> str:
    risks = {item.get("risk") for item in findings}
    if "L3_metric_hazard" in risks:
        return "L3_metric_hazard"
    if "L2_drift" in risks:
        return "L2_drift"
    if "L1_near" in risks:
        return "L1_near"
    return "L0_exact_match"


def build_report(include_docker: bool) -> dict[str, Any]:
    pattern_findings = scan_patterns()
    credential_findings = scan_credential_names()
    docker_result = docker_ps_scan() if include_docker else {"available": False, "skipped": True, "findings": []}
    findings = pattern_findings + credential_findings + docker_result.get("findings", [])
    prompts = [
        "確認本次任務分窗，避免設計/財務/部署/運行混窗。",
        "確認是否接觸 secret、會員明文、Google 私人資料或 Odoo 個資。",
        "確認是否需要 Gateway / Policy / Five Metric Gate。",
        "確認沒有 SSH/SCP/systemctl/docker compose up/down/live execute。",
        "確認容器或服務未非預期暴露在 0.0.0.0。",
        "確認 audit、SHA256 baseline、rollback plan 與 human decision。",
        "財務/基金池/補償/碳權一律切入會計師精準分窗。",
        "公益資產私有化語意一律 L3 阻擋。",
        "本機關機前確認 rescue snapshot / manifest / audit 可接手。",
        "若任務需要敏感資料，降級為只讀或設計窗。",
    ]
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "root": str(ROOT_DIR),
        "mode": "local_readonly_no_secret_output",
        "cloud_api_called": False,
        "container_exec": False,
        "service_mutation": False,
        "secret_file_content_read": False,
        "docker_scan": docker_result,
        "developer_push_policy": {
            "recommendation_required": True,
            "impact_assessment_required": True,
            "single_party_dominance_blocked": True,
        },
        "risk": aggregate_risk(findings),
        "finding_count": len(findings),
        "findings": findings,
        "proactive_developer_prompts": prompts,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--no-docker", action="store_true", help="Skip docker ps scan.")
    args = parser.parse_args()

    report = build_report(include_docker=not args.no_docker)
    write_report(args.output, report)
    if args.stdout:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "schema": report["schema"],
                    "risk": report["risk"],
                    "finding_count": report["finding_count"],
                    "output": str(args.output),
                    "secret_file_content_read": False,
                    "cloud_api_called": False,
                    "service_mutation": False,
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
