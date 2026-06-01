#!/usr/bin/env python3
import os, json, time
import httpx
from pathlib import Path
from dotenv import load_dotenv

root = Path.home() / "Taiji_Hub" / "commander"
load_dotenv(root / "config" / "commander.env")

targets = {
    "open_webui": os.getenv("WUCHANG_OPENWEBUI_URL"),
    "gateway_9002": os.getenv("WUCHANG_GATEWAY_URL") + "/openapi.json",
    "odoo_8069": os.getenv("WUCHANG_ODOO_URL"),
    "ollama_11434": os.getenv("WUCHANG_OLLAMA_URL") + "/api/tags",
    "native_claw_9004": os.getenv("WUCHANG_CLAW_URL") + "/healthz",
}

result = {
    "commander": os.getenv("WUCHANG_COMMANDER_NAME"),
    "workspace": os.getenv("WUCHANG_WORKSPACE"),
    "mode": os.getenv("WUCHANG_MODE"),
    "time": int(time.time()),
    "targets": {}
}

for name, url in targets.items():
    try:
        r = httpx.get(url, timeout=3)
        result["targets"][name] = {
            "url": url,
            "ok": r.status_code < 500,
            "status_code": r.status_code,
        }
    except Exception as e:
        result["targets"][name] = {
            "url": url,
            "ok": False,
            "error": str(e),
        }

out = root / "reports" / "commander_health.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
