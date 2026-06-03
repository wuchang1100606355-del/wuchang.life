from fastapi import FastAPI
import os, time
BOOT=time.time()
app=FastAPI(title="Taiji Policy Collapse Core")
@app.get("/health")
def health():
    return {
        "status":"ok",
        "service":"policy_collapse_core",
        "pid":os.getpid(),
        "uptime":round(time.time()-BOOT,2),
        "rule":"Agent 只能提案，Core 才能塌縮，Claw 才能執行，Ledger 必須留痕"
    }
