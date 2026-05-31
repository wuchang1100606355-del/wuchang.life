from fastapi import FastAPI
import psutil
import time

app = FastAPI()

BOOT = time.time()

@app.get("/metrics")
async def metrics():

    return {

        "cpu_percent":
            psutil.cpu_percent(),

        "memory_percent":
            psutil.virtual_memory().percent,

        "disk_percent":
            psutil.disk_usage("/").percent,

        "boot_seconds":
            int(time.time() - BOOT),

        "process_count":
            len(psutil.pids())
    }
