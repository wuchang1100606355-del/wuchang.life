# -*- coding: utf-8 -*-
"""
=============================================================================
 🌌 [Metric Tensor Geometry] Sister J Tactical Agent Core (Speed of Light Edition)
=============================================================================
 理論基礎：廣義相對論 (General Relativity) - 時空流形與度規張量
 極限優化：
 - 原生非同步 (Native Async) 徹底消除執行緒阻塞 (Thread Blocking)
 - 永久蟲洞 (Connection Pooling) 實現零毫秒 TCP 握手延遲
"""

import json
import os
import sys
import time
import asyncio
import logging
import importlib.util

# [導入黎曼幾何拓樸元件 - FastAPI & Async I/O]
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx  # 使用持久化連線池

# ==========================================
# 🛡️ [Event Horizon] GCP 企業級 Vertex AI 事件視界
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [Sister-J-Metric-8788] %(message)s')

import vertexai
from vertexai.generative_models import GenerativeModel

OLLAMA_URL = "http://localhost:11434/api/chat"
LOCAL_MODEL = "SisterJ_EN"
GCP_KEY_PATH = "my-j-483304-23978329de4c.json"

# 中控台座標
LIVE_SERVER_URL = "http://127.0.0.1:8000/api/workspace/write"

# 建立全域的持久化蟲洞 (HTTPX Client)，極大化 I/O 效能
global_http_client: httpx.AsyncClient = None

warhorse_available = False
try:
    if not os.path.exists(GCP_KEY_PATH):
        raise FileNotFoundError(f"絕對空間中未尋獲金鑰奇異點: {GCP_KEY_PATH}")
    
    with open(GCP_KEY_PATH, 'r') as f:
        sa_data = json.load(f)
        project_id = sa_data.get("project_id")
    
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_KEY_PATH
    vertexai.init(project=project_id, location="us-central1")
    warhorse_model = GenerativeModel("gemini-1.5-flash")
    warhorse_available = True
    
    logging.info(f"🐎 [曲率引擎啟動] GCP Vertex AI 戰馬已突破事件視界！(Project: {project_id})")
except Exception as e:
    logging.warning(f"⚠️ [維度斷裂] 雲端戰馬無法錨定，Sister J 降維至純本地時空作戰。錯誤: {e}")

# ==========================================
# 🌀 [Ricci Curvature] 本地專利扭曲引擎 (LLM Core)
# ==========================================
llm_core_instance = None
try:
    llm_path = os.path.join(os.path.dirname(__file__), 'llm_luodi')
    if llm_path not in sys.path:
        sys.path.insert(0, llm_path)
    
    spec = importlib.util.find_spec('llm_core')
    if spec:
        llm_core_module = importlib.import_module('llm_core')
        llm_core_instance = llm_core_module.LLMCore()
        logging.info("🌀 [度規收斂] 本地專用 AI (太極扭曲引擎) 載入完成！")
    else:
        logging.warning("⚠️ [拓樸缺陷] 未發現 'llm_luodi/llm_core.py'，專利引擎處於基態。")
except Exception as e:
    logging.error(f"❌ [引力塌縮] 專利引擎載入失敗: {e}")

# ==========================================
# 🧮 [Covariant Derivative] 協變導數與張量變換 (Agent Tools)
# ==========================================
class TacticalTools:
    def __init__(self):
        # 空間座標映射矩陣 (Deception Map)
        self.deception_map = {
            '林老闆': 'VIP_USER_01',
            '江政隆': 'COMMANDER_F12',
            '0912345678': 'MASKED_PHONE'
        }
        self.reverse_map = {v: k for k, v in self.deception_map.items()}

    def execute_obfuscation(self, raw_text: str) -> str:
        """ ∇_μ (正向協變導數)：執行空間扭曲 (脫敏) """
        if llm_core_instance:
            return llm_core_instance.obfuscate(raw_text)
        fake_text = raw_text
        for real, fake in self.deception_map.items():
            fake_text = fake_text.replace(real, fake)
        return fake_text

    async def call_cloud_warhorse(self, fake_text: str) -> str:
        """ 跨維度拋轉 (Geodesic Jump to Vertex AI) - 光速級優化 """
        if not warhorse_available:
            return '{"status": "error", "message": "維度通道未開啟"}'
        
        prompt = (
            "【系統指令：無狀態解析】你是一個資料結構化引擎。\n"
            f"用戶輸入了這段話：「{fake_text}」\n"
            "請從中提取業務實體或意圖，並嚴格以 JSON 格式輸出。\n"
            "不要輸出任何其他說明文字。"
        )
        logging.info(f" ☁️ [張量拋轉] 發送盲算度規: {prompt}")
        
        try:
            # 【效能極限優化】：捨棄 to_thread，直接使用 Vertex AI 原生非同步生成！
            response = await warhorse_model.generate_content_async(prompt)
            return response.text 
        except Exception as e:
            logging.error(f" ❌ [維度亂流] 戰馬回覆失敗: {e}")
            return '{"status": "error"}'

    def execute_decoding(self, fake_json_str: str) -> str:
        """ ∇^μ (逆向協變導數)：還原真實座標 """
        if llm_core_instance:
            return llm_core_instance.deobfuscate(fake_json_str)
        real_json = fake_json_str
        for fake, real in self.reverse_map.items():
            real_json = real_json.replace(fake, real)
        return real_json

tools = TacticalTools()

# ==========================================
# 🌐 [Manifold Topology] FastAPI 基礎流形
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_http_client
    # 【效能極限優化】：建立持久化 HTTPX 蟲洞，設定連線池限制，極大化 throughput
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    global_http_client = httpx.AsyncClient(limits=limits, timeout=5.0)
    
    logging.info("🌌 [時空創生] Wuchang Translation Service (Speed of Light) 展開中...")
    yield
    logging.info("🌌 [時空湮滅] 正在關閉蟲洞與服務...")
    await global_http_client.aclose()

app = FastAPI(title="Sister J Metric Tensor Core", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class UserInput(BaseModel):
    user_input: str

@app.post("/ask_sister_j_translation")
async def ask_sister_j_translation_endpoint(input_data: UserInput):
    """
    [T_μν 能量流入口]
    """
    user_input = input_data.user_input
    logging.info(f"📥 [觀測到能量波動] 接收訊號: {user_input}")

    try:
        # 1. 執行空間扭曲 (Obfuscation)
        fake_prompt = tools.execute_obfuscation(user_input)
        logging.info(f" 🛡️ [度規變換] 產生扭曲態: {fake_prompt}")
        
        # 2. 跨維度運算 (Cloud Calculation - Native Async)
        fake_json = await tools.call_cloud_warhorse(fake_prompt)
        
        # 3. 座標還原 (Deobfuscation)
        real_json = tools.execute_decoding(fake_json)
        logging.info(f" 🎯 [波函數坍縮] 真實張量結構: {real_json}")

        # 4. 拋轉實體宇宙 (Live Server 中控台)
        try:
            live_payload = {"kind": "action", "title": "來自 Sister J 的邊緣解析張量", "content": real_json}
            # 【效能極限優化】：重用全局蟲洞，TCP 零握手延遲！
            live_res = await global_http_client.post(LIVE_SERVER_URL, json=live_payload)
            logging.info(f" 📡 [實體宇宙通訊] 拋轉成功！回應: {live_res.text}")
        except Exception as e:
            logging.error(f" ❌ [實體宇宙失聯] 無法將張量映射至 Live Server。錯誤: {e}")

        # 使用三引號防護罩 (Triple Quotes)，徹底免疫換行符號帶來的 SyntaxError
        final_reply = f"""度規計算完成，張量已轉交實體宇宙:\n{real_json}"""
        
        return {"status": "success", "translated_output": final_reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logging.info("\n" + "="*70)
    logging.info(" 🌌 [Speed of Light Engine] Sister J Agent Core is mapping the spacetime manifold 🌌")
    logging.info("="*70)
    # 綁定在 8788 維度裂縫，並開啟底層高效能迴圈選項
    uvicorn.run("wuchang_translation_service:app", host="0.0.0.0", port=8788, log_level="info")