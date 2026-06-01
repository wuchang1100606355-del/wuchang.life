from fastapi import FastAPI
import os, time
BOOT=time.time()
app=FastAPI(title="Taiji Claw Executor")
@app.get("/health")
def health():
    return {
        "status":"ok",
        "service":"claw_executor",
        "pid":os.getpid(),
        "uptime":round(time.time()-BOOT,2),
        "rule":"只執行 core 授權後的本機動作"
    }
