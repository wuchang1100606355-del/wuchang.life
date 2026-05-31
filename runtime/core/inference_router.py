import json
import time
from datetime import datetime

FILE="/home/taiji_admin/Taiji_Hub/runtime/topology/metric_vectors.json"

while True:

    with open(FILE,"r") as f:

        data=json.load(f)

    best_node=None
    best_score=0

    for v in data["vectors"]:

        score=(

            v["trust"]*0.30+

            v["stability"]*0.25+

            v["cognition_capacity"]*0.35+

            (1-v["risk"])*0.10
        )

        if score>best_score:

            best_score=score
            best_node=v["node"]

    routing={

        "timestamp":str(datetime.now()),

        "selected_inference_node":best_node,

        "routing_score":round(best_score,4)
    }

    print(json.dumps(routing,indent=2,ensure_ascii=False))

    time.sleep(20)

