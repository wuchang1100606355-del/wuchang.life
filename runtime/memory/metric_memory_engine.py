import json
import time
from datetime import datetime

FILE="/home/taiji_admin/Taiji_Hub/runtime/topology/metric_vectors.json"

print("\nLittle-J Metric Vector Memory Online\n")

while True:

    with open(FILE,"r") as f:

        data=json.load(f)

    summary=[]

    for v in data["vectors"]:

        state={

            "node": v["node"],

            "trust_level": v["trust"],

            "stability": v["stability"],

            "risk": v["risk"]
        }

        summary.append(state)

    memory={

        "timestamp": str(datetime.now()),

        "metric_memory": summary,

        "memory_mode": "civilization_vector_context",

        "runtime": "little-j"
    }

    print(json.dumps(memory,indent=2,ensure_ascii=False))

    time.sleep(20)
