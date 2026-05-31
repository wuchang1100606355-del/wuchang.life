import os
import time
import shutil
import subprocess

BASE = os.path.expanduser("~/Taiji_Hub/runtime/deadletter")

FAILED = f"{BASE}/failed"
REPLAY = f"{BASE}/replay"
DONE = f"{BASE}/done"

print("[DLQ] replay engine started", flush=True)

while True:

    tasks = os.listdir(FAILED)

    for task in tasks:

        src = f"{FAILED}/{task}"
        replay = f"{REPLAY}/{task}"

        try:

            shutil.move(src, replay)

            with open(replay, "r") as f:
                cmd = f.read().strip()

            print(f"[REPLAY] {cmd}", flush=True)

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:

                shutil.move(
                    replay,
                    f"{DONE}/{task}"
                )

                print(f"[OK] {task}", flush=True)

            else:

                shutil.move(
                    replay,
                    src
                )

                print(f"[RETRY] {task}", flush=True)

        except Exception as e:

            print(f"[ERROR] {task} {e}", flush=True)

    time.sleep(5)
