import os
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

REGISTRY = f"{BASE}/registry/runtime_registry.json"

SERVICES = f"{BASE}/registry/runtime_service_registry.json"

def load_json(path):

    try:

        with open(path, "r") as f:
            return json.load(f)

    except:

        return {}

@app.get("/runtime/health")
def runtime_health():

    return JSONResponse(
        content=load_json(REGISTRY)
    )

@app.get("/runtime/services")
def runtime_services():

    return JSONResponse(
        content=load_json(SERVICES)
    )

@app.get("/runtime/services/{service}")
def runtime_service(service: str):

    services = load_json(SERVICES)

    if service not in services:

        return JSONResponse(
            content={
                "error": "service_not_found"
            },
            status_code=404
        )

    return JSONResponse(
        content=services[service]
    )
