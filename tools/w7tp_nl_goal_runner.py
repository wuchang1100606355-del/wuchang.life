#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

PROJECT_ROOT = Path("/home/taiji_admin/Taiji_Hub")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.execution_continuity import ActionLedger, build_idempotency_key
from core.msi_local_llm_route import (
    MSI_WINDOWS_TAILSCALE_OLLAMA_URL,
    resolve_msi_ollama_url,
)
from core.work_ledger import WorkLedger
from tools.gemini_code_assist_a2a_candidate import (
    MODEL_REF as GEMINI_MODEL_REF,
    PROVIDER_REF as GEMINI_PROVIDER_REF,
    run_pointer_first_candidate as run_gemini_pointer_first_candidate,
)
from tools.total_field_candidate_gateway import llm_push
from tools.total_field_dynamic_context_pull import (
    TotalFieldDynamicContextPullBroker,
)
from tools.w7tp_task_state_minimum_packet import (
    build_task_model_visible_context,
    issue_task_state_minimum_packet,
    select_task_state_support_refs,
)

SKILL_ID = "w7tp-8d-adi-natural-language-control"
LOCAL_AGENT = PROJECT_ROOT / "tools" / "w7tp_local_model_agent.py"
LOCAL_MODEL = os.getenv("TAIJI_LOCAL_MODEL", "taiji-qwen2.5-coder-7b:ctx16k")
LOCAL_OLLAMA_URL_OVERRIDE = os.getenv("TAIJI_LOCAL_OLLAMA_URL", "").strip()
VERTEX_GATEWAY = PROJECT_ROOT / "tools" / "total_field" / "w7tp_vertex_candidate_gateway.py"
GEMINI_PACKET = PROJECT_ROOT / "tools" / "xiaoj_gemini_no_plaintext_candidate_packet.py"
STATE_ROOT = PROJECT_ROOT / "runtime" / "natural_language_control" / "runs"
MAX_CHANGED_FILES = 64
MAX_CHANGED_FILE_BYTES = 8 * 1024 * 1024
SOURCE_ROOTS = (
    "core", "services", "tools", "capabilities", "configs", "schemas",
    "scripts", "tests", "docs", "web", "products", "deploy",
    "legacy_core", "runtime_adapters", "models", "prompts", ".skill-build",
    "Taiji_Odoo/addons", "Taiji_Odoo/config", "Taiji_Odoo/scripts",
)

IGNORE_NAMES = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".git",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())
def safe_rel(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    if rel.startswith("../") or rel == "..":
        raise ValueError("PATH_ESCAPE")
    return rel


def closure_paths(plan: dict[str, Any]) -> list[str]:
    raw = list(plan.get("D3_COORDINATE", {}).get("affected_closure", []))
    expanded: list[str] = []
    for rel in raw:
        if rel == "product_and_competitor_evidence":
            expanded.extend(["products", "web", "docs", "tests"])
        else:
            expanded.append(rel)
    skill_rel = f".skill-build/{SKILL_ID}"
    if skill_rel not in expanded:
        expanded.append(skill_rel)
    return list(dict.fromkeys(expanded))


def copy_source_snapshot(shadow: Path, plan: dict[str, Any]) -> list[str]:
    copied: list[str] = []
    for rel in closure_paths(plan):
        src = PROJECT_ROOT / rel
        dst = shadow / rel
        if not src.exists():
            continue
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            shutil.copytree(
                src, dst, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(*sorted(IGNORE_NAMES), "*.pyc", "*.pyo"),
            )
        copied.append(rel)
    return copied
def snapshot(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel_root in SOURCE_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        paths = [base] if base.is_file() else base.rglob("*")
        for path in paths:
            if not path.is_file() or path.is_symlink():
                continue
            rel = safe_rel(path, root)
            if any(part in IGNORE_NAMES for part in Path(rel).parts):
                continue
            stat = path.stat()
            out[rel] = {"sha256": sha_file(path), "size": stat.st_size}
    return out


def diff_snapshot(before: dict, after: dict) -> dict[str, list[str]]:
    b, a = set(before), set(after)
    return {
        "created": sorted(a - b),
        "deleted": sorted(b - a),
        "modified": sorted(k for k in a & b if before[k]["sha256"] != after[k]["sha256"]),
    }


def _canonical_json_sha(value: Any) -> str:
    return sha_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _total_field_source_delta_gate(
    *,
    run_id: str,
    intent_hash: str,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    changes: dict[str, list[str]],
    deterministic_validation: dict[str, Any],
) -> dict[str, Any]:
    """Adjudicate a verified source delta through the sole Total Field receiver."""

    changed_files = changes["created"] + changes["modified"]
    file_projection: dict[str, dict[str, Any]] = {}
    for rel in changed_files:
        observed = after.get(rel)
        if not isinstance(observed, dict):
            raise RuntimeError("HOLD_TOTAL_FIELD_SOURCE_DELTA_FILE_MISSING")
        file_projection[rel] = {
            "sha256": observed.get("sha256"),
            "size": observed.get("size"),
        }

    previous_state_sha = _canonical_json_sha(before)
    delta_material = {
        "created": changes["created"],
        "modified": changes["modified"],
        "deleted": changes["deleted"],
        "files": file_projection,
    }
    candidate_sha = _canonical_json_sha(delta_material)
    verification_sha = _canonical_json_sha(deterministic_validation)
    suffix = candidate_sha[:16]
    event_ref = f"event:nl-source-delta:{suffix}"
    observation_domain_ref = f"observation-domain:nl-source-delta:{suffix}"

    shared_fields = {
        "D1": {"intent_ref": f"intent:nl:sha256:{intent_hash}"},
        "D3": {
            "node_ref": "node:taiji01",
            "coordinate_ref": "repo:Taiji_Hub",
        },
        "D4": {
            "evidence_ref": f"evidence:source-delta:sha256:{candidate_sha}",
        },
        "D5": {
            "execution_ref": "execution:nl-control:source-land-candidate",
        },
        "D6": {
            "privacy_boundary_ref": "privacy:nl-control:no-plaintext-source",
        },
        "D7": {
            "rule_ref": "rule:nl-control:verified-source-delta",
            "routing_ref": "routing:total-field:source-delta",
            "reconstruction_condition": "condition:deterministic-validation-pass",
        },
        "D8": {
            "adjudication_policy_ref": "d8-policy:nl-control:source-delta",
        },
    }
    previous_state = {
        **shared_fields,
        "D2": {"state_ref": f"source-state:sha256:{previous_state_sha}"},
    }
    candidate_state = {
        **shared_fields,
        "D2": {"state_ref": f"source-candidate:sha256:{candidate_sha}"},
    }
    request = {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": event_ref,
            "observation_domain_ref": observation_domain_ref,
            "dimensions": {
                f"D{i}_ref": f"field/tfct/D{i}/v0_1"
                for i in range(1, 9)
            },
            "constraint_hypergraph_ref": "constraints/tfct/runtime-hypergraph/v0_1",
            "convergence_operator_ref": "convergence/tfct/finite-fixed-point/v0_1",
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "event": {
            "event_id": f"event-id:nl-source-delta:{suffix}",
            "event_ref": event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical-time:nl:{run_id}",
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": candidate_state,
        "context": {
            "request_ref": f"request:nl-source-delta:{suffix}",
            "d3_context": {
                "projection_ref": f"projection:nl-source-delta:{suffix}",
            },
        },
        "adi_requested": False,
    }
    observation_domains = {
        observation_domain_ref: {
            "configured": True,
            "observations": {
                "candidate_delta_ref": f"source-delta:sha256:{candidate_sha}",
                "deterministic_verification_ref": (
                    f"verification:sha256:{verification_sha}"
                ),
                "previous_state_ref": f"source-state:sha256:{previous_state_sha}",
            },
        }
    }

    result = llm_push(
        request,
        previous_state=previous_state,
        observation_domains=observation_domains,
    )
    allowed = (
        result.get("final_decision") == "ALLOW"
        and result.get("fixed_point_status") == "REACHED"
        and result.get("commit_applied") is True
    )
    if not allowed:
        raise RuntimeError(
            "HOLD_TOTAL_FIELD_SOURCE_DELTA:"
            + str(result.get("final_decision"))
            + ":"
            + str(result.get("fixed_point_status"))
        )
    return {
        "state": "PASS_TOTAL_FIELD_SOURCE_DELTA_ADJUDICATION",
        "candidate_sha256": candidate_sha,
        "previous_state_sha256": previous_state_sha,
        "verification_sha256": verification_sha,
        "final_decision": result.get("final_decision"),
        "fixed_point_status": result.get("fixed_point_status"),
        "commit_applied": result.get("commit_applied"),
        "decision_reason_codes": result.get("decision_reason_codes"),
        "state_ref": result.get("state_ref"),
        "tfid": result.get("tfid"),
        "total_field_hash": result.get("total_field_hash"),
        "raw_source_body_submitted": False,
    }


def run(cmd: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout,
    )


def validate_candidate(shadow: Path, changes: dict[str, list[str]]) -> dict[str, Any]:
    changed = changes["created"] + changes["modified"] + changes["deleted"]
    if len(changed) > MAX_CHANGED_FILES:
        raise RuntimeError("HOLD_TOO_MANY_CHANGED_FILES")
    results: list[dict[str, Any]] = []
    for rel in changes["created"] + changes["modified"]:
        path = shadow / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("HOLD_NONREGULAR_CANDIDATE_FILE")
        if path.stat().st_size > MAX_CHANGED_FILE_BYTES:
            raise RuntimeError("HOLD_CHANGED_FILE_TOO_LARGE")
        if rel.endswith(".py"):
            p = run(["python3", "-m", "py_compile", rel], cwd=shadow, timeout=120)
            results.append({"kind": "py_compile", "path": rel, "rc": p.returncode})
            if p.returncode != 0:
                raise RuntimeError("HOLD_PY_COMPILE_FAILED")
        elif rel.endswith(".json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
                results.append({"kind": "json_parse", "path": rel, "rc": 0})
            except Exception as exc:
                raise RuntimeError("HOLD_JSON_PARSE_FAILED") from exc
        elif rel.endswith(".js") and shutil.which("node"):
            p = run(["node", "--check", rel], cwd=shadow, timeout=120)
            results.append({"kind": "node_check", "path": rel, "rc": p.returncode})
            if p.returncode != 0:
                raise RuntimeError("HOLD_NODE_CHECK_FAILED")

    changed_tests = [
        rel for rel in changes["created"] + changes["modified"]
        if rel.startswith("tests/") and rel.endswith(".py")
    ]
    if changed_tests:
        p = run(["python3", "-m", "pytest", "-q", *changed_tests], cwd=shadow, timeout=300)
        results.append({"kind": "pytest_changed", "paths": changed_tests, "rc": p.returncode})
        if p.returncode != 0:
            raise RuntimeError("HOLD_CHANGED_TEST_FAILED")
    return {"state": "PASS_DETERMINISTIC_VALIDATION", "checks": results}
def explicit_delete_allowed(intent: str) -> bool:
    text = intent.lower()
    return any(k in text for k in ("刪除", "移除", "delete", "remove"))


def effectful_intent(intent: str) -> bool:
    text = " ".join(intent.lower().split())
    read_only_markers = (
        "唯讀", "只讀", "只回報", "只檢查", "禁止修改", "不得修改",
        "不要修改", "不修改", "禁止寫入", "不得寫入", "不要寫入",
        "read-only", "readonly", "read only", "no write", "do not modify",
    )
    if any(marker in text for marker in read_only_markers):
        return False
    return any(k in text for k in (
        "新增", "修改", "修正", "修復", "建立", "實作", "加入", "改成",
        "部署", "啟用", "整合", "建構", "落地", "add", "modify", "change",
        "implement", "fix", "create", "update", "deploy", "enable", "integrate",
    ))


def atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".nl.tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def infer_services(changed: list[str]) -> list[str]:
    services: set[str] = set()
    if any(p.startswith("services/gateway/") for p in changed):
        services.add("taiji-gateway.service")
    if "legacy_core/taiji_unified_gateway_edge.py" in changed:
        services.add("taiji_edge_gateway.service")
    return sorted(services)
def health_check(service: str) -> bool:
    try:
        if service == "taiji-gateway.service":
            with urlopen("http://127.0.0.1:8081/health", timeout=5) as r:
                data = json.loads(r.read().decode())
            return r.status == 200 and data.get("gateway") == "online"
        if service == "taiji_edge_gateway.service":
            with urlopen("http://127.0.0.1:9002/healthz", timeout=5) as r:
                data = json.loads(r.read().decode())
            return r.status == 200 and data.get("status") == "ok"
    except Exception:
        return False
    return True


def restore(preimage: Path, changes: dict[str, list[str]], services: list[str]) -> None:
    for rel in changes["created"]:
        target = PROJECT_ROOT / rel
        if target.exists():
            target.unlink()
    for rel in changes["modified"] + changes["deleted"]:
        src = preimage / rel
        if src.exists():
            atomic_copy(src, PROJECT_ROOT / rel)
    for service in services:
        subprocess.run(["sudo", "-n", "systemctl", "restart", service], timeout=30)
def land(shadow: Path, changes: dict[str, list[str]], run_dir: Path, intent: str) -> dict[str, Any]:
    changed = changes["created"] + changes["modified"] + changes["deleted"]
    if changes["deleted"] and not explicit_delete_allowed(intent):
        raise RuntimeError("HOLD_DELETE_NOT_EXPLICIT")
    preimage = run_dir / "preimage"
    preimage.mkdir(parents=True, exist_ok=True)
    for rel in changes["modified"] + changes["deleted"]:
        live = PROJECT_ROOT / rel
        if not live.is_file():
            raise RuntimeError("HOLD_LIVE_PREIMAGE_MISSING")
        atomic_copy(live, preimage / rel)

    for rel in changes["created"] + changes["modified"]:
        atomic_copy(shadow / rel, PROJECT_ROOT / rel)
    for rel in changes["deleted"]:
        (PROJECT_ROOT / rel).unlink()

    services = infer_services(changed)
    try:
        validate_live = validate_candidate(PROJECT_ROOT, {
            "created": changes["created"], "modified": changes["modified"], "deleted": [],
        })
        for service in services:
            p = subprocess.run(["sudo", "-n", "systemctl", "restart", service], timeout=30)
            if p.returncode != 0:
                raise RuntimeError("HOLD_SERVICE_RESTART_FAILED")
            time.sleep(2)
            if not health_check(service):
                raise RuntimeError("HOLD_LIVE_HEALTH_FAILED")
        for rel in changes["created"] + changes["modified"]:
            if sha_file(PROJECT_ROOT / rel) != sha_file(shadow / rel):
                raise RuntimeError("HOLD_LIVE_HASH_MISMATCH")
    except Exception:
        restore(preimage, changes, services)
        raise

    return {
        "state": "ACTIVE_VERIFIED" if services else "LANDED_SOURCE_VERIFIED",
        "changed_files": changed,
        "services_restarted": services,
        "live_validation": validate_live,
        "rollback_preimage": str(preimage.relative_to(PROJECT_ROOT)),
    }


def write_state(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "state.json"
    fd, temp_name = tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=run_dir)
    with os.fdopen(fd, "w", encoding="utf-8") as h:
        json.dump(payload, h, ensure_ascii=False, indent=2)
        h.write("\n")
        h.flush()
        os.fsync(h.fileno())
    os.replace(temp_name, path)
def _append_work_evidence(task_id: str, evidence: dict[str, Any], *, next_action: str | None = None) -> None:
    try:
        ledger = WorkLedger()
        task = next((item for item in ledger.data.get("TASKS", []) if item.get("TASK_ID") == task_id), None)
        if task is None:
            return
        items = list(task.get("D4_EVIDENCE", []))
        items.append(evidence)
        changes: dict[str, Any] = {"D4_EVIDENCE": items}
        if next_action is not None:
            changes["NEXT_ACTION"] = next_action
        ledger.update_task(task_id, **changes)
    except Exception:
        return


def _prepare_action(run_id: str, plan: dict[str, Any], intent_hash: str) -> tuple[ActionLedger, str, str]:
    ledger = ActionLedger()
    task_id = str(plan.get("TASK_ID") or "UNBOUND-NATURAL-LANGUAGE")
    effect_coordinate = (
        f"taiji01:{PROJECT_ROOT}:"
        + ",".join(plan.get("D3_COORDINATE", {}).get("affected_closure", []))
    )
    key = build_idempotency_key(
        task_id=task_id,
        target_coordinate=effect_coordinate,
        operation="natural_language_goal_run",
        intent_hash=intent_hash,
    )
    active_same = next(
        (
            item for item in ledger.data.get("ACTIONS", [])
            if item.get("IDEMPOTENCY_KEY") == key
            and item.get("STATE") not in {"DONE", "FAILED"}
        ),
        None,
    )
    if active_same is not None:
        action_id = str(active_same["ACTION_ID"])
        if active_same.get("STATE") in {"INTERRUPTED", "HOLD"}:
            ledger.resume_action(
                action_id,
                new_process_id=os.getpid(),
                resume_from=str(active_same.get("RESUME_FROM") or "CHECK_ACTUAL_EFFECT_BEFORE_RESUME"),
            )
        else:
            raise RuntimeError(f"HOLD_DUPLICATE_ACTIVE_ACTION:{action_id}")
    else:
        action_id = f"A-NL-{run_id}"
        ledger.begin_action(
            action_id=action_id,
            task_id=task_id,
            turn_id=run_id,
            process_id=os.getpid(),
            target_coordinate=effect_coordinate,
            tool="w7tp_nl_goal_runner",
            idempotency_key=key,
        )
    ledger.update_action(
        action_id,
        RUN_ID=run_id,
        EFFECT_COORDINATE=effect_coordinate,
        RETRY_COUNT=0,
        ROLLBACK_PREIMAGE=None,
        VERIFICATION_RESULT=None,
        RESUME_FROM="LOCAL_MODEL_CANDIDATE",
        LAST_TOOL_EFFECT={"phase": "RUNNER_STARTED", "run_id": run_id},
    )
    return ledger, action_id, task_id


def build_prompt(intent: str, shadow: Path, plan: dict[str, Any]) -> str:
    skill = shadow / ".skill-build" / SKILL_ID / "SKILL.md"
    return f"""Read {skill} and treat it as the task-local 8D ADI control contract.
Do not load or depend on old project AGENTS, old memories, or historical task authority.

Founder natural-language intent:
{intent}

This directory is an ISOLATED SOURCE-ONLY SHADOW of taiji01. It intentionally excludes runtime and evidence history.
Use 8D analysis for understanding/relations and ADI coordinates for localization/comparison.
Separate FACT, HYPOTHESIS, DESIGN, IMPLEMENTATION, LANDING, ACTIVE, and CANONICAL.
Global addressability is not global reading. Follow the affected closure and stop at the first breakpoint.
Reuse/extend/fuse before creating new architecture.
For product/design work include product level and competitor evidence comparison.
Implement the minimum required source delta in this shadow only.
Do not restart services, deploy, push, commit, or modify live paths.
Run proportionate shadow tests. Do not claim ACTIVE or CANONICAL.
Return a concise factual summary of the candidate and verification.

Route plan:
{json.dumps(plan, ensure_ascii=False, sort_keys=True)}
"""
def _json_get(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__}


def current_local_model_route() -> dict[str, Any]:
    return resolve_msi_ollama_url(
        LOCAL_MODEL,
        override_url=LOCAL_OLLAMA_URL_OVERRIDE or None,
        timeout=1.5,
    )


def current_local_ollama_url() -> str:
    route = current_local_model_route()
    selected = route.get("selected_url")
    if not selected:
        raise RuntimeError("HOLD_LOCAL_MODEL_UNREACHABLE")
    return str(selected)


def run_local_transform(intent: str, plan: dict[str, Any], timeout_seconds: int) -> str:
    local_ollama_url = current_local_ollama_url()
    packet = {
        "schema": "W7TP_STATIC_STATE_CELL_READONLY_V1",
        "intent_hash": hashlib.sha256(intent.encode("utf-8")).hexdigest(),
        "TASK_ID": plan.get("TASK_ID"),
        "D3_COORDINATE": plan.get("D3_COORDINATE"),
        "D5_EXECUTION": plan.get("D5_EXECUTION"),
        "observed": {
            "gateway": _json_get("http://127.0.0.1:8081/health"),
            "total_field": _json_get("http://127.0.0.1:8082/healthz"),
            "native_adi": _json_get("http://127.0.0.1:9110/health"),
            "local_models": _json_get(local_ollama_url.rstrip("/") + "/api/tags"),
            "local_model_route": current_local_model_route(),
        },
        "constraints": {
            "read_only": True,
            "no_file_write": True,
            "no_service_restart": True,
            "no_cloud": True,
            "facts_require_observed_field": True,
        },
    }
    prompt = (
        "你是 W7TP 8D ADI 的本地 GPU 語言／狀態轉換器。"
        "只能根據下方 static state cell（靜態狀態原胞）回覆，不得假設未觀測事實。"
        "請用繁體中文精簡回報：目前主要模型來源、是否使用 MSI 本地模型、是否使用 Codex 雲端、"
        "以及是否需要任何實際修改。若不需修改，明確寫 NO_SOURCE_CHANGE。\n\n"
        + json.dumps(packet, ensure_ascii=False, sort_keys=True)
    )
    body = {
        "model": LOCAL_MODEL,
        "messages": [
            {"role": "system", "content": "Facts only from provided state cell. No tools. No hidden reasoning."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.0},
    }
    req = Request(
        local_ollama_url.rstrip("/") + "/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=min(timeout_seconds, 120)) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str((data.get("message") or {}).get("content") or "").strip()


def local_agent_step_budget(plan: dict[str, Any]) -> int:
    resource = plan.get("RESOURCE_DECISION", {})
    profile = (
        resource.get("TASK_PROFILE", {})
        if isinstance(resource, dict)
        else {}
    )
    return 64 if isinstance(profile, dict) and profile.get("complex_code") is True else 32


def run_local_agent(prompt: str, shadow: Path, plan: dict[str, Any], timeout_seconds: int) -> str:
    step_budget = local_agent_step_budget(plan)
    local_ollama_url = current_local_ollama_url()
    cmd = [
        "/usr/bin/python3", str(LOCAL_AGENT),
        "--live-root", str(PROJECT_ROOT),
        "--shadow-root", str(shadow),
        "--allowed-json", json.dumps(closure_paths(plan), ensure_ascii=False),
        "--model", LOCAL_MODEL,
        "--ollama-url", local_ollama_url,
        "--max-steps", str(step_budget),
    ]
    proc = subprocess.run(
        cmd, input=prompt, text=True, capture_output=True,
        timeout=timeout_seconds, cwd=shadow,
    )
    if proc.returncode != 0:
        stderr = str(proc.stderr or "")
        stderr_sha256 = hashlib.sha256(
            stderr.encode("utf-8")
        ).hexdigest()
        if "LOCAL_MODEL_STEP_LIMIT" in stderr:
            code = "HOLD_LOCAL_MODEL_STEP_LIMIT"
        elif "LOCAL_MODEL_CALL_FAILED" in stderr:
            code = "HOLD_LOCAL_MODEL_CALL_FAILED"
        elif "LOCAL_MODEL_STEP_BUDGET_INVALID" in stderr:
            code = "HOLD_LOCAL_MODEL_STEP_BUDGET_INVALID"
        else:
            code = "HOLD_LOCAL_MODEL_AGENT_FAILED"
        raise RuntimeError(
            code + ":stderr_sha256:" + stderr_sha256
        )
    return proc.stdout.strip()


def gemini_task_state_reasoning_hint(
    *,
    intent: str,
    plan: dict[str, Any],
    action_id: str,
    timeout_seconds: int,
) -> dict[str, Any] | None:
    """Issue the current real task packet and obtain one governed Gemini hint."""

    execution = plan.get("D5_EXECUTION", {})
    if (
        not isinstance(execution, dict)
        or execution.get("gemini_a2a_binding")
        != "POINTER_FIRST_TOTAL_FIELD_BOUND"
        or "GEMINI_CODE_ASSIST"
        not in execution.get("bound_reasoning_organs", [])
    ):
        return None
    task_id = str(plan.get("TASK_ID") or "")
    if not task_id:
        raise RuntimeError("HOLD_GEMINI_TASK_PACKET_TASK_ID_MISSING")

    selected = select_task_state_support_refs(
        task_id=task_id,
        current_action_id=action_id,
        max_actions=8,
        max_adi_refs=16,
    )
    issued = issue_task_state_minimum_packet(
        task_id=task_id,
        action_refs=selected["action_refs"],
        support_adi_record_ids=selected["adi_record_ids"],
    )
    packet = issued.get("packet")
    if not isinstance(packet, dict):
        raise RuntimeError("HOLD_GEMINI_TASK_PACKET_ISSUANCE_INVALID")

    broker = TotalFieldDynamicContextPullBroker()
    bootstrap = broker.register(
        packet=packet,
        task_ref=f"task:{task_id}",
        provider_ref=GEMINI_PROVIDER_REF,
        model_ref=GEMINI_MODEL_REF,
        expires_at=(
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ).isoformat(),
        return_coordinate="total-field:candidate-gateway:llm-push",
        context_builder=build_task_model_visible_context,
    )
    instruction = (
        "Analyze the current real task state and the Founder intent below. "
        "Return a candidate-only engineering reasoning object for the local "
        "source builder. Do not claim source-code facts that are not in the "
        "provided task context; the local builder will inspect source "
        "independently. Candidate body should focus on engineering_hypothesis, "
        "implementation_focus, risks, verification_focus, and next_local_step. "
        "Do not request or perform file writes. FOUNDER_INTENT="
        + intent
    )
    result = run_gemini_pointer_first_candidate(
        broker=broker,
        bootstrap=bootstrap,
        task_ref=f"task:{task_id}",
        candidate_instruction=instruction,
        provider_ref=GEMINI_PROVIDER_REF,
        model_ref=GEMINI_MODEL_REF,
        timeout_seconds=min(timeout_seconds, 180),
    )
    if result.get("state") != "PASS_GEMINI_A2A_POINTER_FIRST_CANDIDATE":
        raise RuntimeError("HOLD_GEMINI_TASK_REASONING_NOT_PASS")
    candidate = result.get("candidate")
    if not isinstance(candidate, dict):
        raise RuntimeError("HOLD_GEMINI_TASK_REASONING_CANDIDATE_INVALID")
    total_field = result.get("total_field")
    if not isinstance(total_field, dict):
        raise RuntimeError("HOLD_GEMINI_TASK_REASONING_TOTAL_FIELD_MISSING")
    return {
        "state": "PASS_REAL_TASK_GEMINI_REASONING",
        "task_state_record_id": issued.get("task_state_record_id"),
        "packet_ref": packet.get("packet_ref"),
        "packet_sha256": packet.get("packet_sha256"),
        "bootstrap_sha256": bootstrap.get("bootstrap_sha256"),
        "context_ref": result.get("context_ref"),
        "candidate_sha256": result.get("candidate_sha256"),
        "candidate": candidate.get("candidate"),
        "total_field_decision": total_field.get("final_decision"),
        "total_field_state_ref": total_field.get("state_ref"),
        "total_field_hash": total_field.get("total_field_hash"),
        "provider_reported_model": result.get("provider_reported_model"),
        "provider_internal_context_controlled": result.get(
            "provider_internal_context_controlled"
        ),
        "action_refs": selected["action_refs"],
        "adi_record_ids": selected["adi_record_ids"],
    }


def legacy_google_fallback_allowed(plan: dict[str, Any]) -> bool:
    """Legacy direct cloud hint path is forbidden under pointer-first context."""

    execution = plan.get("D5_EXECUTION", {})
    return not (
        isinstance(execution, dict)
        and execution.get("context_delivery_mode")
        == "TOTAL_FIELD_POINTER_FIRST_DYNAMIC_CONTEXT_PULL"
    )


def google_candidate_hint(intent: str, plan: dict[str, Any], run_dir: Path) -> dict[str, Any] | None:
    if not (GEMINI_PACKET.is_file() and VERTEX_GATEWAY.is_file()):
        return None
    packet_proc = subprocess.run(
        ["/usr/bin/python3", str(GEMINI_PACKET), "--task", intent,
         "--intent-code", "natural_language_development", "--pretty"],
        text=True, capture_output=True, timeout=30, cwd=PROJECT_ROOT,
    )
    if packet_proc.returncode != 0:
        return None
    try:
        packet = json.loads(packet_proc.stdout)
    except json.JSONDecodeError:
        return None
    safe_request = {
        "schema": "W7TP_NL_DEV_GOOGLE_CANDIDATE_HINT_V1",
        "intent_hash": hashlib.sha256(intent.encode("utf-8")).hexdigest(),
        "affected_closure": closure_paths(plan),
        "cloud_candidate_request": packet.get("cloud_candidate_request", {}),
        "instruction": (
            "Return candidate-only engineering hypotheses and a minimal implementation approach. "
            "Do not claim facts, deployment, authority, or source-code state not present in this packet."
        ),
    }
    out = run_dir / "google_candidate"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="w7tp-google-hint-") as td:
        prompt_path = Path(td) / "prompt.json"
        prompt_path.write_text(json.dumps(safe_request, ensure_ascii=False), encoding="utf-8")
        env = os.environ.copy()
        env["FOUNDER_EXPLICIT_CLOUD_AUTHORIZATION"] = "YES"
        proc = subprocess.run(
            ["/usr/bin/python3", str(VERTEX_GATEWAY),
             "--prompt-file", str(prompt_path), "--output-dir", str(out)],
            text=True, capture_output=True, timeout=180, cwd=PROJECT_ROOT, env=env,
        )
    if proc.returncode != 0:
        return None
    normalized = out / "CLOUD_NORMALIZED_CANDIDATE.json"
    if not normalized.is_file():
        return None
    try:
        data = json.loads(normalized.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data.get("candidate") if isinstance(data, dict) else None


def main() -> int:
    if len(sys.argv) < 3:
        return 2
    run_id = sys.argv[1]
    timeout_seconds = int(sys.argv[2])
    intent = sys.stdin.read()
    if not intent.strip():
        return 2

    run_dir = STATE_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    intent_hash = hashlib.sha256(intent.encode("utf-8")).hexdigest()
    plan_path = run_dir / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    try:
        action_ledger, action_id, task_id = _prepare_action(run_id, plan, intent_hash)
    except Exception as exc:
        write_state(run_dir, {
            "run_id": run_id,
            "state": str(exc),
            "started_at": now(),
            "finished_at": now(),
            "intent_hash": intent_hash,
            "prompt_persisted": False,
            "error_type": type(exc).__name__,
        })
        return 1

    state: dict[str, Any] = {
        "run_id": run_id, "action_id": action_id, "task_id": task_id,
        "process_id": os.getpid(),
        "state": "RUNNING", "started_at": now(),
        "intent_hash": intent_hash, "prompt_persisted": False,
        "runner_unit": f"w7tp-nl-run-{run_id[:16]}.service",
        "runner_isolation": "SYSTEMD_TRANSIENT_SERVICE",
    }
    write_state(run_dir, state)
    shadow = Path(tempfile.mkdtemp(prefix=f"w7tp-nl-shadow-{run_id}-"))
    phase = "AFFECTED_CLOSURE"
    try:
        selected_builder = plan.get("D5_EXECUTION", {}).get(
            "selected_candidate_builder"
        )
        if selected_builder != "MSI_OLLAMA_LOCAL":
            raise RuntimeError("HOLD_SELECTED_CANDIDATE_BUILDER_UNAVAILABLE")
        copied_closure = copy_source_snapshot(shadow, plan)
        if not copied_closure:
            raise RuntimeError("HOLD_AFFECTED_CLOSURE_NOT_LOCATED")
        action_ledger.update_action(
            action_id,
            LAST_TOOL_EFFECT={"phase": "AFFECTED_CLOSURE_LOCATED", "paths": copied_closure},
            RESUME_FROM="GEMINI_TASK_STATE_REASONING_OR_LOCAL_MODEL",
        )
        before = snapshot(shadow)
        prompt = build_prompt(intent, shadow, plan)
        gemini_reasoning: dict[str, Any] | None = None
        gemini_reasoning_used = False
        gemini_reasoning_hold: str | None = None
        google_candidate_used = False

        if effectful_intent(intent):
            phase = "GEMINI_TASK_STATE_REASONING"
            try:
                gemini_reasoning = gemini_task_state_reasoning_hint(
                    intent=intent,
                    plan=plan,
                    action_id=action_id,
                    timeout_seconds=timeout_seconds,
                )
                if gemini_reasoning is not None:
                    gemini_reasoning_used = True
                    google_candidate_used = True
                    action_ledger.update_action(
                        action_id,
                        LAST_TOOL_EFFECT={
                            "phase": "GEMINI_TASK_STATE_REASONING_PASS",
                            "task_state_record_id": gemini_reasoning.get(
                                "task_state_record_id"
                            ),
                            "packet_ref": gemini_reasoning.get("packet_ref"),
                            "packet_sha256": gemini_reasoning.get("packet_sha256"),
                            "context_ref": gemini_reasoning.get("context_ref"),
                            "candidate_sha256": gemini_reasoning.get(
                                "candidate_sha256"
                            ),
                            "total_field_decision": gemini_reasoning.get(
                                "total_field_decision"
                            ),
                            "total_field_hash": gemini_reasoning.get(
                                "total_field_hash"
                            ),
                            "provider_reported_model": gemini_reasoning.get(
                                "provider_reported_model"
                            ),
                        },
                        RESUME_FROM="LOCAL_MODEL_CANDIDATE",
                    )
                    prompt += (
                        "\n\nA Total Field-adjudicated Gemini candidate-only "
                        "reasoning result derived from the current real task-state "
                        "Origin-State Minimum Packet is available below. It has no "
                        "source-write or execution authority. Treat it only as a "
                        "hypothesis/design aid. Independently inspect the allowed "
                        "shadow source and implement only locally justified changes.\n"
                        "GEMINI_REAL_TASK_REASONING_CANDIDATE:\n"
                        + json.dumps(
                            gemini_reasoning.get("candidate"),
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
            except Exception as exc:
                gemini_reasoning_hold = str(exc)
                action_ledger.update_action(
                    action_id,
                    LAST_TOOL_EFFECT={
                        "phase": "GEMINI_TASK_STATE_REASONING_HOLD_LOCAL_FALLBACK",
                        "error": gemini_reasoning_hold,
                    },
                    RESUME_FROM="LOCAL_MODEL_CANDIDATE",
                )

            phase = "LOCAL_MODEL_CANDIDATE"
            last_message = run_local_agent(
                prompt,
                shadow,
                plan,
                timeout_seconds,
            )
        else:
            phase = "LOCAL_GPU_READONLY_TRANSFORM"
            action_ledger.update_action(
                action_id,
                LAST_TOOL_EFFECT={"phase": phase, "model": LOCAL_MODEL},
                RESUME_FROM="COMPLETE_READONLY_OBSERVATION",
            )
            last_message = run_local_transform(intent, plan, timeout_seconds)
        after = snapshot(shadow)
        changes = diff_snapshot(before, after)
        changed = changes["created"] + changes["modified"] + changes["deleted"]
        retry_count = 0
        action_ledger.update_action(
            action_id,
            LAST_TOOL_EFFECT={
                "phase": phase,
                "candidate_changes": changes,
                "model": LOCAL_MODEL,
                "gemini_a2a_reasoning_used": gemini_reasoning_used,
                "gemini_candidate_sha256": (
                    gemini_reasoning.get("candidate_sha256")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_reasoning_hold": gemini_reasoning_hold,
            },
            RESUME_FROM="VERIFY_OR_RESOURCE_ARBITRATION",
        )

        if not changed and effectful_intent(intent):
            retry_count = 1
            retry_prompt = prompt + """

The first local-model pass produced NO SOURCE DELTA. For this effectful intent that is not completion.
Re-open the exact target source using tools, stage only the minimum path, implement the requested
change in the shadow, run deterministic checks, and do not stop at analysis or recommendation.
"""
            retry_message = run_local_agent(retry_prompt, shadow, plan, timeout_seconds)
            if retry_message.strip():
                last_message = retry_message
            after = snapshot(shadow)
            changes = diff_snapshot(before, after)
            changed = changes["created"] + changes["modified"] + changes["deleted"]

        if (
            not changed
            and effectful_intent(intent)
            and bool(plan.get("D5_EXECUTION", {}).get("google_candidate_fallback"))
            and legacy_google_fallback_allowed(plan)
        ):
            cloud_hint = google_candidate_hint(intent, plan, run_dir)
            if cloud_hint is not None:
                google_candidate_used = True
                retry_count += 1
                cloud_retry = prompt + """

A Google Vertex/Gemini candidate-only reasoning hint is available below.
It has NO authority and contains no verified source-state claims.
Use it only as a hypothesis/design aid. Re-read local source with tools, independently verify,
then implement only the minimum locally justified source delta in the shadow.

GOOGLE_CANDIDATE_HINT:
""" + json.dumps(cloud_hint, ensure_ascii=False, sort_keys=True)
                cloud_message = run_local_agent(cloud_retry, shadow, plan, timeout_seconds)
                if cloud_message.strip():
                    last_message = cloud_message
                after = snapshot(shadow)
                changes = diff_snapshot(before, after)
                changed = changes["created"] + changes["modified"] + changes["deleted"]

        phase = "VERIFY_CANDIDATE"
        action_ledger.update_action(
            action_id,
            RETRY_COUNT=retry_count,
            LAST_TOOL_EFFECT={
                "phase": "CANDIDATE_READY_FOR_VERIFY",
                "candidate_changes": changes,
                "google_candidate_used": google_candidate_used,
                "gemini_a2a_reasoning_used": gemini_reasoning_used,
                "gemini_task_state_record_id": (
                    gemini_reasoning.get("task_state_record_id")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_candidate_sha256": (
                    gemini_reasoning.get("candidate_sha256")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_reasoning_hold": gemini_reasoning_hold,
            },
            RESUME_FROM="VERIFY_CANDIDATE",
        )
        deterministic = validate_candidate(shadow, changes)
        action_ledger.update_action(
            action_id,
            VERIFICATION_RESULT=deterministic,
            RETRY_COUNT=retry_count,
            RESUME_FROM=(
                "TOTAL_FIELD_SOURCE_DELTA_ADJUDICATION"
                if changed
                else "COMPLETE_OR_HOLD_NO_EFFECT"
            ),
        )
        if not changed:
            final_state = (
                "HOLD_NO_IMPLEMENTATION_EFFECT"
                if effectful_intent(intent)
                else "PASS_NO_SOURCE_CHANGE"
            )
            final = {
                **state, "state": final_state,
                "finished_at": now(),
                "retry_count": retry_count,
                "model_provider": "MSI_OLLAMA_LOCAL",
                "model": LOCAL_MODEL,
                "google_candidate_used": google_candidate_used,
                "gemini_a2a_reasoning_used": gemini_reasoning_used,
                "gemini_task_state_record_id": (
                    gemini_reasoning.get("task_state_record_id")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_candidate_sha256": (
                    gemini_reasoning.get("candidate_sha256")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_reasoning_hold": gemini_reasoning_hold,
                "codex_used": False,
                "agent_output_sha256": sha_bytes(last_message.encode("utf-8")),
                "candidate_changes": changes,
                "deterministic_validation": deterministic,
            }
            if effectful_intent(intent):
                action_ledger.update_action(
                    action_id,
                    STATE="HOLD",
                    RETRY_COUNT=retry_count,
                    LAST_CONFIRMED_EFFECT={"live_effect": False, "source_delta": False},
                    LAST_TOOL_EFFECT={"phase": "NO_IMPLEMENTATION_EFFECT", "google_candidate_used": google_candidate_used},
                    RESUME_FROM="RESOURCE_ARBITRATION_OR_FIRST_BREAKPOINT",
                    VERIFICATION_RESULT=deterministic,
                    ERROR="HOLD_NO_IMPLEMENTATION_EFFECT",
                )
                _append_work_evidence(
                    task_id,
                    {"ACTION_ID": action_id, "RUN_ID": run_id, "STATE": "HOLD_NO_IMPLEMENTATION_EFFECT"},
                    next_action=f"Resume {action_id} from RESOURCE_ARBITRATION_OR_FIRST_BREAKPOINT",
                )
            else:
                action_ledger.update_action(
                    action_id,
                    RETRY_COUNT=retry_count,
                    VERIFICATION_RESULT=deterministic,
                    LAST_TOOL_EFFECT={"phase": "NO_SOURCE_CHANGE_REQUIRED"},
                )
                action_ledger.complete_action(
                    action_id,
                    confirmed_effect={
                        "state": "PASS_NO_SOURCE_CHANGE",
                        "live_effect": False,
                        "verification": deterministic,
                    },
                )
                _append_work_evidence(
                    task_id,
                    {"ACTION_ID": action_id, "RUN_ID": run_id, "STATE": "DONE_NO_SOURCE_CHANGE"},
                )
        else:
            phase = "TOTAL_FIELD_SOURCE_DELTA_ADJUDICATION"
            total_field_gate = _total_field_source_delta_gate(
                run_id=run_id,
                intent_hash=intent_hash,
                before=before,
                after=after,
                changes=changes,
                deterministic_validation=deterministic,
            )
            action_ledger.update_action(
                action_id,
                RETRY_COUNT=retry_count,
                VERIFICATION_RESULT=deterministic,
                LAST_TOOL_EFFECT={
                    "phase": "TOTAL_FIELD_SOURCE_DELTA_ADJUDICATED",
                    "candidate_changes": changes,
                    "total_field_gate": total_field_gate,
                },
                RESUME_FROM="LAND_CANDIDATE",
            )
            phase = "LAND_CANDIDATE"
            landing = land(shadow, changes, run_dir, intent)
            final = {
                **state, **landing, "finished_at": now(),
                "retry_count": retry_count,
                "model_provider": "MSI_OLLAMA_LOCAL",
                "model": LOCAL_MODEL,
                "google_candidate_used": google_candidate_used,
                "gemini_a2a_reasoning_used": gemini_reasoning_used,
                "gemini_task_state_record_id": (
                    gemini_reasoning.get("task_state_record_id")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_candidate_sha256": (
                    gemini_reasoning.get("candidate_sha256")
                    if isinstance(gemini_reasoning, dict)
                    else None
                ),
                "gemini_reasoning_hold": gemini_reasoning_hold,
                "codex_used": False,
                "agent_output_sha256": sha_bytes(last_message.encode("utf-8")),
                "candidate_changes": changes,
                "deterministic_validation": deterministic,
                "total_field_source_delta_gate": total_field_gate,
            }
            action_ledger.update_action(
                action_id,
                RETRY_COUNT=retry_count,
                ROLLBACK_PREIMAGE=landing.get("rollback_preimage"),
                VERIFICATION_RESULT=landing.get("live_validation") or deterministic,
                LAST_TOOL_EFFECT={
                    "phase": "LANDED_REOBSERVED",
                    "changed_files": landing.get("changed_files", []),
                    "services_restarted": landing.get("services_restarted", []),
                },
            )
            action_ledger.complete_action(
                action_id,
                confirmed_effect={
                    "state": landing.get("state"),
                    "changed_files": landing.get("changed_files", []),
                    "services_restarted": landing.get("services_restarted", []),
                    "verification": landing.get("live_validation") or deterministic,
                    "total_field_source_delta_gate": total_field_gate,
                    "gemini_a2a_reasoning_used": gemini_reasoning_used,
                    "gemini_task_state_record_id": (
                        gemini_reasoning.get("task_state_record_id")
                        if isinstance(gemini_reasoning, dict)
                        else None
                    ),
                    "gemini_candidate_sha256": (
                        gemini_reasoning.get("candidate_sha256")
                        if isinstance(gemini_reasoning, dict)
                        else None
                    ),
                    "gemini_reasoning_hold": gemini_reasoning_hold,
                    "rollback_preimage": landing.get("rollback_preimage"),
                },
            )
            _append_work_evidence(
                task_id,
                {
                    "ACTION_ID": action_id,
                    "RUN_ID": run_id,
                    "STATE": "DONE",
                    "LANDING_STATE": landing.get("state"),
                    "CHANGED_FILES": landing.get("changed_files", []),
                    "TOTAL_FIELD_DECISION": total_field_gate.get("final_decision"),
                    "TOTAL_FIELD_STATE_REF": total_field_gate.get("state_ref"),
                    "GEMINI_A2A_REASONING_USED": gemini_reasoning_used,
                    "GEMINI_TASK_STATE_RECORD_ID": (
                        gemini_reasoning.get("task_state_record_id")
                        if isinstance(gemini_reasoning, dict)
                        else None
                    ),
                    "GEMINI_CANDIDATE_SHA256": (
                        gemini_reasoning.get("candidate_sha256")
                        if isinstance(gemini_reasoning, dict)
                        else None
                    ),
                },
            )
        write_state(run_dir, final)
        return 0
    except Exception as exc:
        try:
            if phase == "LAND_CANDIDATE":
                action_ledger.mark_interrupted(
                    action_id,
                    error=str(exc),
                    last_confirmed_effect=None,
                    last_tool_effect={"phase": phase, "error_type": type(exc).__name__},
                    resume_from="CHECK_ACTUAL_EFFECT_BEFORE_RESUME",
                )
            else:
                action_ledger.update_action(
                    action_id,
                    STATE="HOLD",
                    ERROR=str(exc),
                    LAST_TOOL_EFFECT={"phase": phase, "error_type": type(exc).__name__},
                    RESUME_FROM=phase,
                )
            _append_work_evidence(
                task_id,
                {"ACTION_ID": action_id, "RUN_ID": run_id, "STATE": "INTERRUPTED" if phase == "LAND_CANDIDATE" else "HOLD", "ERROR": str(exc)},
                next_action=f"Resume {action_id} from " + ("CHECK_ACTUAL_EFFECT_BEFORE_RESUME" if phase == "LAND_CANDIDATE" else phase),
            )
        except Exception:
            pass
        final = {
            **state, "state": str(exc),
            "finished_at": now(),
            "error_type": type(exc).__name__,
        }
        write_state(run_dir, final)
        return 1
    finally:
        shutil.rmtree(shadow, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
