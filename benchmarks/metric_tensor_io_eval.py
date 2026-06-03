import os
import time
import json
import subprocess
import urllib.request
import pathlib
from datetime import datetime

ROOT = pathlib.Path.home() / "Taiji_Hub"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)

PROMPTS = [
    "請用一句話回報五常太極分散式算力狀態。",
    "請將使用者輸入轉譯為安全的系統狀態探查任務。",
    "請摘要目前 taiji01、penguin、MSI 三機算力角色。",
]

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL_FAST = "metric-language-gateway-ai:latest"

def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=8)
    except Exception as e:
        return f"ERR: {repr(e)}"

def snapshot(label):
    return {
        "label": label,
        "time": datetime.utcnow().isoformat() + "Z",
        "free_h": sh("free -h"),
        "vmstat": sh("vmstat 1 2 | tail -n 1"),
        "disk": sh("df -h /"),
        "docker_stats": sh("docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.BlockIO}}'"),
        "nvidia_smi": sh("nvidia-smi --query-gpu=name,temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || true"),
        "ollama_ps": sh("ps aux | grep -Ei 'ollama|open-webui|uvicorn|python3' | grep -v grep | head -n 30"),
    }

def ollama_generate(prompt, model=MODEL_FAST, timeout=90):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 120,
            "temperature": 0.2
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    dt = time.time() - t0
    obj = json.loads(raw)
    return {
        "ok": True,
        "seconds": round(dt, 3),
        "model": model,
        "prompt_len": len(prompt),
        "response_len": len(obj.get("response", "")),
        "eval_count": obj.get("eval_count"),
        "eval_duration": obj.get("eval_duration"),
        "load_duration": obj.get("load_duration"),
        "total_duration": obj.get("total_duration"),
        "response_head": obj.get("response", "")[:300]
    }

def compact_prompt(prompt):
    # 模擬「度規張量引擎 + 匝道轉譯器」的節能假設：
    # 將自然語言任務收斂成短任務封包，減少上下文搬運與 token I/O。
    return {
        "task": "metric_route",
        "intent": "status_or_dispatch",
        "scope": "local_runtime",
        "safety": "readonly_or_dryrun",
        "input": prompt[:80]
    }

def run_mode(mode_name, prompts, compact=False):
    results = []
    print(f"=== MODE {mode_name} ===")

    before = snapshot(f"{mode_name}_before")

    for i, p in enumerate(prompts, 1):
        try:
            use_prompt = json.dumps(compact_prompt(p), ensure_ascii=False) if compact else p
            r = ollama_generate(use_prompt)
            r["case"] = i
            r["compact"] = compact
            results.append(r)
            print(f"case={i} ok seconds={r['seconds']} response_len={r['response_len']}")
        except Exception as e:
            results.append({
                "case": i,
                "ok": False,
                "compact": compact,
                "error": repr(e)
            })
            print(f"case={i} FAIL {repr(e)}")

    after = snapshot(f"{mode_name}_after")

    return {
        "mode": mode_name,
        "compact": compact,
        "before": before,
        "after": after,
        "results": results
    }

def main():
    print("=== TAIJI METRIC TENSOR IO ENERGY EVAL ===")
    print("root:", ROOT)
    print("model:", MODEL_FAST)
    print()

    tags = sh("curl -s http://127.0.0.1:11434/api/tags | head -c 800")
    print("=== OLLAMA TAGS HEAD ===")
    print(tags)
    print()

    baseline = run_mode("baseline_plain_language", PROMPTS, compact=False)
    time.sleep(2)
    optimized = run_mode("metric_tensor_gateway_compact", PROMPTS, compact=True)

    report = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "purpose": "Evaluate memory I/O and energy-proxy effects of metric tensor engine + gateway translator compact routing.",
        "host": sh("hostname").strip(),
        "baseline": baseline,
        "optimized": optimized
    }

    out = REPORT_DIR / f"metric_tensor_io_energy_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def avg_seconds(block):
        vals = [r["seconds"] for r in block["results"] if r.get("ok")]
        return round(sum(vals) / len(vals), 3) if vals else None

    print()
    print("=== SUMMARY ===")
    print("baseline_avg_seconds:", avg_seconds(baseline))
    print("optimized_avg_seconds:", avg_seconds(optimized))
    print("report:", out)

    print()
    print("=== QUICK INTERPRETATION ===")
    b = avg_seconds(baseline)
    o = avg_seconds(optimized)
    if b and o:
        if o < b:
            print("RESULT: compact metric routing is faster in this run.")
        elif o > b:
            print("RESULT: compact metric routing is slower in this run; model/load/cache effects need review.")
        else:
            print("RESULT: no meaningful latency difference in this run.")
    else:
        print("RESULT: incomplete generation results.")

if __name__ == "__main__":
    main()
