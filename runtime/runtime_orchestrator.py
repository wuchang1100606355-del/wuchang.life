import os
import json
import time
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

FILES = {

    "registry":
        f"{BASE}/registry/runtime_registry.json",

    "health":
        f"{BASE}/metrics/runtime_health.json",

    "watchdog":
        f"{BASE}/metrics/runtime_health.json",

    "fabric":
        f"{BASE}/metrics/node_fabric.json"
}

OUTPUT = f"{BASE}/metrics/runtime_orchestrator.json"

def load(path):

    try:

        with open(path, "r") as f:
            return json.load(f)

    except:

        return {}

while True:

    report = {

        "timestamp":
            datetime.utcnow().isoformat(),

        "runtime":
            load(FILES["registry"]),

        "health":
            load(FILES["health"]),

        "fabric":
            load(FILES["fabric"])
    }

    report["summary"] = {

        "gateway_alive":
            report["health"].get(
                "gateway_alive"
            ),

        "deadletter_alive":
            report["health"].get(
                "deadletter_alive"
            ),

        "runtime_status":
            report["runtime"].get(
                "runtime_status"
            ),

        "active_checkpoint":
            report["runtime"].get(
                "active_checkpoint"
            ),

        "nodes_alive":
            len([
                x for x in
                report["fabric"]
                .get("nodes", {})
                .values()
                if x.get("alive")
            ])
    }

    with open(OUTPUT, "w") as f:

        json.dump(
            report,
            f,
            indent=2
        )

    print(
        json.dumps(
            report["summary"],
            indent=2
        ),
        flush=True
    )

    time.sleep(20)
