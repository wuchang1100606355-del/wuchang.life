# ☯️ 五常太極 8.0 - 核心大一統守護進程 (Main Daemon)
# 整合 Y 軸 (Redis 瞬發氣海) 與 X 軸 (SQLite 玄武地碟)

import redis
import sqlite3
import json
import hashlib
import time
import os
import threading

# ==========================================
# 🛡️ X 軸：玄武地碟引擎
# ==========================================
class TaijiGroundDB:
    def __init__(self, db_path="./f5_core_memory.db"):
        self.db_path = db_path
        self._init_db_and_pragmas()
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)

    def _init_db_and_pragmas(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("PRAGMA busy_timeout=30000;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sister_j_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        element TEXT,
                        memory_text TEXT NOT NULL,
                        context_tag TEXT
                    )
                """)
                print("🛡️ [玄武地碟] 啟動成功！")
        except Exception as e:
            print(f"❌ [玄武地碟] 初始化失敗: {e}")

    def safe_insert(self, element: str, memory_text: str, context_tag: str):
        for attempt in range(3):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("BEGIN TRANSACTION;")
                    cursor.execute(
                        "INSERT INTO sister_j_memory (timestamp, element, memory_text, context_tag) VALUES (datetime('now', 'localtime'), ?, ?, ?)",
                        (element, memory_text, context_tag)
                    )
                    cursor.execute("COMMIT;")
                    return True
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    break
        return False

# ==========================================
# ⚡ Y 軸：赤兔 Redis 氣海引擎
# ==========================================
class TaijiRedisEngine:
    def __init__(self, db_engine: TaijiGroundDB, host='127.0.0.1', port=6379, password='taiji_pulse_secret_888'):
        pool = redis.ConnectionPool(host=host, port=port, password=password, decode_responses=True)
        self.r = redis.Redis(connection_pool=pool)
        self.queue_name = "taiji_5d_pending_queue"
        self.db_engine = db_engine # 注入地碟引擎
        self.r.ping()
        print("⚡ [赤兔氣海] 啟動成功！")

    def instant_thread_push(self, intent_data: dict, context: str) -> str:
        """前台瞬發緒：0 延遲推入氣海"""
        five_d_code = hashlib.sha3_256(f"LAN-GROUP-B:{context}:{time.time_ns()}:INSTANT".encode('utf-8')).hexdigest()
        payload = {"5d_code": five_d_code, "timestamp": time.time(), "context": context, "data": intent_data}
        self.r.lpush(self.queue_name, json.dumps(payload))
        print(f"[{context}] ⚡ 交易懸浮於氣海，5D碼: {five_d_code}")
        return five_d_code

    def cleanup_thread_worker(self):
        """背景清理緒：從氣海拉出，寫入地碟"""
        print("🌀 [清理緒] 背景巡邏中，隨時準備物理坍縮...")
        while True:
            task_data = self.r.brpop(self.queue_name, timeout=5)
            if task_data:
                _, payload_str = task_data
                payload = json.loads(payload_str)
                five_d_code = payload['5d_code']
                data_str = json.dumps(payload['data'], ensure_ascii=False)
                
                print(f"\n[清理緒] 📥 捕獲 5D碼: {five_d_code}，啟動物理固化...")
                
                # 🛑 呼叫玄武地碟，執行真正的物理寫入
                success = self.db_engine.safe_insert(
                    element="Earth_Trust", 
                    memory_text=data_str, 
                    context_tag=f"5D:{five_d_code}"
                )
                
                if success:
                    print(f"[清理緒] ✅ {five_d_code} 已刻入實體地碟！")
                else:
                    print(f"[清理緒] ❌ {five_d_code} 地碟固化失敗，資料可能遺失！")

# ==========================================
# 🧪 戰場啟動與端到端火力測試
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("☯️ 五常太極 8.0 - 核心守護進程啟動")
    print("="*50)
    
    # 1. 喚醒雙引擎
    ground_db = TaijiGroundDB()
    redis_engine = TaijiRedisEngine(db_engine=ground_db)
    
    # 2. 啟動背景清理緒
    cleanup_worker = threading.Thread(target=redis_engine.cleanup_thread_worker, daemon=True)
    cleanup_worker.start()

    # 3. 模擬前台極速開火
    time.sleep(1)
    print("\n--- 模擬客顯機與 POS 瞬間爆發結帳 ---")
    redis_engine.instant_thread_push({"action": "結帳", "member": "江政隆", "total": 1000}, "POS")
    redis_engine.instant_thread_push({"action": "結帳", "member": "A棟主委", "total": 500}, "POS")
    redis_engine.instant_thread_push({"action": "AI對話", "prompt": "社區規約第12條"}, "CHAT")
    
    # 保持主程式運行，讓背景清理緒有時間寫入資料庫
    time.sleep(5)
    print("\n✅ 端到端 (End-to-End) 測試完成！請檢查目錄下是否多出 f5_core_memory.db 與其 WAL 檔案。")