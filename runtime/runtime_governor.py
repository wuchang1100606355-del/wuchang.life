import os
import json
import time
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

FILES = {

    "health":
        f"{BASE}/metrics/runtime_health.json",

    "fabric":
        f"{BASE}/metrics/node_fabric.json",

    "consensus":
        f"{BASE}/metrics/runtime_consensus.json",

    "heal":
        f"{BASE}/metrics/runtime_self_heal.json",

    "mesh":
        f"{BASE}/metrics/cognitive_mesh.json"
}

OUTPUT = f"{BASE}/metrics/runtime_governor.json"

print("[GOVERNOR] online", flush=True)

def load(path):

    try:

        with open(path, "r") as f:
            return json.load(f)

    except:

        return {}

while True:

    health = load(
        FILES["health"]
    )

    fabric = load(
        FILES["fabric"]
    )

    consensus = load(
        FILES["consensus"]
    )

    heal = load(
        FILES["heal"]
    )

    mesh = load(
        FILES["mesh"]
    )

    governor = {

        "timestamp":
            datetime.utcnow().isoformat(),

        "runtime": {

            "gateway":
                health.get(
                    "gateway_alive"
                ),

            "deadletter":
                health.get(
                    "deadletter_alive"
                ),

            "checkpoint":
                health.get(
                    "active_checkpoint"
                ),

            "status":
                health.get(
                    "runtime_status"
                )
        },

        "mesh": {

            "state":
                consensus.get(
                    "mesh_state"
                ),

            "quorum":
                consensus.get(
                    "quorum"
                ),

            "online_agents":
                consensus.get(
                    "online_agents"
                ),

            "gateway_agents":
                consensus.get(
                    "gateway_agents"
                ),

            "avg_load":
                consensus.get(
                    "avg_load"
                )
        },

        "nodes":
            fabric.get(
                "nodes",
                {}
            ),

        "heal_actions":
            heal.get(
                "actions",
                []
            ),

        "agents":
            mesh.get(
                "agents",
                {}
            )
    }

    with open(OUTPUT, "w") as f:

        json.dump(
            governor,
            f,
            indent=2
        )

    print(
        json.dumps(
            governor,
            indent=2
        ),
        flush=True
    )

    time.sleep(20)
