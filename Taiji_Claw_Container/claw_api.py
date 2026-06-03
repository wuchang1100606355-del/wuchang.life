# -*- coding: utf-8 -*-
from fastapi import FastAPI
import os, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [上帝巨螯] %(message)s')
app = FastAPI(title="Wuchang God-Mode Claw API", version="Max_Power")

HOST_ROOT = "/host_root"

@app.get("/")
def health_check():
    return {"status": "Active", "service": "taiji-claw"}

@app.get("/api/claw/scan_physical")
def scan_physical_drives(keyword: str = "", base_path: str = ""):
    logging.warning(f"[SCAN] keyword={keyword} base_path={base_path}")

    if not base_path:
        base_path = f"{HOST_ROOT}/mnt/c/Users/o0930/Taiji_Hub"

    found = []

    if not os.path.exists(base_path):
        return {"status": "error", "msg": "base_path not found", "base_path": base_path}

    for root, dirs, files in os.walk(base_path):
        for f in files:
            if keyword.lower() in f.lower():
                full = os.path.join(root, f)
                display = full.replace(HOST_ROOT, "")
                found.append(display)
                if len(found) >= 10:
                    return {"status": "ok", "count": len(found), "files": found}

    return {"status": "ok", "count": len(found), "files": found}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9004)
