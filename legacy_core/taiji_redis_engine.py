# ☯️ 五常太極 8.0 - Redis 氣海引擎 (取代 tmpfs)
# 負責管理「瞬發緒」的極速寫入與「清理緒」的背景非同步拉取

import redis
import json
import hashlib
import time
import threading

class TaijiRedisEngine:
    def __init__(self, host='127.0.0.1', port=6379, password='taiji_pulse_secret_888'):
        # 建立 Redis 連線池 (工業級做法，支援高併發)
        pool = redis.ConnectionPool(
            host=host, 
            port=port, 
            password=password, 
            decode_responses=True # 自動將 byte 轉回 string
        )
        self.r = redis.Redis(connection_pool=pool)
        self.queue_name = "taiji_5d_pending_queue"

        # 測試連線是否成功
        try:
            self.r.ping()
            print("✅ 成功連線至 Redis 氣海！")
        except Exception as e:
            print(f"❌ 無法連線至 Redis: {e}")

    def generate_5d_code(self, context: str) -> str:
        """生成五維時空碼 (X:Y:Z:T:S)"""
        raw = f"LAN-GROUP-B:{context}:{time.time_ns()}:INSTANT_STATE"
        return hashlib.sha3_256(raw.encode('utf-8')).hexdigest()

    # ==========================================
    # ⚡ [Y軸] 瞬發緒：極速寫入氣海 (0 延遲)
    # ==========================================
    def instant_thread_push(self, intent_data: dict, context: str) -> str:
        """前台客顯機/POS 呼叫此方法。推入 Redis 佇列左側。"""
        five_d_code = self.generate_5d_code(context)
        payload = {
            "5d_code": five_d_code,
            "timestamp": time.time(),
            "context": context,
            "data": intent_data
        }
        self.r.lpush(self.queue_name, json.dumps(payload))
        print(f"[瞬發緒] ⚡ 交易已懸浮於氣海，5D碼: {five_d_code}")
        return five_d_code

    # ==========================================
    # 🧹 [Y軸] 清理緒：活體探測與背景處理
    # ==========================================
    def cleanup_thread_worker(self):
        """背景常駐程式。從 Redis 佇列右側拿出任務處理。"""
        print("🌀 [清理緒] 背景守護進程已啟動，正在監聽 Redis 氣海...")
        while True:
            task_data = self.r.brpop(self.queue_name, timeout=5)
            if task_data:
                _, payload_str = task_data
                payload = json.loads(payload_str)
                five_d_code = payload['5d_code']
                print(f"\n[清理緒] 📥 捕獲任務，準備進行 X 軸坍縮！")
                print(f" -> 5D 碼: {five_d_code}")
                print(f" -> 原始資料: {payload['data']}")
                print(f"[清理緒] ✅ 任務 {five_d_code} 處理完畢。")

if __name__ == "__main__":
    engine = TaijiRedisEngine()

    # 1. 啟動背景清理緒
    cleanup_worker = threading.Thread(target=engine.cleanup_thread_worker, daemon=True)
    cleanup_worker.start()

    # 2. 模擬前台 POS 瞬間爆發 3 筆結帳 (瞬發緒)
    print("\n--- 模擬前台 POS 瞬間高併發結帳 ---")
    engine.instant_thread_push({"member": "江政隆", "amount": 100}, "POS_CHECKOUT")
    engine.instant_thread_push({"member": "五常會員A", "amount": 50}, "POS_CHECKOUT")
    engine.instant_thread_push({"member": "五常會員B", "amount": 200}, "POS_CHECKOUT")

    # 讓主程式等待一下，觀察背景輸出
    time.sleep(3)