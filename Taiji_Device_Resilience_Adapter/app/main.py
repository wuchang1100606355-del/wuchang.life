from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import hashlib
import json
import os
import shutil
import time

APP_NAME = "Taiji Device Resilience Adapter"

BASE_DIR = Path("/mnt/device")
INCOMING = BASE_DIR / "incoming"
COMPLETED = BASE_DIR / "completed"
FAILED = BASE_DIR / "failed"
AUDIT = Path("/mnt/audit")

for p in [INCOMING, COMPLETED, FAILED, AUDIT]:
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME, version="0.1.0")


class FileTask(BaseModel):
    task_id: str = Field(..., min_length=3)
    content: str = Field(..., min_length=1)
    source: str = "device_resilience_adapter"
    metadata: Dict[str, Any] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def audit(event: Dict[str, Any]):
    event["timestamp"] = now_iso()
    event["event_hash"] = sha256_text(json.dumps(event, ensure_ascii=False, sort_keys=True))
    p = AUDIT / f"{event['timestamp'].replace(':','-')}_{event['event_hash'][:16]}.json"
    p.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return event


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": APP_NAME,
        "incoming": str(INCOMING),
        "completed": str(COMPLETED),
        "failed": str(FAILED),
        "audit": str(AUDIT),
        "recording": False,
        "host_root_mounted": Path("/host_root").exists()
    }


@app.post("/v1/file-task")
def create_file_task(t: FileTask):
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in t.task_id)
    h = sha256_text(t.content)
    target = INCOMING / f"{safe_id}_{h[:12]}.txt"
    processing = Path(str(target) + ".processing")

    if target.exists() or processing.exists():
        raise HTTPException(status_code=409, detail="task_already_exists")

    target.write_text(t.content, encoding="utf-8")

    event = audit({
        "type": "file_task_created",
        "task_id": t.task_id,
        "content_hash": h,
        "source": t.source,
        "metadata": t.metadata,
        "path": str(target)
    })

    return {
        "ok": True,
        "task_id": t.task_id,
        "content_hash": h,
        "path": str(target),
        "audit_hash": event["event_hash"]
    }


@app.post("/v1/file-task/{name}/mark-completed")
def mark_completed(name: str):
    src = INCOMING / name
    if not src.exists():
        raise HTTPException(status_code=404, detail="not_found")

    processing = Path(str(src) + ".processing")
    os.rename(src, processing)

    try:
        dst = COMPLETED / name
        shutil.move(str(processing), str(dst))
        event = audit({"type": "file_task_completed", "name": name, "dst": str(dst)})
        return {"ok": True, "dst": str(dst), "audit_hash": event["event_hash"]}
    except Exception as e:
        try:
            if processing.exists():
                os.rename(processing, src)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/queue")
def queue_status():
    return {
        "incoming": sorted([p.name for p in INCOMING.glob("*.txt")]),
        "processing": sorted([p.name for p in INCOMING.glob("*.processing")]),
        "completed_count": len(list(COMPLETED.glob("*"))),
        "failed_count": len(list(FAILED.glob("*")))
    }
