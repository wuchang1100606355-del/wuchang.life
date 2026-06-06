from services.gateway.openai_compat import router as openai_compat_router
from services.gateway.topology_router import router as taiji_topology_router
# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pathlib import Path
import requests, subprocess, json, hashlib, os
from datetime import datetime
from services.w7tp_ui_adapter import router as w7tp_ui_router

app = FastAPI(title="Taiji Gateway", version="1.1.0-redteam")

RUNTIME_API = os.getenv("TAIJI_RUNTIME_API", "http://127.0.0.1:8099")
CLAW_URL = os.getenv("TAIJI_CLAW_URL", "http://127.0.0.1:9004")
OLLAMA_HTTP = os.getenv("TAIJI_OLLAMA_HTTP", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("TAIJI_MODEL", "llama3.1:latest")
PROJECT_ROOT = os.getenv("TAIJI_PROJECT_ROOT", "/home/taiji_admin/Taiji_Hub")

def safe_request(method, url, timeout=5, **kwargs):
    try:
        r = requests.request(method, url, timeout=timeout, **kwargs)
        try:
            data = r.json()
        except Exception:
            data = {"text": r.text[:2000]}
        return {"ok": 200 <= r.status_code < 300, "status_code": r.status_code, "data": data}
    except Exception as e:
        return {"ok": False, "status_code": 0, "error": str(e)}

def runtime_snapshot():
    return {
        "system": safe_request("GET", f"{RUNTIME_API}/runtime/system", timeout=2),
        "status": safe_request("GET", f"{RUNTIME_API}/runtime/status", timeout=2),
        "agents": safe_request("GET", f"{RUNTIME_API}/runtime/agents", timeout=2),
        "claw": safe_request("GET", f"{CLAW_URL}/", timeout=2),
        "timestamp": datetime.now().isoformat()
    }

def context_shards(prompt, keyword):
    text = f"{prompt} {keyword}".lower()
    shards = []

    if any(k in text for k in ["搜尋", "掃描", "找", "search", "scan", "find", "查"]):
        shards.append({"type": "action", "value": "scan"})

    if any(k in text for k in ["整理", "摘要", "分析", "重構", "拓樸", "判斷", "確認", "reason", "summarize"]):
        shards.append({"type": "action", "value": "reason"})

    if any(k in text for k in ["taiji", "太極", "五常", "wuchang"]):
        shards.append({"type": "target", "value": "taiji"})

    if any(k in text for k in ["jules", "小j", "sister", "xiaoj"]):
        shards.append({"type": "target", "value": "xiaoj"})

    if any(k in text for k in ["語音", "voice", "google", "gemini"]):
        shards.append({"type": "input", "value": "voice"})

    shards.append({"type": "scope", "value": "local-first"})
    return shards

def metric_tensor(shards, runtime):
    has_scan = any(s["type"] == "action" and s["value"] == "scan" for s in shards)
    need_reason = any(s["type"] == "action" and s["value"] == "reason" for s in shards)
    claw_alive = bool(runtime.get("claw", {}).get("ok"))
    runtime_alive = bool(runtime.get("system", {}).get("ok"))

    G = {
        "intent": 1.0 if has_scan else 0.65,
        "context": min(1.0, 0.28 + 0.11 * len(shards)),
        "runtime": 1.0 if runtime_alive else 0.35,
        "claw_alive": 1.0 if claw_alive else 0.0,
        "privacy": 1.0,
        "energy_saving": 0.92,
        "local_first": 1.0,
        "redteam_safe_mode": 1.0
    }

    scores = {
        "claw": round((G["intent"] + G["context"] + G["claw_alive"]) / 3, 4),
        "llm": round((G["context"] + G["runtime"] + (1.0 if need_reason else 0.78)) / 3, 4),
        "runtime": round((G["runtime"] + G["privacy"] + G["energy_saving"] + G["local_first"]) / 4, 4)
    }

    if has_scan and claw_alive:
        decision = {"target": "claw", "action": "scan_physical_then_llm_reconstruct"}
    else:
        decision = {"target": "xiaoj_llm", "action": "reason"}

    return G, scores, decision

def claw_openapi_paths():
    r = safe_request("GET", f"{CLAW_URL}/openapi.json", timeout=3)
    if not r.get("ok"):
        return []
    paths = r.get("data", {}).get("paths", {})
    out = []
    for path, methods in paths.items():
        if any(x in path.lower() for x in ["scan", "file", "claw"]):
            for method in methods.keys():
                out.append((method.upper(), path))
    return out

def scan_claw(keyword):
    candidates = [
        ("GET", "/api/claw/scan_physical"),
        ("GET", "/scan_physical"),
        ("GET", "/api/scan_physical"),
        ("GET", "/api/claw/scan"),
        ("POST", "/api/claw/scan_physical"),
        ("POST", "/scan_physical"),
        ("POST", "/api/scan"),
    ]

    discovered = claw_openapi_paths()
    for item in discovered:
        if item not in candidates:
            candidates.insert(0, item)

    base_variants = [
        PROJECT_ROOT,
        "/host_root/home/taiji_admin/Taiji_Hub",
        ""
    ]

    attempts = []
    for method, path in candidates:
        for base_path in base_variants:
            url = f"{CLAW_URL}{path}"
            payload = {"keyword": keyword, "base_path": base_path}

            if method == "GET":
                res = safe_request("GET", url, timeout=60, params=payload)
            else:
                res = safe_request("POST", url, timeout=60, json=payload)

            attempts.append({
                "method": method,
                "path": path,
                "base_path": base_path,
                "status_code": res.get("status_code"),
                "ok": res.get("ok")
            })

            if res.get("ok"):
                data = res.get("data", {})
                if isinstance(data, dict):
                    data["_route_used"] = {"method": method, "path": path, "base_path": base_path}
                return data

    return {
        "status": "degraded",
        "message": "Clow/Claw online but no compatible scan route succeeded",
        "openapi_candidates": discovered,
        "attempts": attempts[-12:]
    }

def ask_xiaoj(prompt):
    try:
        r = requests.post(
            OLLAMA_HTTP,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=180
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "dispatch": "ollama_http",
                "model": OLLAMA_MODEL,
                "response": data.get("response", ""),
                "raw": data
            }
    except Exception:
        pass

    try:
        p = subprocess.run(
            ["docker", "exec", "wuchang_gpu_brain", "ollama", "run", OLLAMA_MODEL, prompt],
            text=True,
            capture_output=True,
            timeout=180
        )
        if p.returncode == 0:
            return {"dispatch": "docker_exec_ollama", "model": OLLAMA_MODEL, "response": p.stdout.strip()}
        return {"dispatch": "docker_exec_ollama", "model": OLLAMA_MODEL, "error": p.stderr.strip()}
    except Exception as e:
        return {"dispatch": "none", "model": OLLAMA_MODEL, "error": str(e)}

def persist_record(record):
    Path("runtime/ledger").mkdir(parents=True, exist_ok=True)
    path = Path("runtime/ledger") / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json")
    safe_record = dict(record)
    safe_record.pop("_plaintext_prompt", None)
    path.write_text(json.dumps(safe_record, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)

def run_taiji(payload):
    prompt = payload.get("prompt") or payload.get("text") or payload.get("utterance") or ""
    keyword = payload.get("keyword", "")

    if not keyword:
        for token in ["jules", "taiji", "小J", "小j", "wuchang", "claw"]:
            if token.lower() in prompt.lower():
                keyword = token
                break

    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    rt = runtime_snapshot()
    shards = context_shards(prompt, keyword)
    G, scores, decision = metric_tensor(shards, rt)

    claw_result = None
    if decision["target"] == "claw":
        claw_result = scan_claw(keyword)

    topology = {
        "topology": "taiji_redteam_hardened_runtime_graph",
        "nodes": [
            {"id": "natural_language.input", "role": "openwebui_or_voice_or_pos"},
            {"id": "xiaoj.intent", "role": "intent_llm_manager"},
            {"id": "context.shards", "role": "privacy_preserving_fragmentation", "shards": shards},
            {"id": "dugui.metric_tensor", "role": "decision_field", "G": G, "scores": scores},
            {"id": decision["target"], "role": "executor", "action": decision["action"]},
            {"id": "xiaoj.llm", "role": "topology_reconstruction"}
        ]
    }

    llm_prompt = json.dumps({
        "role": "小J / Taiji Runtime Core",
        "task": "用紅隊觀點檢查系統狀態，依度規張量、上下文分片、runtime 狀態與 Clow 結果，給出工程結論與風險修正。",
        "prompt_hash": prompt_hash,
        "keyword": keyword,
        "context_shards": shards,
        "metric_tensor": G,
        "scores": scores,
        "decision": decision,
        "runtime": rt,
        "claw_result": claw_result,
        "topology": topology
    }, ensure_ascii=False)

    xiaoj = ask_xiaoj(llm_prompt)

    record = {
        "status": "executed",
        "privacy": {
            "plaintext_context_persisted": False,
            "prompt_hash": prompt_hash
        },
        "runtime": rt,
        "context_shards": shards,
        "metric_tensor": G,
        "scores": scores,
        "decision": decision,
        "topology": topology,
        "claw_result": claw_result,
        "xiaoj": xiaoj,
        "created_at": datetime.now().isoformat()
    }

    record["ledger_path"] = persist_record(record)
    return record

@app.get("/health")
def health():
    return {
        "gateway": "online",
        "service": "taiji-gateway",
        "version": "1.1.0-redteam",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/taiji/plan")
def plan_get():
    return {"status": "online", "hint": "POST /api/taiji/execute with prompt"}

@app.post("/api/taiji/plan")
def plan(payload: dict):
    prompt = payload.get("prompt", "")
    keyword = payload.get("keyword", "")
    rt = runtime_snapshot()
    shards = context_shards(prompt, keyword)
    G, scores, decision = metric_tensor(shards, rt)
    return {"status": "planned", "runtime": rt, "context_shards": shards, "metric_tensor": G, "scores": scores, "decision": decision}

@app.post("/api/taiji/execute")
def execute(payload: dict):
    return run_taiji(payload)

@app.post("/api/taiji/voice")
def voice(payload: dict):
    text = payload.get("text") or payload.get("utterance") or payload.get("prompt") or ""
    payload["prompt"] = text
    payload["source"] = "voice"
    return run_taiji(payload)

app.include_router(taiji_topology_router)
app.include_router(openai_compat_router)
app.include_router(w7tp_ui_router)
