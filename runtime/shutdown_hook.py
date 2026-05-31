import signal
import time
from checkpoint_manager import create_checkpoint

def shutdown_handler(sig, frame):

    state = {
        "status": "SAFE_SHUTDOWN",
        "timestamp": time.time()
    }

    create_checkpoint(state)

    print("[✓] Safe shutdown checkpoint saved")

    exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

print("[✓] Shutdown hook armed")

while True:
    time.sleep(1)
