# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pathlib import Path
import os, requests, time

app = FastAPI(title="Taiji Clow Compatibility Adapter", version="1.0.0-toolfix")

UPSTREAM = os.getenv("TAIJI_CLOW_UPSTREAM", "http://127.0.0.1:9004")
DEFAULT_ROOT = "/home/taiji_admin/Taiji_Hub"

ALLOWED_ROOTS = [
    "/home/taiji_admin/Taiji_Hub",
    "/mnt/c/Users/o0930/Taiji_Hub",
]

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "postgres_data",
    "jules_env",
    "taiji_env",
    ".venv",
    "venv",
    "open_webui_data",
}

def is_allowed(path: str) -> bool:
    try:
        rp = str(Path(path).resolve())
        return any(rp == root or rp.startswith(root + "/") for root in ALLOWED_ROOTS)
    except Exception:
        return False

def normalize_root(base_path: str) -> str:
    if not base_path:
        return DEFAULT_ROOT

    candidates = [base_path]

    if base_path.startswith("/host_root/"):
        candidates.append(base_path.replace("/host_root", "", 1))
    elif base_path.startswith("/"):
        candidates.append("/host_root" + base_path)

    for c in candidates:
        if Path(c).exists() and is_allowed(c):
            return str(Path(c).resolve())

    return DEFAULT_ROOT

def upstream_scan(keyword: str, base_path: str):
    candidates = [
        ("GET", "/api/claw/scan_physical"),
        ("GET", "/scan_physical"),
        ("GET", "/api/scan_physical"),
        ("GET", "/api/claw/scan"),
        ("POST", "/api/claw/scan_physical"),
        ("POST", "/scan_physical"),
        ("POST", "/api/scan"),
    ]

    attempts = []

    for method, path in candidates:
        url = f"{UPSTREAM}{path}"
        payload = {"keyword": keyword, "base_path": base_path}
        try:
            if method == "GET":
                r = requests.get(url, params=payload, timeout=15)
            else:
                r = requests.post(url, json=payload, timeout=15)

            attempts.append({"method": method, "path": path, "status_code": r.status_code})

            if 200 <= r.status_code < 300:
                try:
                    data = r.json()
                except Exception:
                    data = {"text": r.text}

                if isinstance(data, dict):
                    data["_adapter_source"] = "upstream"
                    data["_route_used"] = {"method": method, "path": path}
                return data, attempts
        except Exception as e:
            attempts.append({"method": method, "path": path, "error": str(e)})

    return None, attempts

def local_scan(keyword: str, base_path: str, limit: int = 50):
    root = normalize_root(base_path)
    found = []

    if not Path(root).exists():
        return {
            "status": "error",
            "message": "allowed root not found",
            "root": root,
        }

    kw = (keyword or "").lower()

    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for name in files:
            if kw and kw not in name.lower():
                continue

            full = os.path.join(cur, name)
            found.append(full)

            if len(found) >= limit:
                return {
                    "status": "ok",
                    "adapter_source": "local_allowlist_fallback",
                    "root": root,
                    "keyword": keyword,
                    "count": len(found),
                    "files": found,
                    "note": f"limited to {limit} results",
                }

    return {
        "status": "ok",
        "adapter_source": "local_allowlist_fallback",
        "root": root,
        "keyword": keyword,
        "count": len(found),
        "files": found,
    }

@app.get("/")
def health():
    upstream = None
    try:
        r = requests.get(f"{UPSTREAM}/", timeout=3)
        upstream = {"ok": r.status_code < 500, "status_code": r.status_code}
    except Exception as e:
        upstream = {"ok": False, "error": str(e)}

    return {
        "status": "Active",
        "service": "taiji-clow-adapter",
        "version": "1.0.0-toolfix",
        "upstream": UPSTREAM,
        "upstream_health": upstream,
        "mode": "upstream-first-with-safe-local-fallback",
    }

@app.get("/api/claw/scan_physical")
def scan_physical_get(keyword: str = "", base_path: str = DEFAULT_ROOT):
    upstream_data, attempts = upstream_scan(keyword, base_path)
    if upstream_data:
        upstream_data["_adapter_attempts"] = attempts[-5:]
        return upstream_data

    data = local_scan(keyword, base_path)
    data["_adapter_attempts"] = attempts[-8:]
    return data

@app.post("/api/claw/scan_physical")
def scan_physical_post(payload: dict):
    keyword = payload.get("keyword", "")
    base_path = payload.get("base_path", DEFAULT_ROOT)
    return scan_physical_get(keyword=keyword, base_path=base_path)

@app.get("/scan_physical")
def scan_physical_alias(keyword: str = "", base_path: str = DEFAULT_ROOT):
    return scan_physical_get(keyword=keyword, base_path=base_path)

@app.get("/api/clow/status")
def clow_status():
    return {
        "status": "ok",
        "service": "taiji-clow-adapter",
        "time": time.time(),
        "allowed_roots": ALLOWED_ROOTS,
        "upstream": UPSTREAM,
    }
