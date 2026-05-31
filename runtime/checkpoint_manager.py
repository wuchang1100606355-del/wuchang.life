import json
import os
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")
REGISTRY = f"{BASE}/registry/runtime_registry.json"

def load_registry():
    with open(REGISTRY, "r") as f:
        return json.load(f)

def save_registry(data):
    with open(REGISTRY, "w") as f:
        json.dump(data, f, indent=2)

def create_checkpoint(state):

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    checkpoint_file = f"{BASE}/checkpoints/{ts}.json"

    with open(checkpoint_file, "w") as f:
        json.dump(state, f, indent=2)

    registry = load_registry()

    registry["last_boot"] = ts
    registry["active_checkpoint"] = checkpoint_file
    registry["runtime_status"] = "CHECKPOINT_SAVED"

    save_registry(registry)

    print(f"[✓] Checkpoint saved: {checkpoint_file}")

def restore_checkpoint():

    registry = load_registry()

    checkpoint = registry.get("active_checkpoint")

    if not checkpoint:
        print("[!] No checkpoint found")
        return None

    if not os.path.exists(checkpoint):
        print("[!] Checkpoint file missing")
        return None

    with open(checkpoint, "r") as f:
        state = json.load(f)

    print(f"[✓] Restored checkpoint: {checkpoint}")

    return state

if __name__ == "__main__":

    state = {
        "agents": ["mu_0", "mu_1", "mu_2"],
        "ports": [8000, 9004, 9090],
        "status": "ACTIVE"
    }

    create_checkpoint(state)

    restored = restore_checkpoint()

    print(restored)
