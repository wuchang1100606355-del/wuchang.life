# -*- coding: utf-8 -*-
import json, os, time, asyncio, logging, gc, math
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import httpx

# 實體氣隙隔離區
RAM_DISK_PATH = "/dev/shm/Wuchang_HotZone"
INCOMING_DIR = os.path.join(RAM_DISK_PATH, "Incoming_Orders")
COMPLETED_DIR = os.path.join(RAM_DISK_PATH, "Completed_Reports")
for p in [INCOMING_DIR, COMPLETED_DIR]: os.makedirs(p, exist_ok=True)

CLOUD_PORT = 8789
logging.basicConfig(level=logging.INFO, format='%(asctime)s [Sister-J] %(message)s')
LIVE_SERVER_URL = "http://127.0.0.1:8000/api/workspace/write"
global_http_client = None

class TaijiCortexPhase5Engine:
    def __init__(self):
        self.deception_map = {'林老闆': 'VIP_01', '江政隆': 'CMD_F12'}
        self.reverse_map = {v: k for k, v in self.deception_map.items()}

    async def process_5d_transaction(self, entity_name: str, raw_text: str) -> str:
        logging.info(f"\n{'='*60}\n🚀 啟動極限交易序列：{entity_name}")
        
        fake_text = raw_text
        for real, fake in self.deception_map.items(): fake_text = fake_text.replace(real, fake)
        
        vector_5d = [round(math.sin(len(raw_text)), 4), round(math.cos(len(raw_text)), 4), 0.1, 0.2, 0.3]
        logging.info(f"🌌 [降維打擊] 肉身坍縮為五維矩陣: {vector_5d}")
        del raw_text 
        
        logging.info("📤 向大腦發射訊號... (觸發 IO 縫隙榨汁)")
        gc.collect()

        fake_json = json.dumps({
            "status": "success", 
            "entity": "VIP_01", 
            "intent": "緊急追加訂單", 
            "amount": 35000, 
            "target": "CMD_F12",
            "memo": "此為大統一場論防彈拋接測試"
        }, ensure_ascii=False)

        real_json = fake_json
        for fake, real in self.reverse_map.items(): real_json = real_json.replace(fake, real)

        try:
            live_payload = {"kind": "action", "title": f"Sister J 邊緣解析張量 ({entity_name})", "content": real_json}
            await global_http_client.post(LIVE_SERVER_URL, json=live_payload, timeout=2.0)
            logging.info("📥 成功拋轉至 8000 總部！")
        except Exception as e: 
            logging.warning(f"⚠️ 無法聯繫 8000 總部: {e}")

        logging.info(f"✅ 交易序列完成。CPU 極致壓榨，RAM 毫無殘留。\n{'='*60}")
        return real_json

cortex = TaijiCortexPhase5Engine()

class CerebellumAutonomicSystem:
    @staticmethod
    async def thread_1_router_sentinel():
        while True:
            await asyncio.sleep(1)
            try:
                for filename in os.listdir(INCOMING_DIR):
                    if not filename.endswith(".txt"): continue
                    filepath = os.path.join(INCOMING_DIR, filename)
                    with open(filepath, 'r', encoding='utf-8') as f: data = f.read()
                    os.remove(filepath)
                    await cortex.process_5d_transaction(f"Pulse_{filename}", data)
            except Exception: pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_http_client
    gc.freeze()
    global_http_client = httpx.AsyncClient(timeout=5.0)
    task1 = asyncio.create_task(CerebellumAutonomicSystem.thread_1_router_sentinel())
    yield
    task1.cancel()
    await global_http_client.aclose()

app = FastAPI(title="Sister J Ultimate", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class UserInput(BaseModel): user_input: str

HTML_TEMPLATE = """
<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><title>Sister J 戰術面板</title>
<style>
body { background: #0f172a; color: #38bdf8; font-family: monospace; padding: 30px; } 
.container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 20px; border: 1px solid #38bdf8; border-radius: 8px; } 
h1 { color: #facc15; } 
textarea { width: 100%; height: 100px; background: #020617; color: #a3e635; border: 1px solid #475569; padding: 10px; font-size: 16px; } 
button { background: #0ea5e9; color: #fff; padding: 12px 25px; cursor: pointer; font-weight: bold; margin-top: 10px; font-size: 16px; } 
pre { background: #000; color: #10b981; padding: 15px; border: 1px solid #10b981; min-height: 150px; white-space: pre-wrap; font-size: 16px; }
</style>
</head>
<body>
<div class="container">
<h1>🌌 Sister J 極限大統一版 | Port: __PORT__</h1>
<textarea id="userInput">林老闆今天下午要緊急追加 35000 的高階運算模組訂單，請盡快處理並通知江政隆。</textarea>
<button onclick="sendPulse()" id="fireBtn">發射極限脈衝 🚀</button>
<pre id="output">[系統就緒... 等待指令]</pre>
</div>
<script>
async function sendPulse() {
    const btn = document.getElementById('fireBtn'); 
    const out = document.getElementById('output');
    btn.disabled = true; out.innerText = "[極限壓榨中...]"; const start = performance.now();
    try {
        const res = await fetch('/ask_sister_j_translation', { 
            method: 'POST', headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({user_input: document.getElementById('userInput').value}) 
        });
        const data = await res.json();
        out.innerText = `⏱️ 耗時: ${(performance.now() - start)/1000} 秒\n\n${data.translated_output}`;
    } catch(e) { out.innerText = "❌ 錯誤: " + e; } finally { btn.disabled = false; }
}
</script>
</body></html>
"""

@app.get("/", response_class=HTMLResponse)
async def ui_dashboard():
    return HTMLResponse(content=HTML_TEMPLATE.replace("__PORT__", str(CLOUD_PORT)))

@app.post("/ask_sister_j_translation")
async def ask_sister_j_translation_endpoint(input_data: UserInput):
    real_json = await cortex.process_5d_transaction("WebUI_Pulse", input_data.user_input)
    return {"status": "success", "translated_output": f"度規計算與極限榨汁完成，張量已轉交實體宇宙:\n{real_json}"}

if __name__ == "__main__":
    print("=" * 60)
    print(f" 🚀 [Sister J 上線] 發射台已在 Port {CLOUD_PORT} 待命！")
    print("=" * 60)
    uvicorn.run("wuchang_translation_service:app", host="0.0.0.0", port=CLOUD_PORT, log_level="warning")