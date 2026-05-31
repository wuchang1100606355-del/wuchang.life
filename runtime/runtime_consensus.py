import os
import json
import time
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

MESH = f"{BASE}/metrics/cognitive_mesh.json"

CONSENSUS = f"{BASE}/metrics/runtime_consensus.json"

print("[CONSENSUS] online", flush=True)

while True:

    try:

        with open(MESH, "r") as f:
            mesh = json.load(f)

    except:

        mesh = {}

    agents = mesh.get(
        "agents",
        {}
    )

    online = []

    gateway = []

    loads = []

    for name, info in agents.items():

        state = info.get(
            "state",
            {}
        )

        if state.get("status") in [
            "ONLINE",
            "ACTIVE"
        ]:

            online.append(name)

        if state.get("role") == "gateway":

            gateway.append(name)

        if "load" in state:

            loads.append(
                state["load"]
            )

    report = {

        "timestamp":
            datetime.utcnow().isoformat(),

        "online_agents":
            online,

        "gateway_agents":
            gateway,

        "avg_load":
            (
                sum(loads) / len(loads)
                if loads else 0
            ),

        "quorum":

            len(online) >= 2,

        "mesh_state":

            "HEALTHY"
            if len(online) >= 2
            else "DEGRADED"
    }

    with open(CONSENSUS, "w") as f:

        json.dump(
            report,
            f,
            indent=2
        )

    print(
        json.dumps(
            report,
            indent=2
        ),
        flush=True
    )

    time.sleep(10)
