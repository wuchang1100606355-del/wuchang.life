# 五常智慧雲｜AI 海馬迴
# 統合：度規小模型總拓樸、無明文上下文總成路由器、SQL資料庫、路由器USB死信箱、度規轉譯、分片、語意破碎、Merlin路由器

import hashlib, time, sqlite3
from pathlib import Path

HIPPO_DB = Path("data/ai_hippocampus.db")
DEAD_LETTER_USB_PATH = "/mnt/router_usb/dead_letter_box"
MERLIN_ROUTER_ROLE = "ASUS Merlin Router / Dead Letter Router Node"

def _h(x: str) -> str:
    return hashlib.sha256(str(x).encode()).hexdigest()

def hippocampus_state():
    return {
        "version": "Wuchang-AI-Hippocampus-v1",
        "name": "AI 海馬迴",
        "status": "active",
        "modules": [
            "metric_small_model_topology",
            "nameless_context_router",
            "sqlite_memory_index",
            "router_usb_dead_letter_box",
            "metric_translation_engine",
            "semantic_fragmentation",
            "sharding",
            "asus_merlin_router_firmware_node"
        ],
        "principles": {
            "no_plaintext_context_by_default": True,
            "semantic_fragments_not_fulltext": True,
            "router_usb_dead_letter_box": True,
            "local_first": True,
            "user_controlled_reconstruction": True,
            "external_exfiltration": False
        },
        "paths": {
            "sql_database": str(HIPPO_DB),
            "router_usb_dead_letter_box": DEAD_LETTER_USB_PATH
        },
        "router": MERLIN_ROUTER_ROLE
    }

def init_hippocampus_db():
    HIPPO_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(HIPPO_DB)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hippocampus_fragments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_token TEXT,
        shard_id TEXT,
        metric_code TEXT,
        semantic_hash TEXT,
        fragment_hint TEXT,
        tier TEXT,
        created_at REAL
    )
    """)
    con.commit()
    con.close()
    return {"status": "ok", "db": str(HIPPO_DB)}

def metric_translate(text: str, model: str = "small-metric-model"):
    token = _h(text)
    return {
        "version": "Wuchang-Metric-Translator-v1",
        "model": model,
        "object_token": token[:16],
        "metric_code": token[:32],
        "plaintext_retained": False,
        "rule": "Input is translated into metric code; plaintext should not be stored by default."
    }

def semantic_shatter(text: str, shards: int = 5):
    shards = max(2, min(int(shards), 16))
    token = _h(text)
    pieces = []
    for i in range(shards):
        shard_seed = _h(f"{token}:{i}")[:24]
        pieces.append({
            "shard_id": f"mu_{i}",
            "semantic_hash": shard_seed,
            "fragment_hint": f"fragment-{i}",
            "plaintext": None
        })
    return {
        "version": "Wuchang-Semantic-Shatter-v1",
        "object_token": token[:16],
        "shard_count": shards,
        "fragments": pieces,
        "reconstruction_policy": "user_authorized_only",
        "plaintext_context": "not_stored"
    }

def route_nameless_context(text: str, sensitivity: str = "normal", target: str = "auto"):
    translated = metric_translate(text)
    shattered = semantic_shatter(text)
    if sensitivity in ["pii", "private", "sensitive"]:
        tier = "hot_system_space"
    elif target in ["dead_letter", "router_usb"]:
        tier = "router_usb_dead_letter_box"
    else:
        tier = "warm_sql_index"
    return {
        "version": "Wuchang-Nameless-Context-Router-v1",
        "object_token": translated["object_token"],
        "assigned_tier": tier,
        "metric_code": translated["metric_code"],
        "shards": shattered["fragments"],
        "plaintext_retained": False,
        "dead_letter_available": True,
        "router_node": MERLIN_ROUTER_ROLE
    }

def commit_fragment_index(text: str, sensitivity: str = "normal", target: str = "auto"):
    init_hippocampus_db()
    routed = route_nameless_context(text, sensitivity, target)
    con = sqlite3.connect(HIPPO_DB)
    cur = con.cursor()
    for frag in routed["shards"]:
        cur.execute("""
        INSERT INTO hippocampus_fragments
        (object_token, shard_id, metric_code, semantic_hash, fragment_hint, tier, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            routed["object_token"],
            frag["shard_id"],
            routed["metric_code"],
            frag["semantic_hash"],
            frag["fragment_hint"],
            routed["assigned_tier"],
            time.time()
        ))
    con.commit()
    con.close()
    return {
        "version": "Wuchang-Hippocampus-Commit-v1",
        "status": "indexed",
        "object_token": routed["object_token"],
        "tier": routed["assigned_tier"],
        "db": str(HIPPO_DB),
        "plaintext_stored": False,
        "shard_count": len(routed["shards"])
    }

def dead_letter_state():
    return {
        "version": "Wuchang-RouterUSB-DeadLetter-v1",
        "router": MERLIN_ROUTER_ROLE,
        "path": DEAD_LETTER_USB_PATH,
        "exists": Path(DEAD_LETTER_USB_PATH).exists(),
        "purpose": "store non-plaintext fragments, failed routes, delayed context packets, and audit-safe dead letters",
        "write_policy": "manual_or_authorized_only",
        "plaintext_allowed": False
    }
