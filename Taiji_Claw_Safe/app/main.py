from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_NAME = "Taiji Claw Safe"
AUDIT_DIR = Path("/mnt/audit")
QUEUE_DIR = Path("/mnt/queue")
CURRENT_DIR = Path("/mnt/current")
INDEX_DIR = Path("/mnt/indexes")

AUDIT_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME, version="0.1.0")

FORBIDDEN_ACTIONS = {
    "read_private_key",
    "read_env",
    "grant_owner",
    "grant_super_admin",
    "modify_domain_wide_delegation",
    "make_public_share",
    "enable_google_ads",
    "delete_account",
    "delete_audit_logs",
    "export_global_user_data",
    "mount_host_root",
}

L2_ACTIONS = {
    "create_shared_drive",
    "modify_group_membership",
    "upload_archive_bundle",
    "change_private_permissions",
    "create_service_account",
}

L1_ACTIONS = {
    "create_folder",
    "write_report",
    "create_draft",
    "generate_manifest",
    "queue_task",
}

L0_ACTIONS = {
    "health_check",
    "list_current_files",
    "list_indexes",
    "read_current_state",
    "classify",
    "dry_run",
}


class TaskEnvelope(BaseModel):
    task_id: str = Field(..., min_length=3)
    action: str
    resource_hint: Optional[str] = None
    scope: List[str] = []
    payload: Dict[str, Any] = {}
    confirmation_token: Optional[str] = None
    actor: str = "local_ai"
    dry_run: bool = True


def sha256_obj(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_action(action: str) -> Dict[str, Any]:
    if action in FORBIDDEN_ACTIONS:
        return {"level": "L3_NO_AUTOMATION", "allowed": False, "requires_confirmation": False}
    if action in L2_ACTIONS:
        return {"level": "L2_CONFIRM_REQUIRED", "allowed": True, "requires_confirmation": True}
    if action in L1_ACTIONS:
        return {"level": "L1_LOW_RISK", "allowed": True, "requires_confirmation": False}
    if action in L0_ACTIONS:
        return {"level": "L0_READONLY", "allowed": True, "requires_confirmation": False}
    return {"level": "L2_CONFIRM_REQUIRED", "allowed": True, "requires_confirmation": True}


def audit(event: Dict[str, Any]) -> Dict[str, Any]:
    event["timestamp"] = now_iso()
    event["event_hash"] = sha256_obj(event)
    p = AUDIT_DIR / f"{event['timestamp'].replace(':','-')}_{event['event_hash'][:16]}.json"
    p.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return event


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": APP_NAME,
        "mode": "safe_broker",
        "host_root_mounted": Path("/host_root").exists(),
        "current_dir": str(CURRENT_DIR),
        "index_dir": str(INDEX_DIR),
        "audit_dir": str(AUDIT_DIR),
        "queue_dir": str(QUEUE_DIR),
    }


@app.post("/v1/tasks/classify")
def classify(task: TaskEnvelope):
    c = classify_action(task.action)
    result = {
        "task_id": task.task_id,
        "action": task.action,
        "classification": c,
        "task_hash": sha256_obj(task.model_dump()),
    }
    audit({"type": "classify", "result": result})
    return result


@app.post("/v1/tasks/dry-run")
def dry_run(task: TaskEnvelope):
    c = classify_action(task.action)
    result = {
        "task_id": task.task_id,
        "action": task.action,
        "classification": c,
        "would_execute": c["allowed"] and c["level"] != "L3_NO_AUTOMATION",
        "requires_confirmation": c["requires_confirmation"],
        "resource_hint": task.resource_hint,
        "scope": task.scope,
        "task_hash": sha256_obj(task.model_dump()),
    }
    audit({"type": "dry_run", "result": result})
    return result


@app.post("/v1/tasks/execute")
def execute(task: TaskEnvelope):
    c = classify_action(task.action)

    if c["level"] == "L3_NO_AUTOMATION":
        event = {"type": "blocked_execute", "reason": "L3 forbidden", "task": task.model_dump(), "classification": c}
        audit(event)
        raise HTTPException(status_code=403, detail=event)

    if c["requires_confirmation"] and task.confirmation_token != "CONFIRM_L2":
        event = {"type": "need_confirmation", "task": task.model_dump(), "classification": c}
        audit(event)
        raise HTTPException(status_code=409, detail=event)

    if task.dry_run:
        return dry_run(task)

    queued = {
        "task_id": task.task_id,
        "action": task.action,
        "status": "QUEUED_SAFE_NO_REAL_CLOUD_EXECUTION",
        "classification": c,
        "task_hash": sha256_obj(task.model_dump()),
        "note": "MVP only queues; real Google/Odoo execution not connected yet."
    }

    q = QUEUE_DIR / f"{task.task_id}_{queued['task_hash'][:12]}.json"
    q.write_text(json.dumps(queued, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit({"type": "execute_queued", "result": queued})
    return queued


@app.get("/v1/audit")
def list_audit():
    files = sorted(AUDIT_DIR.glob("*.json"), reverse=True)[:50]
    return {"count": len(files), "files": [f.name for f in files]}
