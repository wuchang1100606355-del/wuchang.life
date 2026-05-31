from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import os
import json
import psutil
import time
import requests
from datetime import datetime

app = FastAPI()

BOOT = time.time()

BASE = "/home/taiji_admin/Taiji_Hub/runtime"

BASE_METRICS = f"{BASE}/metrics"
BASE_EVENTS = f"{BASE}/outbox"
BASE_MEMORY = f"{BASE}/memory/conversations"
BASE_AGENTS = f"{BASE}/agents"

MODEL = "llama3.1:latest"

os.makedirs(BASE_MEMORY, exist_ok=True)
os.makedirs(BASE_AGENTS, exist_ok=True)

def load_json(path):

    if not os.path.exists(path):
        return {}

    try:

        with open(path, "r") as f:
            return json.load(f)

    except:
        return {}

def save_json(path, data):

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def save_memory(prompt, response):

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = f"{BASE_MEMORY}/{ts}.json"

    save_json(path, {
        "timestamp": ts,
        "prompt": prompt,
        "response": response
    })

@app.get("/")
async def root():

    return {
        "runtime": "online",
        "model": MODEL
    }

@app.get("/runtime/system")
async def system():

    return {

        "runtime": "online",

        "model": MODEL,

        "boot_seconds":
            int(time.time() - BOOT),

        "cpu_percent":
            psutil.cpu_percent(),

        "memory_percent":
            psutil.virtual_memory().percent,

        "disk_percent":
            psutil.disk_usage("/").percent,

        "process_count":
            len(psutil.pids())
    }

@app.get("/runtime/status")
async def status():

    return {
        "health":
            load_json(f"{BASE_METRICS}/runtime_health.json"),

        "consensus":
            load_json(f"{BASE_METRICS}/runtime_consensus.json"),

        "governor":
            load_json(f"{BASE_METRICS}/runtime_governor.json")
    }

@app.get("/runtime/metrics")
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

@app.get("/runtime/events")
async def events():

    results = []

    if os.path.exists(BASE_EVENTS):

        for file in sorted(os.listdir(BASE_EVENTS), reverse=True)[:20]:

            path = f"{BASE_EVENTS}/{file}"

            data = load_json(path)

            if data:
                data["_file"] = file
                results.append(data)

    return {
        "events": results
    }

@app.get("/runtime/memory")
async def memory():

    results = []

    for file in sorted(os.listdir(BASE_MEMORY), reverse=True)[:20]:

        path = f"{BASE_MEMORY}/{file}"

        data = load_json(path)

        if data:
            data["_file"] = file
            results.append(data)

    return {
        "memory": results
    }

@app.get("/runtime/models")
async def models():

    r = requests.get(
        "http://127.0.0.1:11434/api/tags",
        timeout=30
    )

    return r.json()

@app.get("/runtime/agents")
async def agents():

    results = []

    for file in sorted(os.listdir(BASE_AGENTS)):

        path = f"{BASE_AGENTS}/{file}"

        data = load_json(path)

        if data:
            results.append(data)

    return {
        "agents": results
    }

@app.get("/runtime/agent/{name}")
async def get_agent(name: str):

    path = f"{BASE_AGENTS}/{name}.json"

    return load_json(path)

@app.post("/runtime/agent/register")
async def register_agent(req: Request):

    body = await req.json()

    name = body.get("name")

    role = body.get("role")

    host = body.get("host")

    ts = datetime.now().isoformat()

    data = {
        "name": name,
        "role": role,
        "host": host,
        "registered_at": ts
    }

    save_json(
        f"{BASE_AGENTS}/{name}.json",
        data
    )

    return {
        "registered": data
    }

@app.post("/runtime/agent/task")
async def agent_task(req: Request):

    body = await req.json()

    agent = body.get("agent")

    task = body.get("task")

    ts = datetime.now().isoformat()

    result = {
        "agent": agent,
        "task": task,
        "timestamp": ts,
        "status": "accepted"
    }

    save_json(
        f"{BASE_EVENTS}/agent_task_{int(time.time())}.json",
        result
    )

    return result

@app.post("/runtime/generate")
async def generate(req: Request):

    body = await req.json()

    prompt = body.get(
        "prompt",
        ""
    )

    r = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=180
    )

    result = r.json()

    save_memory(
        prompt,
        result.get("response", "")
    )

    return result

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():

    return f"""
    <html>
    <body style="background:#0b1020;color:white;font-family:Arial;padding:30px">

    <h1>Taiji Runtime Core</h1>

    <p>Model: {MODEL}</p>

    <p><a href="/runtime/system">Runtime System</a></p>

    <p><a href="/runtime/status">Runtime Status</a></p>

    <p><a href="/runtime/metrics">Runtime Metrics</a></p>

    <p><a href="/runtime/events">Runtime Events</a></p>

    <p><a href="/runtime/memory">Runtime Memory</a></p>

    <p><a href="/runtime/models">Available Models</a></p>

    <p><a href="/runtime/agents">Registered Agents</a></p>

    </body>
    </html>
    """
