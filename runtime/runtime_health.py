import os
import json
import time
import socket
import subprocess
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

REGISTRY = f"{BASE}/registry/runtime_registry.json"
METRICS = f"{BASE}/metrics/runtime_health.json"

def pid_alive(name):

    try:
        out = subprocess.check_output(
            f"pgrep -f '{name}'",
            shell=True
        ).decode().strip()

        return bool(out)

    except:
        return False

def port_alive(port):

    s = socket.socket()

    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True

    except:
        return False

while True:

    try:

        with open(REGISTRY, "r") as f:
            registry = json.load(f)

    except:
        registry = {}

    health = {

        "timestamp": datetime.utcnow().isoformat(),

        "gateway_alive":
            pid_alive("uvicorn"),

        "gateway_port_8081":
            port_alive(8081),

        "deadletter_alive":
            pid_alive("deadletter_replay.py"),

        "checkpoint_manager":
            os.path.exists(
                f"{BASE}/checkpoint_manager.py"
            ),

        "restore_runtime":
            os.path.exists(
                f"{BASE}/restore_runtime.py"
            ),

        "runtime_status":
            registry.get("runtime_status"),

        "active_checkpoint":
            registry.get("active_checkpoint"),

        "last_boot":
            registry.get("last_boot")
    }

    with open(METRICS, "w") as f:
        json.dump(
            health,
            f,
            indent=2
        )

    print(json.dumps(health, indent=2), flush=True)

    time.sleep(15)
