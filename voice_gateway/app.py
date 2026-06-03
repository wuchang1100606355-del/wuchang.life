from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os, time, requests

CLAW_URL = os.getenv("CLAW_URL", "http://host.docker.internal:9004")
APP_VERSION = "voice_gateway_v0.1"

app = FastAPI(title="Taiji Voice Gateway", version=APP_VERSION)

class VoiceTask(BaseModel):
    text: str
    speaker: Optional[str] = "pos_voice"
    source_node: Optional[str] = "v3-mix-edla-gl"
    mode: Optional[str] = "dry_run"
    metadata: Dict[str, Any] = {}

@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "service": "taiji_voice_gateway",
        "version": APP_VERSION,
        "claw_url": CLAW_URL,
        "time": time.time()
    }

@app.post("/v1/voice/task")
def voice_task(req: VoiceTask):
    envelope = {
        "task_id": f"voice-{int(time.time())}",
        "action": "voice_task_intake",
        "resource_hint": "pos_voice_edge",
        "scope": ["voice", "task_envelope", "claw_dry_run"],
        "actor": req.speaker,
        "dry_run": True,
        "payload": {
            "mutates_system": False,
            "requires_shell": False,
            "source_node": req.source_node,
            "voice_text": req.text,
            "metadata": req.metadata
        }
    }

    r = requests.post(
        f"{CLAW_URL}/v1/tasks/dry-run",
        json=envelope,
        timeout=5
    )

    return {
        "ok": True,
        "received_text": req.text,
        "task_envelope": envelope,
        "claw_status": r.status_code,
        "claw_response": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
    }
