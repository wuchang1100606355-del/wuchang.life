from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.resource_arbitration import (
    arbitrate_resources,
    build_static_state_cell_envelope,
)

router = APIRouter(prefix="/api/taiji/nl-control", tags=["8D ADI Natural Language Control"])

PROJECT_ROOT = Path(os.getenv("TAIJI_PROJECT_ROOT", "/home/taiji_admin/Taiji_Hub"))
SKILL_ID = "w7tp-8d-adi-natural-language-control"
SKILL_ROOT = PROJECT_ROOT / ".skill-build" / SKILL_ID
RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "natural_language_control"
RUNNER_PATH = PROJECT_ROOT / "tools" / "w7tp_nl_goal_runner.py"
LOCAL_AGENT_PATH = PROJECT_ROOT / "tools" / "w7tp_local_model_agent.py"
CLEAN_EXEC_ROOT = Path("/tmp/w7tp-nl-control-exec")
LOCAL_OLLAMA_URL = os.getenv("TAIJI_LOCAL_OLLAMA_URL", "http://100.84.204.114:11434")
LOCAL_MODEL = os.getenv("TAIJI_LOCAL_MODEL", "taiji-qwen2.5-coder-7b:ctx16k")
GOOGLE_FALLBACK = os.getenv("TAIJI_GOOGLE_CANDIDATE_FALLBACK", "1") == "1"
AUTO_LAND_DEFAULT = True
class NaturalLanguageRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=8192)
    task_id: str | None = Field(default=None, min_length=1, max_length=128)
    goal_mode: bool = True
    auto_land: bool = True
    timeout_seconds: int = Field(default=1200, ge=60, le=3600)
    dry_run: bool = False
    google_fallback: bool = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(args: list[str]) -> str:
    p = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *args],
        text=True,
        capture_output=True,
        timeout=15,
    )
    return p.stdout.strip()
def _http_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=3) as r:
            raw = r.read(64 * 1024)
        data = json.loads(raw.decode("utf-8"))
        return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _local_model_health() -> dict[str, Any]:
    probe = _http_json(LOCAL_OLLAMA_URL.rstrip("/") + "/api/tags")
    if not probe.get("ok"):
        return {"ok": False, "model": LOCAL_MODEL}
    models = [
        item.get("name")
        for item in probe.get("data", {}).get("models", [])
        if isinstance(item, dict)
    ]
    return {
        "ok": LOCAL_MODEL in models,
        "model": LOCAL_MODEL,
        "provider": "MSI_OLLAMA_LOCAL",
    }


def _resolve_task_id(requested: str | None) -> str:
    if requested:
        return requested
    try:
        ledger = json.loads((PROJECT_ROOT / "state" / "WORK_LEDGER.json").read_text(encoding="utf-8"))
        doing = [
            task for task in ledger.get("TASKS", [])
            if task.get("STATE") == "DOING"
        ]
        rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        doing.sort(key=lambda task: (rank.get(task.get("PRIORITY"), 99), task.get("TASK_ID", "")))
        if doing:
            return str(doing[0]["TASK_ID"])
    except Exception:
        pass
    return "UNBOUND-NATURAL-LANGUAGE"


def _affected_closure(intent: str) -> list[str]:
    text = intent.lower()
    closure = [f".skill-build/{SKILL_ID}"]
    matched = False

    if any(k in text for k in ["自然語言", "nl-control", "intent", "意圖", "gateway", "控制器"]):
        closure.extend([
            "core/intent_continuity.py",
            "core/work_ledger.py",
            "services/gateway",
        ])
        matched = True
    if any(k in text for k in ["網路", "network", "tailscale", "router", "路由", "vpn"]):
        closure.extend([
            "capabilities/w7tp-8d-adi-adaptive-network",
            "configs", "scripts", "tests",
        ])
        matched = True
    if any(k in text for k in ["產品", "product", "競品", "competition", "競賽", "展示"]):
        closure.append("product_and_competitor_evidence")
        matched = True
    if any(k in text for k in ["咖啡", "pos", "odoo", "菜單", "會員"]):
        closure.extend([
            "Taiji_Odoo/addons", "web", "tools", "tests", "configs",
        ])
        matched = True
    if any(k in text for k in ["total field", "總場", "8d adi", "8dadi", "native adi"]):
        closure.extend([
            "tools/total_field", "services", "configs", "schemas", "tests",
        ])
        matched = True

    if not matched:
        closure.extend(["core", "services", "tools", "tests"])
    return list(dict.fromkeys(closure))
def build_plan(req: NaturalLanguageRequest) -> dict[str, Any]:
    task_id = _resolve_task_id(req.task_id)
    closure = _affected_closure(req.intent)
    google_allowed = bool(req.google_fallback and GOOGLE_FALLBACK)
    resource_decision = arbitrate_resources(
        req.intent,
        root=PROJECT_ROOT,
        local_ollama_url=LOCAL_OLLAMA_URL,
        local_model=LOCAL_MODEL,
        google_allowed=google_allowed,
    )
    static_cell = build_static_state_cell_envelope(
        req.intent,
        task_id=task_id,
        affected_closure=closure,
        resource_decision=resource_decision,
    )
    preferred = resource_decision.get("PREFERRED_SET", [])
    qualified = resource_decision.get("QUALIFIED_SET", [])
    resource_coordinates = resource_decision.get(
        "RESOURCE_COORDINATES",
        [],
    )
    gemini_resource = next(
        (
            item
            for item in resource_coordinates
            if isinstance(item, dict)
            and item.get("RESOURCE_ID") == "GEMINI_CODE_ASSIST"
        ),
        {},
    )
    gemini_pointer_bound = (
        gemini_resource.get("CONTEXT_BINDING_STATE")
        == "POINTER_FIRST_TOTAL_FIELD_BOUND"
    )
    selected_candidate_builder = (
        "MSI_OLLAMA_LOCAL"
        if "MSI_OLLAMA_LOCAL" in qualified
        else None
    )
    bound_reasoning_organs = (
        ["GEMINI_CODE_ASSIST"]
        if gemini_pointer_bound
        else []
    )
    return {
        "state": "READY_GOAL_MODE",
        "skill_id": SKILL_ID,
        "TASK_ID": task_id,
        "goal_mode": req.goal_mode,
        "auto_land": req.auto_land,
        "intent_hash": _sha256_text(req.intent),
        "RESOURCE_DECISION": resource_decision,
        "STATIC_STATE_CELL": static_cell,
        "D1_INTENT": {"source": "FOUNDER_NATURAL_LANGUAGE", "present": True},
        "D2_STATE": {"mode": "GOAL_MODE", "status": "PLANNED"},
        "D3_COORDINATE": {
            "node": "taiji01",
            "root": str(PROJECT_ROOT),
            "branch": _git(["branch", "--show-current"]),
            "head": _git(["rev-parse", "HEAD"]),
            "affected_closure": closure,
        },
        "D4_EVIDENCE": {
            "prompt_persisted": False,
            "resource_coordinate_count": len(resource_decision.get("RESOURCE_COORDINATES", [])),
        },
        "D5_EXECUTION": {
            "executor": (
                "w7tp_nl_goal_runner -> resource arbitration -> shadow candidate "
                "-> deterministic verification -> Total Field sole receiver "
                "-> control-layer autoland"
            ),
            "mode": "source-only shadow async goal runner",
            "current_runner_provider": selected_candidate_builder,
            "selected_candidate_builder": selected_candidate_builder,
            "primary_model": LOCAL_MODEL,
            "preferred_resources": preferred,
            "google_candidate_fallback": google_allowed,
            "cloud_authority": "CANDIDATE_ONLY",
            "formal_land_gate": "TAIJI01_TOTAL_FIELD_SOLE_RECEIVER",
            "context_delivery_mode": "TOTAL_FIELD_POINTER_FIRST_DYNAMIC_CONTEXT_PULL",
            "context_pull_owner": (
                "tools.total_field_dynamic_context_pull."
                "TotalFieldDynamicContextPullBroker"
            ),
            "context_bootstrap": "POINTER_AND_REFERENCES_ONLY",
            "dynamic_context_materialization": "LOCAL_VOLATILE_ON_PULL",
            "context_persistence": "EPHEMERAL_BODY_REFERENCES_ONLY",
            "real_task_state_packet_auto_issue": gemini_pointer_bound,
            "real_task_state_sources": [
                "WORK_LEDGER",
                "ACTION_LEDGER",
                "CURRENT_CONVERSATION_CHECKPOINT",
                "NATIVE_ADI_SELECTED_RECORDS",
            ],
            "complex_code_reasoning_pipeline": (
                "REAL_TASK_STATE_MINIMUM_PACKET"
                "->GEMINI_A2A_POINTER_FIRST_CANDIDATE"
                "->MSI_LOCAL_SOURCE_BUILDER"
                "->DETERMINISTIC_VALIDATION"
                "->TOTAL_FIELD_SOURCE_DELTA_GATE"
                "->LAND"
            ),
            "legacy_vertex_direct_context_allowed": False,
            "bound_reasoning_organs": bound_reasoning_organs,
            "gemini_a2a_binding": (
                "POINTER_FIRST_TOTAL_FIELD_BOUND"
                if gemini_pointer_bound
                else "HOLD_POINTER_FIRST_A2A_NOT_BOUND"
            ),
            "gemini_direct_source_write": False,
            "resource_binding_state": (
                "EXECUTABLE_LOCAL_WITH_RESOURCE_DECISION"
                if preferred[:1] == ["MSI_OLLAMA_LOCAL"]
                else (
                    "EXECUTABLE_LOCAL_SOURCE_BUILDER_WITH_BOUND_GEMINI_REASONING_ORGAN"
                    if (
                        preferred[:1] == ["GEMINI_CODE_ASSIST"]
                        and gemini_pointer_bound
                        and selected_candidate_builder == "MSI_OLLAMA_LOCAL"
                    )
                    else (
                        "EXECUTABLE_LOCAL_FALLBACK_SPECIALIST_PENDING"
                        if selected_candidate_builder == "MSI_OLLAMA_LOCAL"
                        else "HOLD_NO_EXECUTABLE_CANDIDATE_BUILDER"
                    )
                )
            ),
        },
        "D6_GST": {"state": "NOT_APPLICABLE_CONTROL_CARRIER"},
        "D7_RISK": {
            "unrelated_dirty_state_must_be_preserved": True,
            "cloud_requires_static_state_cell": True,
            "context_pull_single_use": True,
            "context_pull_exact_task_provider_model_binding": True,
            "full_dynamic_context_in_initial_model_bootstrap": False,
            "local_rule_ref_cloud_visible": False,
            "gemini_reasoning_failure_local_fallback": True,
            "gemini_candidate_never_becomes_source_truth": True,
        },
        "D8_AUTHORITY": {
            "source": "CURRENT_FOUNDER_INTENT_ENVELOPE",
            "provider_authority": "NONE",
            "formal_effect_boundary": "TAIJI01_TOTAL_FIELD",
        },
    }
def _local_agent_prompt(intent: str, plan: dict[str, Any]) -> str:
    return """Use $w7tp-8d-adi-natural-language-control from {skill_root}.

Founder natural-language intent:
{intent}

Operate in GOAL MODE on taiji01 at {project_root}.
Mandatory:
- Use 8D analysis as the understanding/relationship engine and ADI coordinates as the localization/comparison basis.
- Separate OBSERVED_FACT, HYPOTHESIS, DESIGN, IMPLEMENTATION, LANDED, ACTIVE, and CANONICAL.
- Global addressability does not mean full scan. Follow only the affected closure and stop expansion at the first breakpoint.
- Reuse/extend/fuse existing capabilities before creating a new framework.
- Model context delivery is pointer-first: initial model context may carry only governed pull coordinates and references; full Dynamic Context must be materialized locally on pull and remain ephemeral.
- For product/design work include product level and competitor comparison with evidence coordinates; unknown competitor facts remain UNKNOWN.
- AUTO-LAND is enabled for reversible effects inside this intent scope: do not stop at candidate or ready-to-land.
- Preserve unrelated dirty worktree state. Never use git reset --hard, clean -fd, force push, or bulk staging.
- After implementation, run proportionate tests, land the exact effect, reobserve, and rollback if the target state is not reached.
- Do not claim CANONICAL without an actual authority resolution.
- Continue until ACTIVE_VERIFIED or one true external hard blocker.

Server-side route plan:
{plan_json}
""".format(
        skill_root=SKILL_ROOT,
        intent=intent,
        project_root=PROJECT_ROOT,
        plan_json=json.dumps(plan, ensure_ascii=False, sort_keys=True),
    )
def _write_receipt(receipt: dict[str, Any]) -> str:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + ".json"
    path = RUNTIME_ROOT / name
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(PROJECT_ROOT))


@router.get("/status")
def status():
    return {
        "state": "ACTIVE_EXECUTABLE_CAPABILITY" if SKILL_ROOT.exists() and RUNNER_PATH.exists() and LOCAL_AGENT_PATH.exists() else "HOLD_CAPABILITY_MISSING",
        "skill_id": SKILL_ID,
        "skill_present": SKILL_ROOT.exists(),
        "codex_in_execution_path": False,
        "local_agent_present": LOCAL_AGENT_PATH.exists(),
        "local_model_primary": LOCAL_MODEL,
        "local_model_host": "MSI",
        "local_ollama_url": LOCAL_OLLAMA_URL,
        "local_model_health": _local_model_health(),
        "development_ui": "https://taiji01.tailea1eef.ts.net:8444/?folder=/home/taiji_admin/Taiji_Hub",
        "google_fallback": GOOGLE_FALLBACK,
        "google_cloud_role": "CANDIDATE_ONLY_AFTER_LOCAL_HOLD",
        "auto_land_default": AUTO_LAND_DEFAULT,
        "execution_architecture": "8D_ADI_LOCAL_MODEL_SHADOW_GOOGLE_CANDIDATE_AUTOLAND",
        "runner_isolation": "SYSTEMD_TRANSIENT_SERVICE",
        "goal_runner_present": RUNNER_PATH.exists(),
        "project_root": str(PROJECT_ROOT),
        "gateway_health": _http_json("http://127.0.0.1:8081/health"),
        "total_field_health": _http_json("http://127.0.0.1:8082/healthz"),
        "native_adi_health": _http_json("http://127.0.0.1:9110/health"),
    }
@router.post("/plan")
def plan(req: NaturalLanguageRequest):
    return build_plan(req)


def _run_state_path(run_id: str) -> Path:
    if len(run_id) != 32 or any(ch not in "0123456789abcdef" for ch in run_id):
        raise HTTPException(status_code=400, detail="RUN_ID_INVALID")
    return RUNTIME_ROOT / "runs" / run_id / "state.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_name, path)


@router.get("/runs/{run_id}")
def run_state(run_id: str):
    path = _run_state_path(run_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/execute")
def execute(req: NaturalLanguageRequest):
    if not req.goal_mode:
        raise HTTPException(status_code=409, detail="HOLD_GOAL_MODE_REQUIRED")
    if not req.auto_land:
        raise HTTPException(status_code=409, detail="HOLD_AUTO_LAND_REQUIRED_FOR_EXECUTE")
    if not SKILL_ROOT.exists():
        raise HTTPException(status_code=503, detail="HOLD_SKILL_NOT_INSTALLED")
    if not LOCAL_AGENT_PATH.exists():
        raise HTTPException(status_code=503, detail="HOLD_LOCAL_AGENT_NOT_AVAILABLE")
    if not RUNNER_PATH.exists():
        raise HTTPException(status_code=503, detail="HOLD_GOAL_RUNNER_NOT_AVAILABLE")

    plan_data = build_plan(req)
    if req.dry_run:
        return {"state": "PASS_DRY_RUN", "plan": plan_data}

    run_id = uuid.uuid4().hex
    run_dir = RUNTIME_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    plan_data["run_id"] = run_id
    _atomic_write_json(run_dir / "plan.json", plan_data)
    runner_unit = f"w7tp-nl-run-{run_id[:16]}.service"
    fifo_path = Path(f"/tmp/w7tp-nl-intent-{run_id}.fifo")
    _atomic_write_json(
        run_dir / "state.json",
        {
            "run_id": run_id,
            "state": "STARTING",
            "started_at": _now(),
            "intent_hash": plan_data["intent_hash"],
            "prompt_persisted": False,
            "runner_unit": runner_unit,
            "runner_isolation": "SYSTEMD_TRANSIENT_SERVICE",
        },
    )

    os.mkfifo(fifo_path, 0o600)
    shell_command = (
        f"exec /usr/bin/python3 {RUNNER_PATH} {run_id} {req.timeout_seconds} "
        f"< {fifo_path}"
    )
    launch = subprocess.run(
        [
            "sudo", "-n", "systemd-run",
            f"--unit={runner_unit.removesuffix('.service')}",
            "--collect",
            "--property=User=taiji_admin",
            "--property=Group=taiji_admin",
            f"--property=WorkingDirectory={PROJECT_ROOT}",
            "/bin/bash", "-lc", shell_command,
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    if launch.returncode != 0:
        fifo_path.unlink(missing_ok=True)
        _atomic_write_json(
            run_dir / "state.json",
            {
                "run_id": run_id,
                "state": "HOLD_RUNNER_START_FAILED",
                "finished_at": _now(),
                "intent_hash": plan_data["intent_hash"],
                "prompt_persisted": False,
                "runner_unit": runner_unit,
            },
        )
        raise HTTPException(status_code=500, detail="RUNNER_START_FAILED")

    fd = None
    deadline = time.monotonic() + 5
    while fd is None and time.monotonic() < deadline:
        try:
            fd = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            time.sleep(0.05)
    if fd is None:
        fifo_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="RUNNER_STDIN_UNAVAILABLE")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(req.intent)
        handle.flush()
    fifo_path.unlink(missing_ok=True)

    return {
        "state": "GOAL_RUN_STARTED",
        "run_id": run_id,
        "intent_hash": plan_data["intent_hash"],
        "prompt_persisted": False,
        "auto_land": True,
        "runner_unit": runner_unit,
        "runner_isolation": "SYSTEMD_TRANSIENT_SERVICE",
        "status_endpoint": f"/api/taiji/nl-control/runs/{run_id}",
    }
