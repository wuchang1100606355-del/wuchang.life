import os
import json
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime/memory/conversations")

os.makedirs(BASE, exist_ok=True)

def save_event(prompt, dispatch, response):

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    path = f"{BASE}/{ts}.json"

    event = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "dispatch": dispatch,
        "response": response
    }

    with open(path, "w") as f:
        json.dump(event, f, indent=2)

    return path
