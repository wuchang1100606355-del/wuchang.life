import os
import json
import time
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

BUS = f"{BASE}/memory_bus/outbox"

GRAPH = f"{BASE}/metrics/cognitive_mesh.json"

agents = {}

print("[COGMESH] online", flush=True)

while True:

    files = sorted(
        os.listdir(BUS)
    )

    for file in files:

        path = f"{BUS}/{file}"

        try:

            with open(path, "r") as f:
                data = json.load(f)

            evt = data.get(
                "event",
                {}
            )

            agent = evt.get(
                "agent",
                "unknown"
            )

            payload = evt.get(
                "payload",
                {}
            )

            agents[agent] = {

                "last_seen":
                    datetime.utcnow().isoformat(),

                "state":
                    payload
            }

            print(
                f"[SYNC] {agent}",
                flush=True
            )

            os.remove(path)

        except Exception as e:

            print(
                f"[ERROR] {file} {e}",
                flush=True
            )

    with open(GRAPH, "w") as f:

        json.dump(
            {
                "timestamp":
                    datetime.utcnow().isoformat(),

                "agents":
                    agents
            },
            f,
            indent=2
        )

    time.sleep(3)
