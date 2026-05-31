import os
import json
import time
import subprocess
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

CONSENSUS = f"{BASE}/metrics/runtime_consensus.json"
HEAL = f"{BASE}/metrics/runtime_self_heal.json"

ROOT = os.path.expanduser("~/Taiji_Hub")

print("[SELFHEAL] online", flush=True)

def alive(pattern):

    return subprocess.call(
        f"pgrep -f '{pattern}' > /dev/null",
        shell=True
    ) == 0

def restart_runtime_api():

    subprocess.Popen(
        [
            "/usr/bin/uvicorn",
            "runtime.runtime_api:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8091"
        ],
        cwd=ROOT
    )

while True:

    heal = {

        "timestamp":
            datetime.now().isoformat(),

        "actions": []
    }

    if not alive("runtime.runtime_api:app"):

        restart_runtime_api()

        heal["actions"].append(
            "restart_runtime_api"
        )

    with open(HEAL, "w") as f:

        json.dump(
            heal,
            f,
            indent=2
        )

    print(
        json.dumps(
            heal,
            indent=2
        ),
        flush=True
    )

    time.sleep(10)
