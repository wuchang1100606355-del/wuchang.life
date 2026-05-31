# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
import requests, hashlib, time, json, os

app = FastAPI(title="Taiji OpenWebUI Bridge", version="1.1.0-redteam")

MODEL_ALIAS = "taiji-runtime-core"
TAIJI_GATEWAY = os.getenv("TAIJI_GATEWAY", "http://127.0.0.1:8081/api/taiji/execute")
HEALTH_URL = os.getenv("TAIJI_HEALTH", "http://127.0.0.1:8081/health")

@app.get("/health")
async def health():
    try:
        r = requests.get(HEALTH_URL, timeout=3)
        gateway = r.json()
        ok = True
    except Exception as e:
        gateway = {"error": str(e)}
        ok = False
    return {
        "status": "ok" if ok else "degraded",
        "service": "taiji-openwebui-bridge",
        "version": "1.1.0-redteam",
        "gateway": gateway
    }

@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [{"id": MODEL_ALIAS, "object": "model", "owned_by": "taiji"}]
    }

@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    messages = body.get("messages", [])

    prompt = "\n".join(
        f"{m.get('role','user')}: {m.get('content','')}"
        for m in messages
    )

    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    try:
        r = requests.post(
            TAIJI_GATEWAY,
            json={"prompt": prompt, "keyword": body.get("keyword", "")},
            timeout=240
        )
        r.raise_for_status()
        data = r.json()
        xiaoj = data.get("xiaoj", {})

        if isinstance(xiaoj, dict):
            text = (
                xiaoj.get("response")
                or xiaoj.get("raw", {}).get("response")
                or json.dumps({
                    "status": data.get("status"),
                    "decision": data.get("decision"),
                    "scores": data.get("scores"),
                    "claw_result": data.get("claw_result"),
                    "ledger_path": data.get("ledger_path")
                }, ensure_ascii=False, indent=2)
            )
        else:
            text = json.dumps({
                "status": data.get("status"),
                "decision": data.get("decision"),
                "scores": data.get("scores"),
                "ledger_path": data.get("ledger_path")
            }, ensure_ascii=False, indent=2)

    except Exception as e:
        text = json.dumps({
            "status": "error",
            "message": "Taiji Gateway execution failed",
            "detail": str(e)
        }, ensure_ascii=False, indent=2)

    return {
        "id": f"taiji-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ALIAS,
        "privacy": {
            "plaintext_context_persisted": False,
            "prompt_hash": prompt_hash
        },
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop"
        }]
    }
