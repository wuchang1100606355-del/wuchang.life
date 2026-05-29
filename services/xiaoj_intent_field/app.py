from fastapi import FastAPI
from datetime import datetime, timezone
app = FastAPI(title="XiaoJ Intent Field")

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "xiaoj-intent-field"}

@app.get("/state")
def state():
    return {
        "intent_field_loaded": True,
        "memory_field_loaded": True,
        "topology_field_loaded": True,
        "policy_gate_active": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/intent-field/status")
def status():
    return {
        "service_name": "xiaoj-intent-field",
        "mode": "containerized_intent_field",
        "governance": "local_first_human_reviewed",
        "hardwalls_enabled": True,
        "cloud_allowed": False,
        "pii_allowed": False,
        "secrets_allowed": False,
    }
