from fastapi import FastAPI
import json
import os

app = FastAPI()

BASE = "/home/taiji_admin/Taiji_Hub/runtime/metrics"

def load(name):

    path = f"{BASE}/{name}"

    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        return json.load(f)

@app.get("/runtime/status")
async def status():

    return {
        "health": load("runtime_health.json"),
        "consensus": load("runtime_consensus.json"),
        "governor": load("runtime_governor.json")
    }

@app.get("/runtime/mesh")
async def mesh():

    return load("cognitive_mesh.json")

@app.get("/runtime/metrics")
async def metrics():

    return {
        "health": load("runtime_health.json"),
        "fabric": load("node_fabric.json"),
        "consensus": load("runtime_consensus.json"),
        "heal": load("runtime_self_heal.json")
    }
