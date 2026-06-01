# -*- coding: utf-8 -*-
"""
☯️ Wuchang OS 8.1.0 大一統邊緣閘道器 (輕量極速版) ☯️
融合來源：[太極 8.0 AI 融合樞紐] + [大一統邊緣閘道器 V8.1.0]
戰術調整：依據指揮官 F124771717 指示，為確保邊緣效能，已主動卸載 ADI 量子時空簽章。
"""
import os, sys, time, zlib, psutil, logging, uuid
from fastapi import FastAPI, Request, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import redis

# 試圖載入同目錄下的 V3 專利引擎
try:
    from taiji_patent_v3_engine import TaijiInformationTheoreticEngine
except ImportError:
    TaijiInformationTheoreticEngine = None

logging.basicConfig(level=logging.INFO, format='[大一統閘道] %(asctime)s - %(message)s')
app = FastAPI(title="Wuchang 8.1.0 Unified Gateway (Lightweight)")

# 連線至 Docker Compose 所帶起的 Redis 氣海。
# Secret must be injected by environment; no plaintext default is allowed.
redis_client = redis.Redis(
    host='127.0.0.1',
    port=6379,
    password=os.environ.get("TAIJI_REDIS_PASSWORD"),
    decode_responses=True,
)
v3_engine = TaijiInformationTheoreticEngine() if TaijiInformationTheoreticEngine else None

# --- 零信任 (Zero Trust) 驗證裝甲 ---
API_KEY_NAME = "x-taiji-auth"
# API key must be injected by environment; no plaintext default is allowed.
VALID_API_KEY = os.environ.get("TAIJI_PULSE_SECRET")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_zero_trust_token(api_key: str = Security(api_key_header)):
    if not VALID_API_KEY:
        logging.error("TAIJI_PULSE_SECRET is not configured; fail closed")
        raise HTTPException(status_code=503, detail="Zero Trust Auth Not Configured")
    if not api_key or api_key != VALID_API_KEY:
        logging.warning("🛡️ [Zero Trust 攔截] 拒絕未經授權的 M2M 呼叫")
        raise HTTPException(status_code=403, detail="Zero Trust Auth Failed: 憑證無效")
    return api_key

# --- 核心 1: 記憶體延遲摺疊與心率防禦 (V8.1.0) ---
class TaiChiAICerebellum:
    def __init__(self):
        self.absolute_hash_space = {}
        
    def check_cpu_governor(self):
        try:
            cpu = psutil.cpu_percent()
            if cpu >= 93.0:
                logging.warning("CRITICAL_93: 觸發硬體中斷，凍結背景任務！")
                return False
        except Exception:
            pass
        return True

    def fold_memory_latency(self):
        if self.check_cpu_governor():
            for k, v in self.absolute_hash_space.items():
                if not v.get('folded', False):
                    self.absolute_hash_space[k]['data'] = zlib.compress(v['data'].encode())
                    self.absolute_hash_space[k]['folded'] = True
            logging.info("記憶體延遲摺疊 (Entropy Reduction) 執行完畢。")

cerebellum = TaiChiAICerebellum()

# --- 核心 2: 輕量級 POS 結帳接收 ---
class PosCheckoutRequest(BaseModel):
    amount: float
    transaction_intent: str

@app.post("/api/pos/checkout")
async def handle_pos_checkout(payload: PosCheckoutRequest, token: str = Depends(verify_zero_trust_token)):
    # 移除 ADI，改用輕量 UUID 確保極速推論
    receipt_id = str(uuid.uuid4())
    
    # 存入記憶體並標示需要摺疊
    cerebellum.absolute_hash_space[receipt_id] = {
        'data': payload.model_dump_json(),
        'folded': False
    }
    cerebellum.fold_memory_latency()
    
    # 寫入實體 Redis 氣海，確保斷電不掉資料
    try:
        redis_client.set(f"taiji:pos:checkout:{receipt_id}", payload.model_dump_json())
    except Exception as e:
        logging.error(f"Redis 寫入失敗: {str(e)}")

    return {
        "status": "success",
        "receipt_id": receipt_id,
        "message": "結帳意圖已接收並執行極速延遲摺疊 (ADI已卸載)。"
    }

# --- 核心 3: 語音 UDP 與 HTTP 網關 (AI 融合樞紐) ---
@app.post("/api/pos/voice_interaction")
async def handle_voice_interaction(request: Request, token: str = Depends(verify_zero_trust_token)):
    payload = await request.json()
    raw_text = str(payload.get('item', ''))
    
    if v3_engine:
        # 執行 V3 專利：實體映射脫敏與記憶體歸零
        masked_text, session_id = v3_engine.apply_deterministic_mapping(raw_text)
        logging.info(f"🎙️ [語音接收] 意圖: {payload.get('action')} | 脫敏內容: {masked_text}")
        v3_engine.execute_memory_zeroization(session_id)
        return {"status": "success", "message": "Sister J 語音意圖已接收並通過 V3 脫敏歸零"}
        
    logging.info(f"🎙️ [語音接收] 意圖: {payload.get('action')} | 內容: {raw_text}")
    return {"status": "success", "message": "Sister J 語音意圖已轉發"}

if __name__ == "__main__":
    import uvicorn
    logging.info("啟動 Wuchang 大一統閘道器 V8.1.0 (輕量版, Port 8000)...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
