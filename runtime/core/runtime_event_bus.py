import json
import time
from datetime import datetime

while True:

    event={

        "timestamp":str(datetime.now()),

        "event":"runtime_heartbeat",

        "node":"MSI_CORE",

        "status":"online"
    }

    print(json.dumps(event,indent=2,ensure_ascii=False))

    time.sleep(15)

