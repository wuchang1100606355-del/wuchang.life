import json
import time
from datetime import datetime

EVENTS=[]

while True:

    event={

        "timestamp": str(datetime.now()),

        "event": "runtime_heartbeat",

        "node": "MSI_CORE",

        "status": "online",

        "context_mode": "metric_vector"
    }

    EVENTS.append(event)

    print(json.dumps(event,indent=2,ensure_ascii=False))

    time.sleep(10)
