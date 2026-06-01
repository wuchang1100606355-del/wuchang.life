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
