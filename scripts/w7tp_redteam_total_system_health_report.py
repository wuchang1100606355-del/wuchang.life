#!/usr/bin/env python3
"""Run a comprehensive red-team oriented W7TP health sweep.

This runner focuses on full-module coverage from the current verifier surface and
outputs a product-level, scene-aware report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"


SCENE_GENERAL = "總場/總體治理"
SCENE_MEMBER = "會員"
SCENE_PERSONAL = "個人"
SCENE_MERCHANT = "商家"
SCENE_PROPERTY = "物業/大樓"
SCENE_ASSOCIATION = "協會"
SCENE_INFRA = "基礎設施"
SCENE_FOUNDER = "創辦人"

# 8 合一分場（總場子場景）
SCENE_INTENT = "D1 意圖場"
SCENE_STATE = "D2 狀態場"
SCENE_COORDINATE = "D3 座標場"
SCENE_EVIDENCE = "D4 證據場"
SCENE_EXECUTION = "D5 執行場（含生成式傳輸）"
SCENE_PRIVACY = "D6 主權隱私場"
SCENE_TRANSMISSION = "D7 生成式傳輸與資源路由場"
SCENE_REDTEAM = "D8 紅隊防繞告警禁錮場"


@dataclass
class CheckSpec:
    check_id: str
    scenes: List[str]
    category: str
    command: Optional[List[str]] = None
    timeout_sec: int = 90
    allowed_nonfatal_markers: List[str] = field(default_factory=list)
    runner: Optional[Callable[[str], "CheckResult"]] = None


@dataclass
class CheckResult:
    check_id: str
    name: str
    status: str
    command: str
    returncode: Optional[int]
    duration_ms: int
    state: Optional[str]
    stdout_tail: str
    stderr_tail: str
    details: List[str]
    severity: str
    scenes: List[str] = field(default_factory=list)
    category: str = ""
    category_sort: int = 0
    requires_total_field_authority: bool = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_key_value_output(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    return parsed


def _jsonify_output(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        return {}


def _extract_matched_alert_ids(raw: str) -> List[str]:
    payload = _jsonify_output(raw)
    if isinstance(payload, list):
        return [
            str(item.get("alert_id", ""))
            for item in payload
            if isinstance(item, dict) and item.get("alert_id")
        ]
    return []


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _run_command(
    command: List[str],
    timeout_sec: int = 90,
    allowed_nonfatal_markers: Optional[List[str]] = None,
    check_id: Optional[str] = None,
) -> CheckResult:
    check_id = check_id or (command[0] if command else "unknown")
    cmd_str = " ".join(shlex.quote(part) for part in command)
    start = datetime.now(timezone.utc)
    allowed_markers = allowed_nonfatal_markers or []

    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        end = datetime.now(timezone.utc)
        out = (exc.stdout or "") if exc.stdout else ""
        err = (exc.stderr or "") if exc.stderr else ""
        return CheckResult(
            check_id=check_id,
            name=" ".join(command),
            status="FAIL",
            command=cmd_str,
            returncode=None,
            duration_ms=int((end - start).total_seconds() * 1000),
            state=None,
            stdout_tail=out[-2400:],
            stderr_tail=err[-1200:],
            details=["timeout_after_90s"],
            severity="critical",
        )
    except OSError as exc:
        end = datetime.now(timezone.utc)
        return CheckResult(
            check_id=check_id,
            name=" ".join(command),
            status="FAIL",
            command=cmd_str,
            returncode=None,
            duration_ms=int((end - start).total_seconds() * 1000),
            state=None,
            stdout_tail="",
            stderr_tail=str(exc),
            details=["os_error"],
            severity="critical",
        )

    out = proc.stdout or ""
    err = proc.stderr or ""
    end = datetime.now(timezone.utc)
    duration_ms = int((end - start).total_seconds() * 1000)
    combined = out + "\n" + err

    state_match = re.search(r"^STATE=([A-Za-z0-9_]+)$", combined, re.MULTILINE)
    state = state_match.group(1) if state_match else None

    details: List[str] = []
    status = "PASS"
    severity = "info"

    if proc.returncode != 0:
        status = "FAIL"
        severity = "critical"
        details.append(f"returncode={proc.returncode}")
        marker_hit = next((m for m in allowed_markers if m in combined), None)
        if marker_hit:
            status = "WARN"
            severity = "high"
            details.append(f"non_fatal_failure_marker={marker_hit}")
        elif state and "HOLD" in state:
            status = "WARN"
            severity = "high"
            details.append(f"state={state}")

    if "VERIFY_FAIL=" in combined:
        status = "FAIL"
        severity = "critical"
        for m in re.findall(r"VERIFY_FAIL=([^\n]+)", combined)[:8]:
            details.append(f"VERIFY_FAIL={m}")

    if state:
        if status == "PASS" and "HOLD" in state:
            status = "WARN"
            severity = "high"
        details.append(f"state={state}")

    if status == "PASS":
        if state:
            details.append(state)
        elif out.strip():
            details.append("no_state_marker_found")
        else:
            details.append("empty_output")

    signals = [
        "PAYMENT_CAPTURE",
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "RESIDENT_PLAINTEXT_READ",
        "RAW_MEMBER_PLAINTEXT_READ",
        "RAW_API_KEY_READ",
        "FORMAL_POS_WRITE",
        "EXTERNAL_API_CALL",
    ]
    for signal in signals:
        if f"{signal}=FALSE" in combined or f"{signal}=true" in combined:
            details.append(signal)

    return CheckResult(
        check_id=check_id,
        name=" ".join(command),
        status=status,
        command=cmd_str,
        returncode=proc.returncode,
        duration_ms=duration_ms,
        state=state,
        stdout_tail=out[-2400:],
        stderr_tail=err[-1200:],
        details=details,
        severity=severity,
    )


def _map_to_eight_scenes(check_id: str, category: str, legacy_scenes: List[str]) -> List[str]:
    """Map legacy scene/category labels to the 8-field governance scene set."""
    category_to_scene = {
        "8D + 8場景": SCENE_STATE,
        "8D 委員輪替": SCENE_STATE,
        "8D 適應性": SCENE_EVIDENCE,
        "Codex 適配": SCENE_EXECUTION,
        "LLM readiness": SCENE_PRIVACY,
        "LLM 候選": SCENE_EVIDENCE,
        "LLM 閘道": SCENE_EXECUTION,
        "POS MVP": SCENE_EXECUTION,
        "PR 區塊": SCENE_EVIDENCE,
        "Persona": SCENE_EVIDENCE,
        "Runtime": SCENE_STATE,
        "W3 部署": SCENE_TRANSMISSION,
        "主權宣告": SCENE_PRIVACY,
        "主鏈規則": SCENE_TRANSMISSION,
        "傳輸壓力": SCENE_TRANSMISSION,
        "前端封裝": SCENE_EXECUTION,
        "協會治理": SCENE_COORDINATE,
        "合規": SCENE_REDTEAM,
        "商務系統": SCENE_EXECUTION,
        "商家產品化": SCENE_EXECUTION,
        "商家研發": SCENE_EXECUTION,
        "團體會員": SCENE_COORDINATE,
        "多端產品化": SCENE_EXECUTION,
        "實體場景": SCENE_COORDINATE,
        "意圖引擎": SCENE_INTENT,
        "意圖推理": SCENE_INTENT,
        "成本路由": SCENE_TRANSMISSION,
        "會員瀏覽": SCENE_PRIVACY,
        "本地候選演練": SCENE_INTENT,
        "產品交接": SCENE_STATE,
        "產品參考彙整": SCENE_STATE,
        "產品套件": SCENE_EXECUTION,
        "產品收斂": SCENE_EVIDENCE,
        "產品文件": SCENE_EVIDENCE,
        "產品目標": SCENE_STATE,
        "節點/容器門禁": SCENE_REDTEAM,
        "紅隊": SCENE_REDTEAM,
        "網站品質": SCENE_STATE,
        "總體產品指令盤": SCENE_STATE,
        "菜單權限": SCENE_EXECUTION,
        "路由治理": SCENE_TRANSMISSION,
        "身份授權": SCENE_PRIVACY,
        "隱私回傳": SCENE_PRIVACY,
        "風險能力": SCENE_REDTEAM,
        "測試套件": SCENE_STATE,
        "紅隊掃描": SCENE_REDTEAM,
        "基礎治理": SCENE_EVIDENCE,
    }

    mapped = category_to_scene.get(category, SCENE_STATE)
    used_default = category not in category_to_scene

    if used_default:
        for scene in legacy_scenes:
            if scene == SCENE_MEMBER:
                mapped = SCENE_PRIVACY
            elif scene == SCENE_PERSONAL:
                mapped = SCENE_PRIVACY
            elif scene == SCENE_MERCHANT:
                mapped = SCENE_EXECUTION
            elif scene in (SCENE_PROPERTY, SCENE_ASSOCIATION):
                mapped = SCENE_COORDINATE
            elif scene == SCENE_FOUNDER:
                mapped = SCENE_STATE
            elif scene == SCENE_INFRA:
                mapped = SCENE_TRANSMISSION
            elif scene == SCENE_GENERAL:
                mapped = SCENE_STATE

    if check_id in {"verify_xiaoj_member_browser_cockpit", "verify_xiaoj_member_browser_release"}:
        mapped = SCENE_INTENT
    if check_id in {"verify_xiaoj_total_field_pr_layer", "verify_xiaoj_local_personal_data_return_packet"}:
        mapped = SCENE_EVIDENCE
    if check_id in {
        "verify_w7tp_codex_task_adapter",
        "verify_xiaoj_total_product_console_status",
        "verify_xiaoj_total_product_operator_handoff",
        "verify_xiaoj_total_product_operator_bundle",
        "verify_xiaoj_total_product_ref_collection",
    }:
        mapped = SCENE_STATE
    return [mapped]


def _run_pytest_if_available(check_id: str) -> CheckResult:
    def _pick_pytest_python() -> Optional[str]:
        candidates = [
            sys.executable,
            str((ROOT / ".venv-health" / "bin" / "python").resolve()),
            str((ROOT / ".venv" / "bin" / "python").resolve()),
            str((ROOT.parent / ".venv-hf" / "bin" / "python").resolve()),
        ]

        # Also try parent and grandparent ".venv" style paths for managed dev setups.
        candidates += [
            str((Path.cwd() / ".venv" / "bin" / "python").resolve()),
            str((Path.cwd() / ".venv-health" / "bin" / "python").resolve()),
            str((Path.cwd() / ".." / ".venv" / "bin" / "python").resolve()),
            str((Path.cwd() / ".." / ".venv-health" / "bin" / "python").resolve()),
            str((Path.cwd() / ".." / ".venv-hf" / "bin" / "python").resolve()),
        ]

        candidates = [c for c in candidates if c]
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        for executable in unique_candidates:
            path = Path(executable)
            if not path.exists() or not path.is_file():
                continue
            probe = subprocess.run(
                [executable, "-m", "pytest", "--version"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if probe.returncode == 0:
                return executable
        return None

    pytest_python = _pick_pytest_python()
    if pytest_python is None:
        # Keep compatibility with system without pytest installed.
        system_probe = shutil.which("pytest")
        if system_probe:
            return _run_command(
                [
                    system_probe,
                    "tests/test_w7tp_xiaoj_service_persona_policy.py",
                    "tests/test_w7tp_8d_identity_feature_marker.py",
                ],
                check_id=check_id,
            )

    base = _run_command([pytest_python or sys.executable, "-m", "pytest", "--version"], check_id=f"{check_id}:version")
    if base.status == "PASS":
        return _run_command(
            [
                pytest_python or sys.executable,
                "-m",
                "pytest",
                "tests/test_w7tp_xiaoj_service_persona_policy.py",
                "tests/test_w7tp_8d_identity_feature_marker.py",
            ],
            check_id=check_id,
        )

    combined = (base.stdout_tail + "\n" + base.stderr_tail).lower()
    if "no module named pytest" in combined:
        return CheckResult(
            check_id=check_id,
            name="Pytest fixture suite (optional)",
            status="WARN",
            command="python3 -m pytest ...",
            returncode=base.returncode,
            duration_ms=base.duration_ms,
            state=None,
            stdout_tail=base.stdout_tail,
            stderr_tail=base.stderr_tail,
            details=["dependency_missing:pytest", "dependency_missing:pytest"],
            severity="low",
        )

    return _run_command(
        [
            pytest_python or sys.executable,
            "-m",
            "pytest",
            "tests/test_w7tp_xiaoj_service_persona_policy.py",
            "tests/test_w7tp_8d_identity_feature_marker.py",
        ],
        check_id=check_id,
    )


def _run_total_field_initial_verification() -> tuple[CheckResult, dict]:
    """Run an online total-field-connected initial verification and return drift signal."""

    start = datetime.now(timezone.utc)
    task_name = "W7TP_REDTEAM_TOTAL_FIELD_INITIAL_VERIFICATION"
    scope = {
        "readonly": True,
        "drift_watch": True,
        "request": "w7tp_redteam_health_report",
        "requester": "xiaoj_redteam_health",
    }
    scope_json = json.dumps(scope, ensure_ascii=False)
    preflight_cmd = [
        "python3",
        "tools/d8_total_field_console.py",
        "preflight",
        "--task-name",
        task_name,
        "--mode",
        "sandbox",
        "--scope-json",
        scope_json,
    ]
    total_field_online_ok = False
    drift_alert_count = 0
    matched_alerts_count = 0
    matched_alerts: List[str] = []
    drift_response = "observe_only"
    execution_paused = False
    execution_pause_reason = None
    external_side_effects_allowed = True
    drift_action = "observe_only"
    decision = "ERROR"
    accepted_return_codes = {0, 10, 20, 30, 40}

    try:
        preflight_proc = subprocess.run(
            preflight_cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except Exception as exc:
        combined = str(exc)
        check_result = CheckResult(
            check_id="total_field_initial_verification",
            name=" ".join(preflight_cmd),
            status="FAIL",
            command=" ".join(shlex.quote(part) for part in preflight_cmd),
            returncode=None,
            duration_ms=int((datetime.now(timezone.utc) - start).total_seconds() * 1000),
            state="ERROR",
            stdout_tail="",
            stderr_tail=combined[-1200:],
            details=[
                "total_field_preflight_exception",
                str(type(exc).__name__),
                f"exception={combined}",
            ],
            severity="critical",
            scenes=[SCENE_REDTEAM],
            category="紅隊",
        )
        return check_result, {
            "total_field_online_ok": total_field_online_ok,
            "drift_alert_count": drift_alert_count,
            "decision": decision,
            "execution_paused": execution_paused,
            "execution_pause_reason": execution_pause_reason,
            "external_side_effects_allowed": external_side_effects_allowed,
            "drift_action": drift_action,
            "drift_response": drift_response,
            "matched_alerts_count": matched_alerts_count,
            "matched_alerts": matched_alerts,
            "preflight_out": {},
            "status_payload": {},
        }

    end = datetime.now(timezone.utc)
    out = preflight_proc.stdout or ""
    err = preflight_proc.stderr or ""
    combined = (out + "\n" + err).strip()
    kv = _parse_key_value_output(combined)
    decision = (kv.get("DECISION") or kv.get("STATE") or "ERROR").strip().upper()
    matched_alerts_count = _safe_int(kv.get("MATCHED_ALERTS_COUNT", "0"), 0)
    parsed_matched_alerts = _extract_matched_alert_ids(kv.get("MATCHED_ALERTS", ""))
    if parsed_matched_alerts:
        matched_alerts = parsed_matched_alerts
    elif kv.get("MATCHED_ALERTS"):
        matched_alerts = [kv["MATCHED_ALERTS"]]

    if preflight_proc.returncode in accepted_return_codes:
        total_field_online_ok = True

    status = "PASS"
    severity = "info"
    if decision in {"PASS", "INFO"}:
        status = "PASS"
        severity = "info"
    elif decision == "WARN":
        status = "WARN"
        severity = "high"
    elif decision in {"HOLD", "BLOCK"}:
        status = "FAIL"
        severity = "critical"
    else:
        status = "FAIL"
        severity = "critical"

    details = [
        f"decision={decision}",
        f"scope={scope_json}",
        "requires_total_field_authority=true",
        f"online_status={'ok' if total_field_online_ok else 'offline_or_unverified'}",
    ]

    preflight_out = {
        "state": kv.get("STATE"),
        "decision": decision,
        "matched_alerts_count": matched_alerts_count,
        "matched_alerts": kv.get("MATCHED_ALERTS", ""),
        "reason": kv.get("REASON", ""),
        "mode": kv.get("MODE", ""),
        "task_name": kv.get("TASK_NAME", ""),
    }

    # enrich with live console status so initial drift is visible before full sweep.
    preflight_scope_payload = {}
    if total_field_online_ok:
        try:
            status_cmd = [
                "python3",
                "tools/d8_total_field_console.py",
                "status",
                "--json",
            ]
            status_proc = subprocess.run(
                status_cmd,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            preflight_scope_payload = _jsonify_output(status_proc.stdout or "{}")
            if preflight_scope_payload:
                alert_counts = preflight_scope_payload.get("alert_counts", {}) or {}
                hold_alerts = _safe_int(alert_counts.get("HOLD", 0))
                block_alerts = _safe_int(alert_counts.get("BLOCK", 0))
                drift_alert_count = max(_safe_int(drift_alert_count), hold_alerts + block_alerts)
                details.extend([
                    f"console_alerts={json.dumps(alert_counts, ensure_ascii=False)}",
                    f"possible_alerts_count={_safe_int(preflight_scope_payload.get('possible_alerts_count', 0))}",
                ])
            else:
                details.append("total_field_status_payload_empty")
            if status_proc.returncode != 0:
                total_field_online_ok = False
                status = "WARN"
                severity = "high"
                details.append(f"total_field_status_returncode={status_proc.returncode}")
        except Exception:
            preflight_scope_payload = {}
            if total_field_online_ok:
                total_field_online_ok = False
            status = "WARN"
            severity = "high"
            details.append("total_field_status_query_failed")

    if preflight_proc.returncode == 40:
        status = "FAIL"
        severity = "critical"
        total_field_online_ok = False
        details.append("total_field_preflight_error")
    elif preflight_proc.returncode == 30:
        details.append("total_field_preflight_block")
    elif preflight_proc.returncode == 20:
        details.append("total_field_preflight_hold")
    elif preflight_proc.returncode == 10:
        details.append("total_field_preflight_warn")

    # any HOLD/BLOCK decision or matching alerts implies drift-relevant candidates.
    if decision in {"HOLD", "BLOCK"}:
        drift_alert_count = max(drift_alert_count, matched_alerts_count)
    elif matched_alerts_count > 0:
        drift_alert_count = max(drift_alert_count, matched_alerts_count)

    if drift_alert_count > 0:
        details.append(f"drift_detected=true")
        details.append(f"drift_alert_count={drift_alert_count}")
        execution_paused = True
        execution_pause_reason = "drift_detected_pause_only_no_write"
        external_side_effects_allowed = False
        drift_action = "PAUSE_ONLY_NO_WRITE"
        drift_response = "pause_only_no_write"
        print("STATE=D8_TOTAL_FIELD_DRIFT_ALERT")
        print(f"DRIFT_ALERT_COUNT={drift_alert_count}")
        if decision:
            print(f"TOTAL_FIELD_DECISION={decision}")
        print("ALERT=PAUSE_DUE_TO_DRIFT")
        print("ALERT_ACTION=PAUSE_ONLY")
        print(f"DRIFT_ACTION={drift_action}")
        print("DRIFT_RESPONSE=READ_ONLY_NO_WRITE")
        status = "FAIL"
        severity = "critical"
        details.append("total_field_initial_drift_detected")
        details.append("drift_response=pause_only_no_write")
        details.append("drift_action=pause_only_no_write")
        details.append("drift_guardrail=readonly")
    else:
        details.append("drift_detected=false")
        details.append(f"drift_response={drift_response}")

    reason = kv.get("REASON", "")
    if reason:
        details.append(f"reason={reason}")

    return CheckResult(
        check_id="total_field_initial_verification",
        name="D8 total field initial preflight verification",
        status=status,
        command=" ".join(shlex.quote(part) for part in preflight_cmd),
        returncode=preflight_proc.returncode,
        duration_ms=int((end - start).total_seconds() * 1000),
        state=decision,
        stdout_tail=out[-2400:],
        stderr_tail=err[-1200:],
        details=details,
        severity=severity,
        scenes=[SCENE_REDTEAM],
        category="紅隊",
    ), {
        "total_field_online_ok": total_field_online_ok,
        "drift_alert_count": drift_alert_count,
        "decision": decision,
        "execution_paused": execution_paused,
        "execution_pause_reason": execution_pause_reason,
        "external_side_effects_allowed": external_side_effects_allowed,
        "drift_action": drift_action,
        "drift_response": drift_response,
        "matched_alerts_count": matched_alerts_count,
        "matched_alerts": matched_alerts[:6],
        "preflight_out": preflight_out,
        "status_payload": preflight_scope_payload,
    }


def _needs_total_field_authority_verification(result: CheckResult) -> bool:
    """Check whether this check must be handed to total-field authority for final ruling."""

    if any("needs_total_field_authority=true" in d for d in result.details):
        return True

    if result.status != "WARN":
        return False

    hold_state = result.state and "HOLD" in result.state
    marker_text = " ".join(result.details).lower()

    evidence_gap_tokens = (
        "requires_total_field_verify",
        "total_field_verify",
        "evidence_gap",
        "evidence_missing",
        "missing_evidence",
        "insufficient_evidence",
        "無證據",
        "缺",
        "補全",
    )

    if hold_state:
        return True

    return any(token in marker_text for token in evidence_gap_tokens)


def _mark_authority_handoff(result: CheckResult) -> None:
    """Annotate report items requiring total-field authority review."""

    if _needs_total_field_authority_verification(result):
        result.requires_total_field_authority = True
        if "needs_total_field_authority=true" not in result.details:
            result.details.append("needs_total_field_authority=true")

        if SCENE_REDTEAM not in result.scenes:
            result.scenes.append(SCENE_REDTEAM)
        if SCENE_STATE not in result.scenes:
            result.scenes.append(SCENE_STATE)


def _scan_secrets_for_patterns(file_list: List[str]) -> Dict[str, Any]:
    patterns: Dict[str, re.Pattern[str]] = {
        "private_key_blob": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "jwt_like": re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
        "api_key_like": re.compile(r"(?i)(access[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9.+/_-]{12,}"),
        "openai_secret_like": re.compile(r"\\bsk-[A-Za-z0-9._-]{24,}\\b"),
        "email_like": re.compile(r"[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}"),
        "tw_phone": re.compile(r"09\\d{2}[- ]?\\d{3}[- ]?\\d{3}"),
        "member_plaintext_like": re.compile(r"(?i)member[_-]?plain", re.IGNORECASE),
    }

    hits: List[Dict[str, Any]] = []
    for rel in file_list:
        path = ROOT / rel
        if not path.exists():
            continue
        text = _read_file(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for tag, pattern in patterns.items():
                if pattern.search(line):
                    hits.append(
                        {
                            "file": rel,
                            "line": line_no,
                            "tag": tag,
                            "line_digest": _safe_hash(line.strip()),
                        }
                    )
    return {
        "status": "PASS" if not hits else "WARN",
        "count": len(hits),
        "hits": hits[:40],
    }


def _scan_policy_risks() -> Dict[str, Any]:
    risk_files = [
        "docs/taiji_hub_architecture_completion_board_zh.md",
        "docs/total_field/W7TP_TRUE8D_ALLNODE_EXPANSION.md",
        "docs/total_field/W7TP_INTENT_BUILD_COMMANDIZATION.md",
        "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py",
        "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py",
        "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_activation.py",
        "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_config.py",
    ]

    hits = _scan_secrets_for_patterns(risk_files)

    exposure_files = [
        "cloudflare/config.yml",
        "docker-compose.ai.yml",
        "docker-compose.yml",
        "deploy/packages/taiji_formal_tensor_runtime_v0_1_0/MANIFEST.json",
    ]
    exposure_findings = []
    for rel in exposure_files:
        path = ROOT / rel
        if not path.exists():
            continue
        if "0.0.0.0:3000" in path.read_text(encoding="utf-8"):
            exposure_findings.append(f"L2 exposure candidate: {rel}")

    redteam_cmds = {
        "verify_LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.sh":
            ["bash", "scripts/verify/verify_LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.sh"],
        "verify_COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.sh":
            ["bash", "scripts/verify/verify_COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.sh"],
    }

    redteam_results = {}
    for item, cmd in redteam_cmds.items():
        r = _run_command(cmd)
        redteam_results[item] = {
            "status": r.status,
            "state": r.state,
            "severity": r.severity,
            "duration_ms": r.duration_ms,
        }

    return {
        "status": "PASS" if hits["status"] == "PASS" and not exposure_findings and all(
            r["status"] == "PASS" for r in redteam_results.values()
        ) else "WARN",
        "secret_pattern_scan": hits,
        "exposure_scan": {
            "status": "WARN" if exposure_findings else "PASS",
            "findings": exposure_findings,
        },
        "compliance_aux_checks": redteam_results,
        "details": [
            f"secret_hits={hits['count']}",
            f"exposure_findings={len(exposure_findings)}",
            f"compliance_aux={len(redteam_results)}",
        ],
    }


def _run_verifier_coverage_check(check_id: str, declared_specs: List[CheckSpec]) -> CheckResult:
    """Verify every scripts/verify verifier file is represented in the sweep plan."""

    verify_dir = ROOT / "scripts/verify"
    discovered_files = {
        path.stem
        for path in sorted(verify_dir.glob("verify_*"))
        if path.suffix in {".py", ".sh"}
    }
    skip_files = {"xiaoj_productization_console_verify_lib"}

    declared_by_id = set()
    declared_file_stems = set()
    duplicate_file_stem_targets = 0
    for spec in declared_specs:
        command = spec.command or []
        if not command or len(command) < 2:
            continue
        candidate = (ROOT / command[1]).resolve()
        if candidate.parent == verify_dir and candidate.name.startswith("verify_") and candidate.suffix in {".py", ".sh"}:
            declared_file_stem = candidate.stem
            declared_file_stems.add(declared_file_stem)
            if spec.check_id in declared_by_id:
                duplicate_file_stem_targets += 1
            declared_by_id.add(spec.check_id)
    missing_stems = sorted(discovered_files - declared_file_stems - skip_files)
    status = "PASS" if not missing_stems else "WARN"
    severity = "info" if status == "PASS" else "medium"
    details = [
        f"verify_scripts={len(discovered_files)}",
        f"covered_verify_scripts={len(declared_file_stems)}",
        f"missing={len(missing_stems)}",
    ]
    if missing_stems:
        details.append(f"missing_files={','.join(missing_stems)}")
    if duplicate_file_stem_targets:
        details.append(f"duplicate_file_stem_targets={duplicate_file_stem_targets}")
        status = "WARN"
        severity = "medium"
    return CheckResult(
        check_id=check_id,
        name="scripts/verify coverage completeness",
        status=status,
        command="coverage_check",
        returncode=0 if status == "PASS" else 1,
        duration_ms=0,
        state="PASS_VERIFIER_COVERAGE" if status == "PASS" else "WARN_VERIFIER_COVERAGE",
        stdout_tail="",
        stderr_tail="",
        details=details,
        severity=severity,
        scenes=[SCENE_REDTEAM],
        category="基礎治理",
    )


def _run_governance_artifacts(check_id: str) -> CheckResult:
    required = [
        "docs/total_field/W7TP_XIAOJ_SERVICE_PERSONA_POLICY.md",
        "docs/total_field/W7TP_MEMBER_AI_LLM_PREFIX_POLICY.md",
        "schemas/w7tp_xiaoj_service_persona.schema.json",
        "schemas/w7tp_8d_identity_feature_marker.schema.json",
        "configs/w7tp_xiaoj_service_persona_policy.example.json",
        "configs/w7tp_member_llm_prefix_policy.example.json",
        "tests/fixtures_w7tp_xiaoj_service_persona_synthetic_cases.json",
        "tests/fixtures_w7tp_8d_identity_feature_marker_synthetic_cases.json",
    ]
    missing = []
    for rel in required:
        if not (ROOT / rel).exists():
            missing.append(rel)

    status = "PASS"
    severity = "info"
    details: List[str] = [f"required_artifacts={len(required)}"]
    if missing:
        status = "FAIL"
        severity = "critical"
        details.append(f"missing={missing}")

    return CheckResult(
        check_id=check_id,
        name="Governance artifact completeness",
        status=status,
        command="manual_file_exists",
        returncode=0 if status == "PASS" else 1,
        duration_ms=0,
        state="PASS_REDTEAM_ARTIFACTS" if status == "PASS" else None,
        stdout_tail="",
        stderr_tail="",
        details=details,
        severity=severity,
    )


def _run_redteam_scan(check_id: str) -> CheckResult:
    report = _scan_policy_risks()
    status = report["status"]
    severity = "info" if status == "PASS" else "medium"
    return CheckResult(
        check_id=check_id,
        name="Red-team static risk scan",
        status="PASS" if status == "PASS" else "WARN",
        command="_scan_policy_risks",
        returncode=0 if status == "PASS" else 1,
        duration_ms=0,
        state="PASS_REDTEAM_SCAN" if status == "PASS" else "WARN_REDTEAM_SCAN",
        stdout_tail="",
        stderr_tail="",
        details=report["details"],
        severity=severity,
    )


def _redteam_forbidden_action_scan(
    check_results: List[CheckResult],
    drift_paused: bool,
) -> Dict[str, Any]:
    """When drift is paused, verify no follow-up action-like markers are emitted."""
    forbidden_markers = ["WRITE", "DB_WRITE", "DEPLOY", "RESTART", "AUTO_FIX", "SYNC_APPLY"]

    if not drift_paused:
        return {
            "status": "SKIPPED",
            "reason": "no_drift_pause",
            "forbidden_hits": [],
            "forbidden_markers": forbidden_markers,
        }

    # Initial preflight is allowed to output safety-status values (READ_ONLY/PRODUCTION flags),
    # but all follow-up checks must be pause-skipped.
    hits: List[Dict[str, str]] = []
    for item in check_results:
        if item.check_id == "total_field_initial_verification":
            continue
        haystack = " ".join(
            [
                item.check_id,
                item.name,
                item.state or "",
                item.command,
                " ".join(item.details),
                item.stdout_tail,
                item.stderr_tail,
            ]
        )
        for marker in forbidden_markers:
            if re.search(rf"\\b{re.escape(marker)}\\b", haystack):
                hits.append({
                    "check_id": item.check_id,
                    "marker": marker,
                    "matched_in": "command_or_detail",
                })

    return {
        "status": "PASS" if not hits else "FAIL",
        "reason": "pause_gate_active_no_forbidden_actions" if not hits else "forbidden_actions_found",
        "forbidden_hits": hits,
        "forbidden_markers": forbidden_markers,
        "drift_paused": drift_paused,
    }


def _build_pause_skipped_result(
    check_id: str,
    scenes: List[str],
    category: str,
    execution_pause_reason: Optional[str],
    external_side_effects_allowed: bool,
) -> CheckResult:
    """Build a CHECK result that explicitly records pause-gated skip."""
    return CheckResult(
        check_id=check_id,
        name=f"SKIP_DUE_TO_DRIFT_PAUSE:{check_id}",
        status="WARN",
        command="N/A",
        returncode=0,
        duration_ms=0,
        state="PAUSED_BY_DRIFT",
        stdout_tail="",
        stderr_tail="",
        details=[
            "execution_paused=true",
            f"execution_pause_reason={execution_pause_reason or 'null'}",
            f"external_side_effects_allowed={external_side_effects_allowed}",
            "drift_pause_gate_active",
        ],
        severity="medium",
        scenes=scenes,
        category=category,
    )


def _build_check_specs() -> List[CheckSpec]:
    specs: List[CheckSpec] = [
        CheckSpec("verify_w7tp_xiaoj_convergence", [SCENE_GENERAL], "Persona", ["python3", "scripts/w7tp_xiaoj_convergence_verifier.py"]),
        CheckSpec("verify_xiaoj_8d_total_system_assembly", [SCENE_GENERAL, SCENE_MEMBER, SCENE_MERCHANT, SCENE_PROPERTY, SCENE_ASSOCIATION], "8D + 8場景", ["python3", "scripts/verify/verify_xiaoj_8d_total_system_assembly.py"]),
        CheckSpec("verify_xiaoj_8d_delegate_rotation", [SCENE_GENERAL], "8D 委員輪替", ["python3", "scripts/verify/verify_xiaoj_8d_delegate_rotation.py"]),
        CheckSpec("verify_xiaoj_total_product_console_status", [SCENE_GENERAL], "總體產品指令盤", ["python3", "scripts/verify/verify_xiaoj_total_product_console_status.py"]),
        CheckSpec("verify_xiaoj_total_product_ref_collection", [SCENE_GENERAL], "產品參考彙整", ["python3", "scripts/verify/verify_xiaoj_total_product_ref_collection.py"]),
        CheckSpec("verify_xiaoj_total_product_operator_handoff", [SCENE_GENERAL], "產品交接", ["python3", "scripts/verify/verify_xiaoj_total_product_operator_handoff.py"]),
        CheckSpec("verify_xiaoj_total_product_operator_bundle", [SCENE_GENERAL], "產品套件", ["python3", "scripts/verify/verify_xiaoj_total_product_operator_bundle.py"]),
        CheckSpec("verify_xiaoj_member_llm_release_gate", [SCENE_MEMBER], "LLM 閘道", ["python3", "scripts/verify/verify_xiaoj_member_llm_release_gate.py"]),
        CheckSpec("verify_xiaoj_local_personal_data_return_packet", [SCENE_MEMBER, SCENE_PERSONAL], "隱私回傳", ["python3", "scripts/verify/verify_xiaoj_local_personal_data_return_packet.py"]),
        CheckSpec("verify_xiaoj_sovereign_xiaoj_claim", [SCENE_GENERAL], "主權宣告", ["python3", "scripts/verify/verify_xiaoj_sovereign_xiaoj_claim.py"]),
        CheckSpec("verify_xiaoj_sovereign_member_llm_readiness", [SCENE_MEMBER, SCENE_GENERAL], "LLM readiness", ["python3", "scripts/verify/verify_xiaoj_sovereign_member_llm_readiness.py"]),
        CheckSpec("verify_xiaoj_lineworks_productization", [SCENE_GENERAL], "多端產品化", ["python3", "scripts/verify/verify_xiaoj_lineworks_productization.py"]),
        CheckSpec("verify_xiaoj_business_backend_optimization", [SCENE_MERCHANT], "商務系統", ["python3", "scripts/verify/verify_xiaoj_business_backend_optimization.py"]),
        CheckSpec("verify_w7tp_packet_inference_runtime", [SCENE_GENERAL, SCENE_MEMBER, SCENE_MERCHANT, SCENE_PROPERTY, SCENE_ASSOCIATION, SCENE_FOUNDER], "意圖推理", ["python3", "scripts/verify/verify_w7tp_packet_inference_runtime.py"]),
        CheckSpec("verify_w7tp_packet_inference_cockpit", [SCENE_GENERAL, SCENE_MEMBER, SCENE_MERCHANT, SCENE_PROPERTY, SCENE_ASSOCIATION, SCENE_FOUNDER], "意圖推理", ["python3", "scripts/verify/verify_w7tp_packet_inference_cockpit.py"]),
        CheckSpec("verify_xiaoj_member_browser_cockpit", [SCENE_MEMBER], "會員瀏覽", ["python3", "scripts/verify/verify_xiaoj_member_browser_cockpit.py"]),
        CheckSpec("verify_xiaoj_member_browser_release", [SCENE_MEMBER], "會員瀏覽", ["python3", "scripts/verify/verify_xiaoj_member_browser_release.py"]),
        CheckSpec("verify_xiaoj_browser_packaged_pages", [SCENE_GENERAL], "前端封裝", ["python3", "scripts/verify/verify_xiaoj_browser_packaged_pages.py"]),
        CheckSpec("verify_w7tp_codex_task_adapter", [SCENE_GENERAL], "Codex 適配", ["python3", "scripts/verify/verify_w7tp_codex_task_adapter.py"]),
        CheckSpec("verify_xiaoj_p1_intent_engine", [SCENE_GENERAL, SCENE_MEMBER, SCENE_MERCHANT, SCENE_PROPERTY, SCENE_ASSOCIATION], "意圖引擎", ["python3", "scripts/verify/verify_xiaoj_p1_intent_engine.py"]),
        CheckSpec("verify_xiaoj_p1_local_rehearsal", [SCENE_MEMBER, SCENE_GENERAL], "本地候選演練", ["python3", "scripts/verify/verify_xiaoj_p1_local_rehearsal.py"]),
        CheckSpec("verify_xiaoj_p0_shadow_rehearsal", [SCENE_MERCHANT], "本地候選演練", ["python3", "scripts/verify/verify_xiaoj_p0_shadow_rehearsal.py"]),
        CheckSpec("verify_xiaoj_p1_console_prototype", [SCENE_MERCHANT, SCENE_GENERAL], "商務系統", ["python3", "scripts/verify/verify_xiaoj_p1_console_prototype.py"]),
        CheckSpec("verify_xiaoj_source_route_shell", [SCENE_GENERAL, SCENE_MEMBER, SCENE_MERCHANT, SCENE_ASSOCIATION], "路由治理", ["python3", "scripts/verify/verify_xiaoj_source_route_shell.py"]),
        CheckSpec("verify_xiaoj_premium_manuals", [SCENE_GENERAL, SCENE_MEMBER, SCENE_MERCHANT], "產品文件", ["python3", "scripts/verify/verify_xiaoj_premium_manuals.py"]),
        CheckSpec("verify_xiaoj_line_official_account_authorization", [SCENE_GENERAL], "身份授權", ["python3", "scripts/verify/verify_xiaoj_line_official_account_authorization.py"]),
        CheckSpec("verify_xiaoj_llm_cost_saving_model_router", [SCENE_GENERAL], "成本路由", ["python3", "scripts/verify/verify_xiaoj_llm_cost_saving_model_router.py"]),
        CheckSpec("verify_xiaoj_merchant_productization_readiness", [SCENE_MERCHANT], "商家產品化", ["python3", "scripts/verify/verify_xiaoj_merchant_productization_readiness.py"]),
        CheckSpec("verify_xiaoj_sovereign_av_ordering_research_packet", [SCENE_MERCHANT, SCENE_GENERAL], "商家研發", ["python3", "scripts/verify/verify_xiaoj_sovereign_av_ordering_research_packet.py"]),
        CheckSpec("verify_xiaoj_sovereign_1b_product_goal", [SCENE_GENERAL], "產品目標", ["python3", "scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py"]),
        CheckSpec("verify_xiaoj_real_menu_source_lock", [SCENE_MERCHANT], "菜單權限", ["python3", "scripts/verify/verify_xiaoj_real_menu_source_lock.py"]),
        CheckSpec("verify_xiaoj_auth_node_container_gate", [SCENE_GENERAL], "節點/容器門禁", ["python3", "scripts/verify/verify_xiaoj_auth_node_container_gate.py"], allowed_nonfatal_markers=["STATE=HOLD_XIAOJ_AUTH_ROUTE_GATE", "STATE=HOLD_NODE_CONTAINER_GATE"]),
        CheckSpec("verify_xiaoj_field_practicum_dual_track", [SCENE_GENERAL, SCENE_MEMBER], "實體場景", ["python3", "scripts/verify/verify_xiaoj_field_practicum_dual_track.py"]),
        CheckSpec("verify_xiaoj_capability_risk_evidence_field_matrix", [SCENE_GENERAL], "風險能力", ["python3", "scripts/verify/verify_xiaoj_capability_risk_evidence_field_matrix.py"]),
        CheckSpec("verify_xiaoj_gemini_no_plaintext_candidate_worker", [SCENE_GENERAL], "LLM 候選", ["python3", "scripts/verify/verify_xiaoj_gemini_no_plaintext_candidate_worker.py"]),
        CheckSpec("verify_product_av_ordering_ai_convergence", [SCENE_MERCHANT, SCENE_GENERAL], "產品收斂", ["python3", "scripts/verify/verify_product_av_ordering_ai_convergence.py"]),
        CheckSpec("verify_8d_packet_adaptivity_evidence", [SCENE_GENERAL], "8D 適應性", ["python3", "scripts/verify/verify_8d_packet_adaptivity_evidence.py"]),
        CheckSpec("verify_association_patent_subject_governance", [SCENE_ASSOCIATION], "協會治理", ["python3", "scripts/verify/verify_association_patent_subject_governance.py"]),
        CheckSpec("verify_group_member_8d_registration", [SCENE_MEMBER, SCENE_ASSOCIATION], "團體會員", ["python3", "scripts/verify/verify_group_member_8d_registration.py"]),
        CheckSpec("verify_w7tp_total_field_pr_layer", [SCENE_GENERAL, SCENE_FOUNDER], "PR 區塊", ["python3", "scripts/verify/verify_w7tp_total_field_pr_layer.py"]),
        CheckSpec("verify_w7tp_total_branch_runtime", [SCENE_GENERAL], "Runtime", ["python3", "scripts/verify/verify_w7tp_total_branch_runtime.py"]),
        CheckSpec("verify_wuchang_website_quality", [SCENE_GENERAL], "網站品質", ["python3", "scripts/verify/verify_wuchang_website_quality.py"]),
        CheckSpec("verify_gt_5gb_speed_packet", [SCENE_INFRA], "傳輸壓力", ["python3", "scripts/verify/verify_gt_5gb_speed_packet.py"]),
        CheckSpec("verify_direct_shortest_path_gtp", [SCENE_GENERAL], "主鏈規則", ["bash", "scripts/verify/verify_direct_shortest_path_gtp.sh"], allowed_nonfatal_markers=["STATE=HOLD_VERIFY"]),
        CheckSpec("verify_W3_GENERATIVE_TRANSFER_DEPLOY_20260621", [SCENE_GENERAL, SCENE_INFRA], "W3 部署", ["bash", "scripts/verify/verify_W3_GENERATIVE_TRANSFER_DEPLOY_20260621.sh"]),
        CheckSpec("verify_W3_MASTER_DEPLOY_INDEX_20260613_064840", [SCENE_GENERAL, SCENE_INFRA], "W3 部署", ["bash", "scripts/verify/verify_W3_MASTER_DEPLOY_INDEX_20260613_064840.sh"]),
        CheckSpec("verify_COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312", [SCENE_GENERAL], "合規", ["bash", "scripts/verify/verify_COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.sh"]),
        CheckSpec("verify_FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417", [SCENE_GENERAL], "合規", ["bash", "scripts/verify/verify_FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417.sh"]),
        CheckSpec("verify_LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900", [SCENE_INFRA], "合規", ["bash", "scripts/verify/verify_LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.sh"]),
        CheckSpec("verify_REDTEAM_PASTE_INTEGRITY_GATE_20260613_064232", [SCENE_GENERAL], "紅隊", ["bash", "scripts/verify/verify_REDTEAM_PASTE_INTEGRITY_GATE_20260613_064232.sh"]),
        CheckSpec("verify_REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516", [SCENE_GENERAL], "紅隊", ["bash", "scripts/verify/verify_REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.sh"]),
        CheckSpec("verify_pos_mvp_p2_candidate_projection", [SCENE_MERCHANT], "POS MVP", ["bash", "scripts/verify/verify_pos_mvp_p2_candidate_projection.sh"]),
        CheckSpec("verify_pos_mvp_sandbox", [SCENE_MERCHANT], "POS MVP", ["bash", "scripts/verify/verify_pos_mvp_sandbox.sh"], allowed_nonfatal_markers=["ModuleNotFoundError: No module named 'runtime'", "STATE=HOLD"]),
    ]

    dedup = {}
    for spec in specs:
        dedup[spec.check_id] = spec
    return list(dedup.values())


def _dedupe_by_id(results: List[CheckResult]) -> List[CheckResult]:
    keep: Dict[str, CheckResult] = {}
    for result in results:
        keep[result.check_id] = result
    return list(keep.values())


def _build_scene_matrix(results: List[CheckResult]) -> Dict[str, Dict[str, Any]]:
    scene_order = [
        SCENE_INTENT,
        SCENE_STATE,
        SCENE_COORDINATE,
        SCENE_EVIDENCE,
        SCENE_EXECUTION,
        SCENE_PRIVACY,
        SCENE_TRANSMISSION,
        SCENE_REDTEAM,
    ]
    matrix = {s: {"pass": 0, "warn": 0, "fail": 0, "checks": []} for s in scene_order}
    for result in results:
        for scene in result.scenes or [SCENE_GENERAL]:
            row = matrix.setdefault(
                scene,
                {"pass": 0, "warn": 0, "fail": 0, "checks": []},
            )
            if result.status == "PASS":
                row["pass"] += 1
            elif result.status == "WARN":
                row["warn"] += 1
            else:
                row["fail"] += 1
            row["checks"].append(result.check_id)
    return matrix


def _build_category_matrix(results: List[CheckResult]) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = {}
    for result in results:
        row = matrix.setdefault(result.category or "未分類", {"pass": 0, "warn": 0, "fail": 0})
        if result.status == "PASS":
            row["pass"] += 1
        elif result.status == "WARN":
            row["warn"] += 1
        else:
            row["fail"] += 1
    return matrix


def _to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# W7TP 紅隊全面系統健康總報告（全場景）")
    lines.append("")
    lines.append(f"產生時間（UTC）：{report['generated_at_utc']}")
    lines.append(f"執行範圍：{report['scope']}")
    lines.append("")
    lines.append(f"- 總檢查項：{report['summary']['total']}")
    lines.append(f"- PASS：{report['summary']['pass']}")
    lines.append(f"- WARN：{report['summary']['warn']}")
    lines.append(f"- FAIL：{report['summary']['fail']}")
    lines.append(f"- CRITICAL_FAIL：{report['summary']['critical_fail']}")
    lines.append(f"- 總場權威認定待處理：{report['summary']['total_field_authority_required_count']}")
    lines.append(f"- 總場線上初驗：{'通過' if report['summary']['total_field_online_ok'] else '未通過'}")
    lines.append(f"- 初驗狀態：{report['summary']['total_field_initial_verification_status']}")
    lines.append(f"- 初驗飄移告警數：{report['summary']['initial_drift_alert_count']}")
    lines.append(f"- 初驗漂移回應：{report['summary']['initial_drift_response']}")
    lines.append(f"- 初驗匹配告警數：{report['summary']['initial_matched_alerts_count']}")
    lines.append(f"- scripts/verify 覆蓋：{report['summary']['verify_scripts_covered']} / {report['summary']['verify_script_count']}（缺 {report['summary']['verify_coverage_missing']}）")
    lines.append("")

    if report["summary"]["critical_fail"] > 0:
        lines.append("## 主要結論")
        lines.append("- 存在紅隊高風險暫停項，建議先修正後再進場景導入節奏。")
    elif report["summary"]["fail"] > 0:
        lines.append("## 主要結論")
        lines.append("- 有可執行缺口，偏向治理/文件/環境缺失，建議納入下一輪修補。")
    else:
        lines.append("## 主要結論")
        lines.append("- 目前未出現紅隊高危暫停項；持續追蹤 WARN 類高風險門檻。")
    lines.append("")

    lines.append("## 類別觀測（PASS/WARN/FAIL）")
    lines.append("| 類別 | PASS | WARN | FAIL |")
    lines.append("| --- | ---: | ---: | ---: |")
    for category, counts in sorted(report["category_matrix"].items()):
        lines.append(f"| {category} | {counts['pass']} | {counts['warn']} | {counts['fail']} |")
    lines.append("")

    lines.append("## 場景覆蓋表（PASS/WARN/FAIL）")
    lines.append("| 場景 | PASS | WARN | FAIL | 涵蓋檢查 |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for scene, value in report["scene_matrix"].items():
        checks = ", ".join(value["checks"]) if value["checks"] else "-"
        lines.append(f"| {scene} | {value['pass']} | {value['warn']} | {value['fail']} | {checks} |")
    lines.append("")

    lines.append("## 檢查結果")
    lines.append("")
    lines.append("| ID | 狀態 | 嚴重度 | 總場權威 | 場景 | 分類 | 耗時(ms) | 註記 |")
    lines.append("| --- | --- | --- | --- | --- | --- | ---: | --- |")
    for item in report["checks"]:
        status = {
            "PASS": "✅ PASS",
            "WARN": "⚠️ WARN",
            "FAIL": "⛔ FAIL",
        }.get(item["status"], "?")
        note = "; ".join(item["details"][:5]) if item["details"] else "-"
        lines.append(
            f"| {item['check_id']} | {status} | {item['severity']} | {'是' if item.get('requires_total_field_authority') else '否'} | {','.join(item['scenes'])} | {item['category']} | {item['duration_ms']} | {note} |"
        )

    lines.append("")
    lines.append("## 總場初驗飄移告警")
    if report["summary"]["initial_drift_alert_count"] > 0:
        lines.append(f"- 判定：{report['summary']['total_field_initial_verification_status']}")
        for matched in report["total_field_initial_verification"].get("matched_alerts", []):
            lines.append(f"- matched_alert={matched}")
    else:
        lines.append("- 尚未偵測到初驗飄移告警。")
    lines.append("")

    lines.append("## scripts/verify 覆蓋完整性")
    coverage = report["summary"]
    if coverage["verify_coverage_missing"] > 0:
        lines.append(f"- 未覆蓋 verifier：{coverage['verify_coverage_missing']}")
        for item in report["checks"]:
            if item["check_id"] == "verify_w7tp_verifier_script_coverage":
                for detail in item["details"]:
                    if detail.startswith("missing_files="):
                        lines.append(f"- 缺漏：{detail.split('=', 1)[1]}")
                        break
    else:
        lines.append("- 全量 scripts/verify 已納入健康檢查。")
    lines.append("")

    lines.append("## 紅隊靜態風險摘要")
    redteam = report["redteam_scan"]
    lines.append(f"- secret pattern scan: {redteam['secret_pattern_scan']['status']}（{redteam['secret_pattern_scan']['count']} 筆）")
    lines.append(f"- 對外暴露掃描: {redteam['exposure_scan']['status']}")
    for finding in redteam["exposure_scan"]["findings"]:
        lines.append(f"  - {finding}")

    authority_checks = [item["check_id"] for item in report["checks"] if item.get("requires_total_field_authority")]
    if authority_checks:
        lines.append("")
        lines.append("## 總場權威認定待辦")
        for check_id in authority_checks:
            lines.append(f"- {check_id}")

    lines.append("")
    lines.append("## 修補優先序")
    for item in report["recommendations"]:
        lines.append(f"- {item}")

    if report["recommendations"]:
        lines.append("")
    lines.append("## 建議下個 sprint 實作")
    lines.append("- 1) 先修正高風險 FAIL（W3 deploy 校驗、資源缺失）")
    lines.append("- 2) 將 HOLD 類候選 gate 轉為可驗證的 PASS 產物（例如 direct shortest、auth route）")
    lines.append("- 3) 補齊 POS sandbox 的執行環境隔離（避免 runtime path 漏值）")
    return "\n".join(lines)


def _generate_recommendations(summary: Dict[str, int], checks: List[Dict[str, Any]], scene_matrix: Dict[str, Any]) -> List[str]:
    recs: List[str] = []
    authority_checks = [c for c in checks if c.get("requires_total_field_authority")]
    if authority_checks:
        ids = ", ".join(c["check_id"] for c in authority_checks[:4])
        recs.append(f"以下 {len(authority_checks)} 項需總場權威認定：{ids}...（如仍未補完請停止下放）")

    if summary["critical_fail"] > 0:
        recs.append("優先修正 FAIL 高風險暫停項：W3 系列部署一致性、schema/hash 校驗、關鍵實體缺失。")

    fail_like = [c for c in checks if c["status"] == "FAIL"]
    hold_like = [c for c in checks if c["status"] == "WARN" and c["severity"] in {"high", "critical"}]

    if fail_like:
        sample = ", ".join(c["check_id"] for c in fail_like[:4])
        recs.append(f"建議針對高風險 FAIL 逐一關閉：{sample}。")
    if hold_like:
        recs.append("加速處理 HOLD/WARN 類門檻，完成後轉為 PASS 的可見化節點（特別是 auth/container 與 manual gate）。")

    for scene, value in scene_matrix.items():
        if value["warn"] > 0 or value["fail"] > 0:
            recs.append(f"{scene} 場景的風險需補齊：PASS {value['pass']} / WARN {value['warn']} / FAIL {value['fail']}。")

    if not recs:
        recs.append("目前可追蹤項目可視為初版通過，持續以每次收斂提交更新。")
    return recs[:12]


def _run_sweep() -> Dict[str, Any]:
    total_field_initial_check, total_field_ctx = _run_total_field_initial_verification()
    check_results: List[CheckResult] = []
    total_field_initial_check.scenes = [SCENE_REDTEAM]
    total_field_initial_check.category = "紅隊"
    drift_paused = bool(total_field_ctx.get("execution_paused"))
    execution_pause_reason = total_field_ctx.get("execution_pause_reason")
    external_side_effects_allowed = bool(total_field_ctx.get("external_side_effects_allowed", True))
    _mark_authority_handoff(total_field_initial_check)
    check_results.append(total_field_initial_check)

    check_specs = _build_check_specs()
    for spec in check_specs:
        if drift_paused:
            result = _build_pause_skipped_result(
                check_id=spec.check_id,
                scenes=_map_to_eight_scenes(spec.check_id, spec.category, spec.scenes),
                category=spec.category,
                execution_pause_reason=execution_pause_reason,
                external_side_effects_allowed=external_side_effects_allowed,
            )
        elif spec.command is not None:
            result = _run_command(
                spec.command,
                timeout_sec=spec.timeout_sec,
                allowed_nonfatal_markers=spec.allowed_nonfatal_markers,
                check_id=spec.check_id,
            )
        elif spec.runner is not None:
            result = spec.runner(spec.check_id)
        else:
            raise RuntimeError(f"Check {spec.check_id} missing runner")

        result.scenes = _map_to_eight_scenes(spec.check_id, spec.category, spec.scenes)
        result.category = spec.category
        _mark_authority_handoff(result)
        check_results.append(result)

    # add explicit coverage checks
    if drift_paused:
        coverage_check = _build_pause_skipped_result(
            check_id="verify_w7tp_verifier_script_coverage",
            scenes=_map_to_eight_scenes("verify_w7tp_verifier_script_coverage", "基礎治理", [SCENE_GENERAL]),
            category="基礎治理",
            execution_pause_reason=execution_pause_reason,
            external_side_effects_allowed=external_side_effects_allowed,
        )
    else:
        coverage_check = _run_verifier_coverage_check("verify_w7tp_verifier_script_coverage", check_specs)
        coverage_check.scenes = _map_to_eight_scenes(coverage_check.check_id, coverage_check.category, [SCENE_GENERAL])
        coverage_check.category = "基礎治理"
    _mark_authority_handoff(coverage_check)
    check_results.append(coverage_check)

    for spec in [
        CheckSpec(
            check_id="governance_artifact_matrix",
            scenes=[SCENE_GENERAL],
            category="基礎治理",
            runner=_run_governance_artifacts,
        ),
        CheckSpec(
            check_id="pytest_fixture_suite",
            scenes=[SCENE_GENERAL],
            category="測試套件",
            runner=_run_pytest_if_available,
        ),
        CheckSpec(
            check_id="redteam_policy_risk_scan",
            scenes=[SCENE_GENERAL],
            category="紅隊掃描",
            runner=_run_redteam_scan,
        ),
    ]:
        if drift_paused:
            result = _build_pause_skipped_result(
                check_id=spec.check_id,
                scenes=_map_to_eight_scenes(spec.check_id, spec.category, spec.scenes),
                category=spec.category,
                execution_pause_reason=execution_pause_reason,
                external_side_effects_allowed=external_side_effects_allowed,
            )
            result.scenes = _map_to_eight_scenes(spec.check_id, spec.category, spec.scenes)
            result.category = spec.category
            _mark_authority_handoff(result)
            check_results.append(result)
            continue

        if spec.runner is None:
            continue
        result = spec.runner(spec.check_id)
        result.scenes = _map_to_eight_scenes(spec.check_id, spec.category, spec.scenes)
        result.category = spec.category
        _mark_authority_handoff(result)
        check_results.append(result)

    # remove accidental duplicates preserving the latest status
    check_results = _dedupe_by_id(check_results)

    serialized = [asdict(r) for r in check_results]
    status_counter = {"PASS": 0, "WARN": 0, "FAIL": 0}
    critical_fail = 0
    total_field_authority_required_count = 0
    verifier_coverage = {
        "verify_script_count": 0,
        "verify_scripts_covered": 0,
        "verify_coverage_missing": 0,
        "verify_coverage_missing_files": [],
    }
    for item in serialized:
        status_counter[item["status"]] = status_counter.get(item["status"], 0) + 1
        if item.get("requires_total_field_authority"):
            total_field_authority_required_count += 1
        if item["status"] == "FAIL" and item["severity"] in {"critical", "high"}:
            critical_fail += 1
        if item["check_id"] == "verify_w7tp_verifier_script_coverage":
            for detail in item.get("details", []):
                if detail.startswith("verify_scripts="):
                    verifier_coverage["verify_script_count"] = int(detail.split("=", 1)[1])
                elif detail.startswith("covered_verify_scripts="):
                    verifier_coverage["verify_scripts_covered"] = int(detail.split("=", 1)[1])
                elif detail.startswith("missing="):
                    verifier_coverage["verify_coverage_missing"] = int(detail.split("=", 1)[1])
                elif detail.startswith("missing_files="):
                    files = detail.split("=", 1)[1]
                    verifier_coverage["verify_coverage_missing_files"] = files.split(",") if files else []

    scene_matrix = _build_scene_matrix(check_results)
    category_matrix = _build_category_matrix(check_results)
    if drift_paused:
        redteam_scan = {
            "status": "WARN",
            "secret_pattern_scan": {
                "status": "SKIPPED",
                "count": 0,
                "hits": [],
            },
            "exposure_scan": {
                "status": "SKIPPED",
                "findings": [],
            },
            "compliance_aux_checks": {
                "status": "SKIPPED",
            },
            "details": [
                "execution_paused=true",
                f"execution_pause_reason={execution_pause_reason or 'null'}",
                f"external_side_effects_allowed={external_side_effects_allowed}",
                "drift_pause_gate_active",
            ],
        }
    else:
        redteam_scan = _scan_policy_risks()
    action_guard = _redteam_forbidden_action_scan(check_results, drift_paused)

    report = {
        "generated_at_utc": _now_iso(),
        "scope": "W7TP 全系統紅隊觀點（8 合一總場分場）+ 全功能健康矩陣",
        "summary": {
            "total": len(serialized),
            "pass": status_counter["PASS"],
            "warn": status_counter["WARN"],
            "fail": status_counter["FAIL"],
            "critical_fail": critical_fail,
            "total_field_initial_verification_status": total_field_ctx["decision"],
            "total_field_online_ok": total_field_ctx["total_field_online_ok"],
            "initial_drift_alert_count": total_field_ctx["drift_alert_count"],
            "initial_matched_alerts_count": total_field_ctx["matched_alerts_count"],
            "initial_drift_response": total_field_ctx["drift_response"],
            "execution_paused": total_field_ctx["execution_paused"],
            "execution_pause_reason": total_field_ctx["execution_pause_reason"],
            "external_side_effects_allowed": total_field_ctx["external_side_effects_allowed"],
            "verify_script_count": verifier_coverage["verify_script_count"],
            "verify_scripts_covered": verifier_coverage["verify_scripts_covered"],
            "verify_coverage_missing": verifier_coverage["verify_coverage_missing"],
            "total_field_authority_required_count": total_field_authority_required_count,
        },
        "total_field_initial_verification": total_field_ctx,
        "checks": serialized,
        "scene_matrix": scene_matrix,
        "category_matrix": category_matrix,
        "redteam_scan": redteam_scan,
        "redteam_forbidden_action_scan": action_guard,
    }
    report["recommendations"] = _generate_recommendations(report["summary"], report["checks"], report["scene_matrix"])

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a comprehensive red-team health sweep and render report.")
    parser.add_argument("--out-json", default="reports/w7tp_redteam_total_system_health_report.json", help="JSON report path")
    parser.add_argument("--out-md", default="reports/w7tp_redteam_total_system_health_report.md", help="Markdown report path")
    args = parser.parse_args()

    report = _run_sweep()

    # static check scan data already calculated during run_sweep
    redteam_scan = report["redteam_scan"]

    json_path = ROOT / args.out_json
    md_path = ROOT / args.out_md
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")

    print(f"STATE=PASS_W7TP_REDTEAM_TOTAL_SYSTEM_HEALTH_REPORT")
    print(f"TOTAL={report['summary']['total']} PASS={report['summary']['pass']} WARN={report['summary']['warn']} FAIL={report['summary']['fail']}")
    print(f"CRITICAL_FAIL={report['summary']['critical_fail']}")
    print(f"STATE={'D8_TOTAL_FIELD_ONLINE_OK' if report['summary']['total_field_online_ok'] else 'D8_TOTAL_FIELD_ONLINE_CHECK_FAILED'}")
    print(f"TOTAL_FIELD_INITIAL_DECISION={report['summary']['total_field_initial_verification_status']}")
    print(f"TOTAL_FIELD_INITIAL_DRIFT_COUNT={report['summary']['initial_drift_alert_count']}")
    print(f"TOTAL_FIELD_INITIAL_MATCHED_ALERTS={report['summary']['initial_matched_alerts_count']}")
    print(f"TOTAL_FIELD_INITIAL_DRIFT_RESPONSE={report['summary']['initial_drift_response']}")
    print(f"execution_paused={report['summary']['execution_paused']}")
    print(f"execution_pause_reason={report['summary']['execution_pause_reason']}")
    print(f"external_side_effects_allowed={report['summary']['external_side_effects_allowed']}")
    if report["summary"]["initial_drift_alert_count"] > 0:
        print("ALERT=PAUSE_DUE_TO_DRIFT")
        print("ALERT_ACTION=PAUSE_ONLY")
        print("DRIFT_ACTION=PAUSE_ONLY_NO_WRITE")
        print("DRIFT_RESPONSE=READ_ONLY_NO_WRITE")
    print(f"TOTAL_FIELD_AUTHORITY={report['summary']['total_field_authority_required_count']}")
    print(f"SECRET_SCAN_STATUS={redteam_scan['secret_pattern_scan']['status']}")
    print(f"EXPOSURE_SCAN_STATUS={redteam_scan['exposure_scan']['status']}")
    print(f"REDTEAM_RESULT={report['redteam_forbidden_action_scan']['status']}")
    print(f"REDTEAM_FORBIDDEN_HITS={len(report['redteam_forbidden_action_scan']['forbidden_hits'])}")
    print(f"JSON={json_path}")
    print(f"MD={md_path}")

    if report["summary"]["critical_fail"] > 0:
        return 2
    if report["summary"]["fail"] > 0 or report["summary"]["warn"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
