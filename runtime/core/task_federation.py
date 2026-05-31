import json
import time
from datetime import datetime

print("\nLittle-J Task Federation Online\n")

TASKS=[

    {
        "task":"voice_processing",
        "required":"voice"
    },

    {
        "task":"governance_review",
        "required":"governance"
    },

    {
        "task":"semantic_analysis",
        "required":"vector"
    }

]

REGISTRY="/home/taiji_admin/Taiji_Hub/runtime/topology/node_registry.json"

while True:

    with open(REGISTRY,"r") as f:

        nodes=json.load(f)

    assignments=[]

    for task in TASKS:

        assigned=None

        for n in nodes["nodes"]:

            if n["status"]=="online":

                if task["required"] in n and n[task["required"]]==True:

                    assigned=n["id"]

                    break

        assignments.append({

            "task": task["task"],

            "assigned_node": assigned
        })

    federation={

        "timestamp": str(datetime.now()),

        "task_federation": assignments,

        "runtime":"little-j",

        "mode":"distributed_task_routing"
    }

    print(json.dumps(federation,indent=2,ensure_ascii=False))

    time.sleep(20)
