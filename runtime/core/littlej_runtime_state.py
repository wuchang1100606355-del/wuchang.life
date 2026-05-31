import json
import time
from datetime import datetime

while True:

    state={

        "runtime":"little-j",

        "timestamp":str(datetime.now()),

        "civilization_runtime":"active",

        "context_engine":"metric_vector_context"
    }

    print(json.dumps(state,indent=2,ensure_ascii=False))

    time.sleep(20)

