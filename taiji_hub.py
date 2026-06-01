# -*- coding: utf-8 -*-
import socket, threading, uvicorn, time, json, hashlib, html
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyD1S280xvybM4RdJR6jhgHJXKVAG0pburM"
genai.configure(api_key=GEMINI_API_KEY)

class TaijiAIEngine:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("[AI Engine] Gemini AI API Connected!")

    def process_text_intent(self, text, source):
        print(f"[AI Parsing] {source}: {text}")
        prompt = f'你是一個POS系統AI。請將客人語音轉為JSON: {{"action": "點餐", "items": ["品項1"], "remark": "備註"}}。客人說：{text}。嚴格只輸出JSON。'
        try:
            res = self.model.generate_content(prompt)
            clean = res.text.replace('`json', '').replace('`', '').strip()
            intent = json.loads(clean)
            print(f"[AI Success] {intent}")
            return intent
        except Exception as e:
            print(f"[AI Error] {e}")
            return {"error": str(e)}

ai_brain = TaijiAIEngine()

def udp_audio_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 9999))
    print("[UDP Engine] Listening on 9999...")
    while True:
        try:
            data, addr = sock.recvfrom(4096)
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=udp_audio_listener, daemon=True).start()
    yield

app = FastAPI(title="Taiji 8.0 Hub", lifespan=lifespan)
workspace_memory = []

@app.get("/", response_class=HTMLResponse)
def read_root():
    return '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>太極神級語音終端</title>
<style>body{font-family:sans-serif;text-align:center;padding-top:50px;background:#121212;color:#fff;}
.mic-btn{width:220px;height:220px;border-radius:50%;font-size:32px;background:#bb86fc;border:none;margin-top:20px;}
#status{margin-top:30px;font-size:24px;color:#cf6679;} #ai-result{margin-top:20px;font-size:20px;color:#03dac6;}</style>
</head><body>
<h1>太極語音接收器 8.0</h1>
<button id="micBtn" class="mic-btn" onclick="startDictation()">按住說話</button>
<div id="status">等待語音指令...</div><div id="ai-result"></div>
<script>
function startDictation() {
    var sr = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!sr) return alert("不支援語音");
    var r = new sr(); r.lang = "zh-TW";
    document.getElementById('micBtn').innerText = "聆聽中...";
    r.start();
    r.onresult = function(e) {
        var txt = e.results[0][0].transcript;
        document.getElementById('status').innerText = "您說了: " + txt;
        document.getElementById('ai-result').innerText = "大腦解析中...";
        fetch('/api/order', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:"神級語音",item:txt,table:"POS"})})
        .then(res=>res.json()).then(d=>{
            if(d.ai_intent) document.getElementById('ai-result').innerText = "解析完成! 品項: " + d.ai_intent.items + " | 備註: " + (d.ai_intent.remark||"無");
        });
    };
}
</script></body></html>'''

@app.post("/api/order")
def receive_http_order(order_data: dict):
    if order_data.get("action") == "神級語音":
        intent = ai_brain.process_text_intent(order_data.get("item", ""), order_data.get("table", "未知"))
        return {"status": "success", "ai_intent": intent}
    return {"status": "success"}

@app.post("/api/workspace/write")
async def receive_workspace_write(request: Request):
    try:
        payload = await request.json()
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "title": payload.get("title", "未授權脈衝"),
            "content": payload.get("content", "{}")
        }
        workspace_memory.insert(0, record)
        if len(workspace_memory) > 20:
            workspace_memory.pop()
        print(f"[Workspace HQ] Received tensor pulse: {record['timestamp']}")
        return {"status": "success", "message": "HQ Confirmed. Target Acquired."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/workspace", response_class=HTMLResponse)
async def workspace_dashboard():
    cards_html = ""
    for idx, item in enumerate(workspace_memory):
        content_str = str(item["content"])
        try:
            parsed = json.loads(content_str)
            content_str = json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            pass

        cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span><span class="pulse-dot"></span><strong>#{len(workspace_memory) - idx} | {html.escape(str(item["title"]))}</strong></span>
                <span class="time">{html.escape(item["timestamp"])}</span>
            </div>
            <pre>{html.escape(content_str)}</pre>
        </div>
        """

    if not cards_html:
        cards_html = "<div class='empty'>總部雷達守望中，等待 Sister J 拋轉資料...</div>"

    html_content = f"""
    <!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>五常總部戰情室 (Port: 8000)</title><meta http-equiv="refresh" content="2">
    <style>body {{ background-color: #020617; color: #e2e8f0; font-family: sans-serif; padding: 20px; }} .header {{ border-bottom: 2px solid #ef4444; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; gap: 16px; }} h1 {{ color: #ef4444; margin: 0; text-transform: uppercase; }} .status {{ background: #1e293b; padding: 5px 15px; border-radius: 20px; border: 1px solid #334155; font-size: 14px; color: #10b981; white-space: nowrap; }} .card {{ background: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #3b82f6; margin-bottom: 15px; border-radius: 4px; overflow: hidden; }} .card-header {{ background: #1e293b; padding: 10px 15px; display: flex; justify-content: space-between; gap: 12px; }} .pulse-dot {{ width: 10px; height: 10px; background-color: #3b82f6; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #3b82f6; }} .time {{ color: #94a3b8; font-family: monospace; font-size: 12px; white-space: nowrap; }} pre {{ margin: 0; padding: 15px; color: #a3e635; font-family: monospace; font-size: 14px; white-space: pre-wrap; }} .empty {{ text-align: center; color: #94a3b8; padding: 50px; font-size: 18px; border: 1px dashed #334155; border-radius: 8px; }}</style></head>
    <body><div class="header"><h1>實體總部戰情室 (Workspace HQ)</h1><div class="status">8000 埠監聽中</div></div><div id="radar-container">{cards_html}</div></body></html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run("taiji_hub:app", host="0.0.0.0", port=8000, reload=False)
