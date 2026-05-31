import os
import json
import time
import subprocess
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

METRICS = f"{BASE}/metrics/node_fabric.json"

NODES = {
    "taiji_01": "100.71.224.18",
    "taiji_02": "100.111.139.7"
}

def ping(host):

    try:

        subprocess.check_output(
            f"ping -c 1 -W 1 {host}",
            shell=True,
            stderr=subprocess.DEVNULL
        )

        return True

    except:

        return False

def latency(host):

    try:

        out = subprocess.check_output(
            f"ping -c 1 {host}",
            shell=True
        ).decode()

        line = [
            x for x in out.splitlines()
            if "time=" in x
        ][0]

        return line.split("time=")[1].split()[0]

    except:

        return None

while True:

    report = {

        "timestamp":
            datetime.utcnow().isoformat(),

        "nodes": {}
    }

    for name, host in NODES.items():

        alive = ping(host)

        report["nodes"][name] = {

            "host": host,
            "alive": alive,
            "latency_ms":
                latency(host) if alive else None
        }

    with open(METRICS, "w") as f:

        json.dump(
            report,
            f,
            indent=2
        )

    print(
        json.dumps(report, indent=2),
        flush=True
    )

    time.sleep(30)
