import os
import json
import time
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

ORCH = f"{BASE}/metrics/runtime_orchestrator.json"

SNAPDIR = f"{BASE}/snapshots"

os.makedirs(
    SNAPDIR,
    exist_ok=True
)

def load():

    try:

        with open(ORCH, "r") as f:
            return json.load(f)

    except:

        return {}

while True:

    ts = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    state = load()

    snap = f"{SNAPDIR}/{ts}.json"

    with open(snap, "w") as f:

        json.dump(
            state,
            f,
            indent=2
        )

    latest = f"{SNAPDIR}/LATEST.json"

    with open(latest, "w") as f:

        json.dump(
            state,
            f,
            indent=2
        )

    print(
        f"[SNAPSHOT] {snap}",
        flush=True
    )

    snaps = sorted([
        x for x in os.listdir(SNAPDIR)
        if x.endswith(".json")
        and x != "LATEST.json"
    ])

    while len(snaps) > 20:

        old = snaps.pop(0)

        os.remove(
            f"{SNAPDIR}/{old}"
        )

        print(
            f"[PRUNE] {old}",
            flush=True
        )

    time.sleep(60)
