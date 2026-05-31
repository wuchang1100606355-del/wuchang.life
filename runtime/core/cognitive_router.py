import json
import time

REGISTRY="~/Taiji_Hub/runtime/topology/node_registry.json"

print("\nLittle-J Cognitive Router Online\n")

while True:

    with open("/home/taiji_admin/Taiji_Hub/runtime/topology/node_registry.json","r") as f:

        nodes=json.load(f)

    online=[]

    for n in nodes["nodes"]:

        if n["status"]=="online":

            online.append(n["id"])

    state={

        "routing_mode":"distributed_cognition",

        "online_nodes": online,

        "active_runtime":"little-j",

        "metric_topology":"active"
    }

    print(json.dumps(state,indent=2,ensure_ascii=False))

    time.sleep(20)
