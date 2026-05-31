import os
import json
import time
from datetime import datetime

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

BUS = f"{BASE}/memory_bus"

INBOX = f"{BUS}/inbox"
OUTBOX = f"{BUS}/outbox"
ARCHIVE = f"{BUS}/archive"

os.makedirs(INBOX, exist_ok=True)
os.makedirs(OUTBOX, exist_ok=True)
os.makedirs(ARCHIVE, exist_ok=True)

print("[MEMBUS] online", flush=True)

while True:

    files = sorted(
        os.listdir(INBOX)
    )

    for file in files:

        src = f"{INBOX}/{file}"

        try:

            with open(src, "r") as f:
                data = json.load(f)

            event = {

                "timestamp":
                    datetime.utcnow().isoformat(),

                "event":
                    data
            }

            out = f"{OUTBOX}/{file}"

            with open(out, "w") as f:
                json.dump(
                    event,
                    f,
                    indent=2
                )

            os.rename(
                src,
                f"{ARCHIVE}/{file}"
            )

            print(
                f"[EVENT] {file}",
                flush=True
            )

        except Exception as e:

            print(
                f"[ERROR] {file} {e}",
                flush=True
            )

    time.sleep(3)
