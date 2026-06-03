from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, List
import os, time
from taiji_metric_memory_core import MEMORY

BOOT = time.time()
app = FastAPI(title="Taiji Metric Memory API")

class WriteReq(BaseModel):
    code: List[float]
    value: Any

class ReadReq(BaseModel):
    code: List[float]

@app.get("/health")
def health():
    return {"status": "ok", "service": "metric_memory", "pid": os.getpid(), "uptime": round(time.time()-BOOT, 2)}

@app.get("/memory/status")
def status():
    return MEMORY.status()

@app.post("/memory/write")
def write(req: WriteReq):
    return MEMORY.set(req.code, req.value)

@app.post("/memory/read")
def read(req: ReadReq):
    return MEMORY.get(req.code)

@app.post("/memory/evict")
def evict(current_time: float):
    return MEMORY.evict(current_time)
