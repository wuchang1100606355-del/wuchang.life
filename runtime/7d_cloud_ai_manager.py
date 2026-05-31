import json
import pathlib
import datetime
import socket

ROOT = pathlib.Path.home() / "Taiji_Hub"
POLICY = ROOT / "policies/7d_cloud_ai_policy.json"
STATE = ROOT / "state/runtime_7d_state.json"
PACKET = ROOT / "state/runtime_7d_packet.example.json"
LOG = ROOT / "logs/7d_cloud_ai_management.jsonl"

def port_open(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.35)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

policy = json.loads(POLICY.read_text(encoding="utf-8"))
state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
packet = json.loads(PACKET.read_text(encoding="utf-8")) if PACKET.exists() else {}

ports = {
    "five_metric_8105": port_open(8105),
    "odoo_8069": port_open(8069),
    "ollama_11434": port_open(11434),
    "mu_1_gateway_9004": port_open(9004),
    "formal_tensor_runtime_8126": port_open(8126)
}

payload_class = packet.get("packet_type", "runtime_state_capsule")
risk = packet.get("metric", {}).get("risk", 0.99)
formation = packet.get("formation", "UNKNOWN")

if not ports["five_metric_8105"]:
    decision = "BLOCK_CLOUD_ROUTE_NO_METRIC_GATE"
elif risk >= 0.8:
    decision = "BLOCK_CLOUD_ROUTE_HIGH_RISK"
elif payload_class == "runtime_state_capsule":
    decision = "ALLOW_CLOUD_DERIVATION_MASKED_PACKET_ONLY"
else:
    decision = "LOCAL_ONLY_REVIEW_REQUIRED"

result = {
    "event": "7d_cloud_ai_management_check",
    "time": now,
    "runtime": "7D",
    "policy": policy["policy_name"],
    "node": "MSI",
    "formation": formation,
    "payload_class": payload_class,
    "risk": risk,
    "ports": ports,
    "decision": decision,
    "cloud_ai_authority": "external_derivation_only",
    "cloud_direct_write": False,
    "cloud_direct_odoo_modify": False,
    "cloud_raw_private_data_access": False
}

LOG.parent.mkdir(parents=True, exist_ok=True)
with LOG.open("a", encoding="utf-8") as f:
    f.write(json.dumps(result, ensure_ascii=False) + "\n")

print(json.dumps(result, ensure_ascii=False, indent=2))
