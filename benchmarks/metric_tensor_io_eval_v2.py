import json
import time
import statistics
import pathlib
import urllib.request
import subprocess
from datetime import datetime, UTC

ROOT = pathlib.Path.home() / "Taiji_Hub"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "metric-language-gateway-ai:latest"

BASELINE_PROMPTS = [
    "請用一句話回報五常太極分散式算力狀態。",
    "請將使用者輸入轉譯為安全的系統狀態探查任務。",
    "請摘要目前 taiji01、penguin、MSI 三機算力角色。"
]

OPTIMIZED_TASKS = [
    {"task":"status", "scope":"compute_cluster", "output":"one_sentence"},
    {"task":"translate", "scope":"readonly_diagnostics", "safety":"dry_run"},
    {"task":"summarize_roles", "nodes":["taiji01","penguin","MSI"], "output":"compact"}
]

SYSTEM_SHORT = """
你是度規匝道轉譯器。只輸出最短繁體中文或短 JSON。
不可長篇解釋。不可展開背景。不可超過 80 字。
"""

def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=8)
    except Exception as e:
        return f"ERR: {repr(e)}"

def generate(prompt, compact=False):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "system": SYSTEM_SHORT if compact else "請直接回答，避免長篇背景。",
        "options": {
            "num_predict": 80 if compact else 160,
            "temperature": 0.1
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
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read().decode("utf-8", errors="replace")
    dt = time.time() - t0
    obj = json.loads(raw)

    return {
        "seconds": round(dt, 4),
        "prompt_chars": len(prompt),
        "response_chars": len(obj.get("response", "")),
        "eval_count": obj.get("eval_count"),
        "total_duration": obj.get("total_duration"),
        "load_duration": obj.get("load_duration"),
        "response": obj.get("response", "")[:300]
    }

def run_group(name, items, compact=False, rounds=5):
    print(f"=== {name} ===")
    rows = []

    # warmup
    try:
        generate("warmup", compact=compact)
    except Exception:
        pass

    for r in range(1, rounds + 1):
        for i, item in enumerate(items, 1):
            prompt = json.dumps(item, ensure_ascii=False, separators=(",", ":")) if compact else item
            try:
                result = generate(prompt, compact=compact)
                result["round"] = r
                result["case"] = i
                rows.append(result)
                print(
                    f"round={r} case={i} "
                    f"sec={result['seconds']} "
                    f"in={result['prompt_chars']} "
                    f"out={result['response_chars']}"
                )
            except Exception as e:
                rows.append({"round": r, "case": i, "error": repr(e)})
                print(f"round={r} case={i} ERROR {repr(e)}")

    return {
        "name": name,
        "compact": compact,
        "rows": rows
    }

def stats(block):
    vals = [x["seconds"] for x in block["rows"] if "seconds" in x]
    in_chars = [x["prompt_chars"] for x in block["rows"] if "prompt_chars" in x]
    out_chars = [x["response_chars"] for x in block["rows"] if "response_chars" in x]

    return {
        "count": len(vals),
        "avg_seconds": round(statistics.mean(vals), 4) if vals else None,
        "min_seconds": round(min(vals), 4) if vals else None,
        "max_seconds": round(max(vals), 4) if vals else None,
        "stdev_seconds": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0,
        "avg_prompt_chars": round(statistics.mean(in_chars), 2) if in_chars else None,
        "avg_response_chars": round(statistics.mean(out_chars), 2) if out_chars else None
    }

def main():
    print("=== METRIC TENSOR IO EVAL V2 ===")
    print("model:", MODEL)
    print("time:", datetime.now(UTC).isoformat())
    print()

    before = {
        "free": sh("free -h"),
        "vmstat": sh("vmstat 1 2 | tail -n 1"),
        "docker_stats": sh("docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.BlockIO}}'"),
        "gpu": sh("nvidia-smi --query-gpu=power.draw,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || true")
    }

    baseline = run_group("baseline_plain_language", BASELINE_PROMPTS, compact=False, rounds=5)
    optimized = run_group("optimized_metric_packet", OPTIMIZED_TASKS, compact=True, rounds=5)

    after = {
        "free": sh("free -h"),
        "vmstat": sh("vmstat 1 2 | tail -n 1"),
        "docker_stats": sh("docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.BlockIO}}'"),
        "gpu": sh("nvidia-smi --query-gpu=power.draw,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || true")
    }

    b = stats(baseline)
    o = stats(optimized)

    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "before": before,
        "after": after,
        "baseline": baseline,
        "optimized": optimized,
        "baseline_stats": b,
        "optimized_stats": o
    }

    out = REPORT_DIR / f"metric_tensor_io_energy_eval_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=== SUMMARY ===")
    print("baseline:", b)
    print("optimized:", o)

    if b["avg_seconds"] and o["avg_seconds"]:
        diff = round(b["avg_seconds"] - o["avg_seconds"], 4)
        pct = round(diff / b["avg_seconds"] * 100, 2)
        print("latency_saved_seconds:", diff)
        print("latency_saved_percent:", pct)

    if b["avg_response_chars"] and o["avg_response_chars"]:
        diff_out = round(b["avg_response_chars"] - o["avg_response_chars"], 2)
        pct_out = round(diff_out / b["avg_response_chars"] * 100, 2)
        print("response_chars_saved:", diff_out)
        print("response_chars_saved_percent:", pct_out)

    print("report:", out)

if __name__ == "__main__":
    main()
