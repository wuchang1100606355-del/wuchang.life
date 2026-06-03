from pathlib import Path
import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
TOPO = ROOT / "configs" / "taiji_topology.json"
LEDGER = ROOT / "runtime" / "ledger" / "routing_decisions.jsonl"
DEAD = ROOT / "runtime" / "dead_letter" / "routing_rejected.jsonl"

router = APIRouter(prefix="/taiji", tags=["taiji-topology"])

class RouteRequest(BaseModel):
    task_class: str
    action: str
    payload_summary: str = ""
    authority_level: int = 1
    human_online: bool = False
    preferred_node: str | None = None

def append_jsonl(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_topology():
    if not TOPO.exists():
        raise HTTPException(status_code=500, detail="missing taiji_topology.json")
    return json.loads(TOPO.read_text(encoding="utf-8"))

@router.get("/topology")
def topology():
    return load_topology()

@router.get("/topology/summary")
def topology_summary():
    topo = load_topology()
    return {
        "owner": topo.get("owner"),
        "version": topo.get("version"),
        "layers": list(topo.get("layers", {}).keys()),
        "services": topo.get("services", {}),
        "nodes": list(topo.get("nodes", {}).keys()),
        "hard_denies": topo.get("hard_denies", [])
    }

@router.post("/route/decide")
def route_decide(req: RouteRequest):
    topo = load_topology()

    if req.action in topo.get("hard_denies", []):
        rejected = {
            "ts": time.time(),
            "event": "route_rejected",
            "reason": "hard_denied_action",
            "request": req.model_dump()
        }
        append_jsonl(DEAD, rejected)
        raise HTTPException(status_code=403, detail=rejected)

    nodes = topo.get("nodes", {})
    selected = None

    if req.preferred_node and req.preferred_node in nodes:
        selected = req.preferred_node
    elif req.task_class in ["topology_compute", "metric_tensor", "local_llm"]:
        selected = "taiji01"
    elif req.task_class in ["chat", "ui"]:
        selected = "openwebui"
    elif req.task_class in ["property_case", "pos", "finance_record"]:
        selected = "odoo"
    elif req.task_class in ["heartbeat", "sensing", "environment_state"]:
        selected = "sensor"
    else:
        selected = "taiji01"

    node = nodes.get(selected)
    if not node:
        rejected = {
            "ts": time.time(),
            "event": "route_rejected",
            "reason": "no_selected_node",
            "request": req.model_dump()
        }
        append_jsonl(DEAD, rejected)
        raise HTTPException(status_code=404, detail=rejected)

    if req.authority_level > int(node.get("max_authority_level", 0)):
        rejected = {
            "ts": time.time(),
            "event": "route_rejected",
            "reason": "authority_level_exceeds_node",
            "selected_node": selected,
            "request": req.model_dump()
        }
        append_jsonl(DEAD, rejected)
        raise HTTPException(status_code=403, detail=rejected)

    decision = {
        "ts": time.time(),
        "event": "route_decided",
        "task_class": req.task_class,
        "action": req.action,
        "selected_node": selected,
        "authority_level": req.authority_level,
        "human_online": req.human_online,
        "payload_summary": req.payload_summary
    }
    append_jsonl(LEDGER, decision)
    return decision
