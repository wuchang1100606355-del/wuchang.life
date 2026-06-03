#!/usr/bin/env bash
set -Eeuo pipefail

BASE="$HOME/Taiji_Hub"
RUN="$BASE/run"
LOG="$BASE/logs"
DATA="$BASE/data"

mkdir -p "$BASE" "$RUN" "$LOG" \
  "$DATA/ledger" \
  "$DATA/fragments/disk_a" \
  "$DATA/fragments/disk_b" \
  "$DATA/fragments/disk_c" \
  "$DATA/deadletter" \
  "$DATA/secrets" \
  "$BASE/web"

cd "$BASE"

echo "======================================================"
echo "⚡ 五常太極大陣：安全開機 + 五維碼記憶體治理 v1"
echo "======================================================"

python3 - <<'PY_DEPS'
import importlib.util, subprocess, sys
packages = [("fastapi", "fastapi"), ("uvicorn", "uvicorn"), ("pydantic", "pydantic")]
missing = [p for m, p in packages if importlib.util.find_spec(m) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", *missing])
print("✅ Python 套件 OK")
PY_DEPS

if [ ! -f "$DATA/secrets/owner_memory_secret.key" ]; then
  python3 - <<PY_SECRET
import secrets, pathlib, os
p = pathlib.Path("$DATA/secrets/owner_memory_secret.key")
p.write_text(secrets.token_hex(64))
os.chmod(p, 0o600)
print("✅ Owner Secret 已建立")
PY_SECRET
else
  chmod 600 "$DATA/secrets/owner_memory_secret.key"
  echo "✅ Owner Secret 已存在"
fi

cat > "$BASE/taiji_metric_memory_core.py" <<'PY_CORE'
import os, json, time, base64, hashlib, sqlite3
from pathlib import Path
from typing import Any, Dict, Tuple, Set

FiveDCode = Tuple[float, float, float, float, float]

BASE = Path.home() / "Taiji_Hub"
DATA = BASE / "data"
DB = DATA / "ledger" / "metric_memory.sqlite3"
FRAG = DATA / "fragments"
DLQ = DATA / "deadletter"
SECRET = DATA / "secrets" / "owner_memory_secret.key"

for p in [DB.parent, FRAG/"disk_a", FRAG/"disk_b", FRAG/"disk_c", DLQ, SECRET.parent]:
    p.mkdir(parents=True, exist_ok=True)

def now():
    return time.time()

def js(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def code5(code):
    if not isinstance(code, (list, tuple)) or len(code) != 5:
        raise ValueError("FiveDCode must be [x,y,z,time,scale]")
    return tuple(float(v) for v in code)

def addr(code):
    return hashlib.sha256(js(code5(code)).encode()).hexdigest()

def h(x):
    return hashlib.sha256(js(x).encode()).hexdigest()

def secret():
    if not SECRET.exists():
        SECRET.write_text(os.urandom(64).hex())
        os.chmod(SECRET, 0o600)
    return SECRET.read_text().strip().encode()

def stream(address, n):
    s = secret()
    out = bytearray()
    i = 0
    while len(out) < n:
        out.extend(hashlib.sha256(s + address.encode() + str(i).encode()).digest())
        i += 1
    return bytes(out[:n])

def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))

class Ledger:
    def __init__(self):
        with sqlite3.connect(DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS fragments(
                address TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_access REAL NOT NULL,
                status TEXT NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                address TEXT,
                code TEXT,
                reason TEXT,
                created_at REAL NOT NULL
            )""")
            c.commit()

    def fragment(self, address, code, phash):
        with sqlite3.connect(DB) as c:
            old = c.execute("SELECT created_at FROM fragments WHERE address=?", (address,)).fetchone()
            created = old[0] if old else now()
            c.execute("INSERT OR REPLACE INTO fragments VALUES (?, ?, ?, ?, ?, ?)",
                      (address, js(code), phash, created, now(), "active"))
            c.commit()

    def touch(self, address):
        with sqlite3.connect(DB) as c:
            c.execute("UPDATE fragments SET last_access=? WHERE address=?", (now(), address))
            c.commit()

    def event(self, event_type, address=None, code=None, reason=""):
        with sqlite3.connect(DB) as c:
            c.execute("INSERT INTO events(event_type,address,code,reason,created_at) VALUES(?,?,?,?,?)",
                      (event_type, address, js(code) if code else None, reason, now()))
            c.commit()

    def status(self):
        with sqlite3.connect(DB) as c:
            fragments = c.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
            events = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"db": str(DB), "fragments": fragments, "events": events}

class Deadletter:
    def write(self, reason, code=None, payload=None):
        event_id = hashlib.sha256(f"{time.time()}:{reason}".encode()).hexdigest()[:24]
        obj = {
            "event_id": event_id,
            "reason": reason,
            "code": list(code) if code else None,
            "payload_hash": h(payload) if payload is not None else None,
            "redacted_summary": "payload_redacted",
            "created_at": now(),
        }
        (DLQ / f"{event_id}.json").write_text(js(obj), encoding="utf-8")
        return obj

class Fragments:
    def write(self, address, payload):
        raw = js(payload).encode()
        enc = xor(raw, stream(address, len(raw)))
        a = len(enc)//3
        b = len(enc)*2//3
        parts = [enc[:a], enc[a:b], enc[b:]]
        for disk, part in zip(["disk_a", "disk_b", "disk_c"], parts):
            (FRAG/disk/f"{address}.frag").write_bytes(base64.b64encode(part))

    def read(self, address):
        parts = []
        for disk in ["disk_a", "disk_b", "disk_c"]:
            p = FRAG/disk/f"{address}.frag"
            if not p.exists():
                raise FileNotFoundError(f"missing {disk}/{address}.frag")
            parts.append(base64.b64decode(p.read_bytes()))
        enc = b"".join(parts)
        raw = xor(enc, stream(address, len(enc)))
        return json.loads(raw.decode())

class Memory:
    def __init__(self):
        self.ram: Dict[FiveDCode, Any] = {}
        self.protected: Set[FiveDCode] = set()
        self.ledger = Ledger()
        self.dead = Deadletter()
        self.frag = Fragments()

    def halo(self, code):
        x, y, z, t, s = code5(code)
        return {
            (x, y, z, t, s),
            (x+1, y, z, t, s),
            (x-1, y, z, t, s),
            (x, y+1, z, t, s),
            (x, y-1, z, t, s),
        }

    def evict(self, current_time):
        killed = 0
        for c in list(self.ram.keys()):
            if c not in self.protected and c[3] < float(current_time):
                del self.ram[c]
                killed += 1
        if killed:
            self.ledger.event("temporal_eviction", reason=f"evicted={killed}")
        return {"evicted": killed, "ram_items": len(self.ram)}

    def set(self, code, value):
        c = code5(code)
        a = addr(c)
        self.protected = self.halo(c)
        self.ram[c] = value
        try:
            self.frag.write(a, value)
            self.ledger.fragment(a, c, h(value))
            self.ledger.event("write", a, c, "ram_plus_fragment")
        except Exception as e:
            self.dead.write(f"write_failed:{e}", c, value)
            self.ledger.event("deadletter", a, c, str(e))
            raise
        return {"ok": True, "address": a, "payload_hash": h(value), "equilibrium": self.evict(c[3])}

    def get(self, code):
        c = code5(code)
        a = addr(c)
        self.protected = self.halo(c)
        eq = self.evict(c[3])
        if c in self.ram:
            self.ledger.touch(a)
            self.ledger.event("read_hit", a, c, "ram")
            return {"ok": True, "source": "ram", "address": a, "value": self.ram[c], "equilibrium": eq}
        try:
            v = self.frag.read(a)
            self.ram[c] = v
            self.ledger.touch(a)
            self.ledger.event("read_regenerate", a, c, "fragment")
            return {"ok": True, "source": "fragment_regeneration", "address": a, "value": v, "equilibrium": eq}
        except Exception as e:
            d = self.dead.write(f"read_failed:{e}", c, None)
            self.ledger.event("deadletter", a, c, str(e))
            return {"ok": False, "source": "deadletter", "address": a, "error": str(e), "deadletter": d, "equilibrium": eq}

    def status(self):
        return {
            "runtime": "taiji_metric_memory_core",
            "ram_items": len(self.ram),
            "protected_items": len(self.protected),
            "ledger": self.ledger.status(),
            "fragment_root": str(FRAG),
            "deadletter_root": str(DLQ),
            "policy": {
                "device_owns_existence": True,
                "container_owns_dispatch": True,
                "plaintext_persistence": False,
                "deadletter_reversible": False,
                "single_disk_reconstructable": False,
                "time_eviction": True,
                "metric_regeneration": True
            }
        }

MEMORY = Memory()
PY_CORE

cat > "$BASE/taiji_metric_memory_api.py" <<'PY_API'
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, List
import os, time
from taiji_metric_memory_core import MEMORY

BOOT = time.time()
app = FastAPI(title="Taiji Metric Memory API")

class WriteReq(BaseModel):
    code: List[float]
    value: Any

class ReadReq(BaseModel):
    code: List[float]

@app.get("/health")
def health():
    return {"status": "ok", "service": "metric_memory", "pid": os.getpid(), "uptime": round(time.time()-BOOT, 2)}

@app.get("/memory/status")
def status():
    return MEMORY.status()

@app.post("/memory/write")
def write(req: WriteReq):
    return MEMORY.set(req.code, req.value)

@app.post("/memory/read")
def read(req: ReadReq):
    return MEMORY.get(req.code)

@app.post("/memory/evict")
def evict(current_time: float):
    return MEMORY.evict(current_time)
PY_API

cat > "$BASE/taiji_core_stub.py" <<'PY_CORE_STUB'
from fastapi import FastAPI
import os, time
BOOT=time.time()
app=FastAPI(title="Taiji Policy Collapse Core")
@app.get("/health")
def health():
    return {
        "status":"ok",
        "service":"policy_collapse_core",
        "pid":os.getpid(),
        "uptime":round(time.time()-BOOT,2),
        "rule":"Agent 只能提案，Core 才能塌縮，Claw 才能執行，Ledger 必須留痕"
    }
PY_CORE_STUB

cat > "$BASE/taiji_claw_stub.py" <<'PY_CLAW'
from fastapi import FastAPI
import os, time
BOOT=time.time()
app=FastAPI(title="Taiji Claw Executor")
@app.get("/health")
def health():
    return {
        "status":"ok",
        "service":"claw_executor",
        "pid":os.getpid(),
        "uptime":round(time.time()-BOOT,2),
        "rule":"只執行 core 授權後的本機動作"
    }
PY_CLAW

cat > "$BASE/web/index.html" <<'HTML_WEB'
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>五常太極大陣</title>
<style>
body{font-family:system-ui,"Noto Sans TC",sans-serif;background:#111;color:#eee;padding:32px;line-height:1.7}
.card{background:#1c1c1c;border:1px solid #333;border-radius:16px;padding:20px;margin:16px 0}
code{background:#000;padding:2px 6px;border-radius:6px}
a{color:#8fd3ff}
</style>
</head>
<body>
<h1>⚡ 五常太極大陣</h1>
<div class="card">
<h2>系統狀態</h2>
<p>8000 戰情室、9004 Claw、9090 Core、9101 五維碼記憶體核心。</p>
</div>
<div class="card">
<h2>記憶體治理</h2>
<p>FiveDCode = <code>(x, y, z, time, scale)</code></p>
<p>時間淘汰、映射再生、分碟碎片、死信箱不可逆稽核。</p>
</div>
</body>
</html>
HTML_WEB

safe_kill(){
  name="$1"
  pidfile="$RUN/$name.pid"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile" || true)"
    if [ -n "${pid:-}" ] && ps -p "$pid" >/dev/null 2>&1; then
      echo "🧹 停止 $name PID=$pid"
      kill "$pid" || true
      sleep 1
      ps -p "$pid" >/dev/null 2>&1 && kill -9 "$pid" || true
    fi
    rm -f "$pidfile"
  fi
}

for s in warroom_8000 claw_9004 core_9090 memory_9101; do
  safe_kill "$s"
done

start_svc(){
  name="$1"
  port="$2"
  cmd="$3"
  log="$LOG/$name.log"
  pidfile="$RUN/$name.pid"
  nohup bash -lc "$cmd" > "$log" 2>&1 &
  pid=$!
  echo "$pid" > "$pidfile"
  sleep 2
  if ps -p "$pid" >/dev/null 2>&1; then
    echo "✅ $name Port=$port PID=$pid"
  else
    echo "❌ $name 啟動失敗"
    tail -n 40 "$log" || true
    exit 1
  fi
}

start_svc "warroom_8000" "8000" "cd '$BASE/web' && python3 -m http.server 8000 --bind 127.0.0.1"
start_svc "claw_9004" "9004" "cd '$BASE' && python3 -m uvicorn taiji_claw_stub:app --host 127.0.0.1 --port 9004"
start_svc "core_9090" "9090" "cd '$BASE' && python3 -m uvicorn taiji_core_stub:app --host 127.0.0.1 --port 9090"
start_svc "memory_9101" "9101" "cd '$BASE' && python3 -m uvicorn taiji_metric_memory_api:app --host 127.0.0.1 --port 9101"

check(){
  name="$1"
  url="$2"
  if curl -fsS --max-time 3 "$url" >/dev/null; then
    echo "✅ $name OK"
  else
    echo "❌ $name FAIL：$url"
  fi
}

check "戰情室 8000" "http://127.0.0.1:8000"
check "Claw 9004" "http://127.0.0.1:9004/health"
check "Core 9090" "http://127.0.0.1:9090/health"
check "Memory 9101" "http://127.0.0.1:9101/health"

curl -fsS -X POST "http://127.0.0.1:9101/memory/write" \
  -H "Content-Type: application/json" \
  -d '{"code":[10,10,10,1,1],"value":{"name":"五常微度規核心","mode":"time_eviction_metric_regeneration","plain_text_persistence":false}}' >/dev/null \
  && echo "✅ 五維碼記憶寫入成功" || echo "❌ 五維碼記憶寫入失敗"

echo "🧠 五維碼記憶讀取測試："
curl -fsS -X POST "http://127.0.0.1:9101/memory/read" \
  -H "Content-Type: application/json" \
  -d '{"code":[10,10,10,1,1]}' | python3 -m json.tool || true

echo
echo "======================================================"
echo "✅ 五常大陣開機完成"
echo "======================================================"
echo "戰情室：http://127.0.0.1:8000"
echo "Claw ：http://127.0.0.1:9004/health"
echo "Core ：http://127.0.0.1:9090/health"
echo "記憶體：http://127.0.0.1:9101/memory/status"
echo
echo "以後只要執行："
echo "bash ~/Taiji_Hub/taiji_boot_memory_v1.sh"
echo "======================================================"
