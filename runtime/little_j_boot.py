import json
import time
from datetime import datetime

print("\n⚡ Little-J Autonomous Runtime Online\n")

while True:

    runtime_state = {
        "timestamp": str(datetime.now()),
        "identity": "online",
        "event_bus": "online",
        "memory": "online",
        "consensus": "online",
        "status": "autonomous_runtime_active"
    }

    print(json.dumps(runtime_state, indent=2))

    time.sleep(30)
