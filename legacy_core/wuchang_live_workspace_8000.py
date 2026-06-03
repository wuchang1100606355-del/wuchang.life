# -*- coding: utf-8 -*-
"""
🏢 戰略代號：五常大陣 - 實體總部戰情室 (Workspace Live Server)
"""
import uvicorn
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="Wuchang Live Workspace", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

database_memory = []

@app.post("/api/workspace/write")
async def receive_edge_tensor(request: Request):
    try:
        payload = await request.json()
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "title": payload.get("title", "未授權脈衝"),
            "content": payload.get("content", "{}")
        }
        database_memory.insert(0, record)
        if len(database_memory) > 20: database_memory.pop()
        print(f"📥 [總部接收] 收到來自邊緣節點的張量脈衝: {record['timestamp']}")
        return {"status": "success", "message": "HQ Confirmed. Target Acquired."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/", response_class=HTMLResponse)
async def hq_dashboard():
    cards_html = ""
    for idx, item in enumerate(database_memory):
        content_str = item['content']
        try:
            parsed = json.loads(content_str)
            content_str = json.dumps(parsed, indent=2, ensure_ascii=False)
        except: pass
        cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span class="pulse-dot"></span>
                <strong>#{len(database_memory) - idx} | {item['title']}</strong>
                <span class="time">{item['timestamp']}</span>
            </div>
            <pre>{content_str}</pre>
        </div>
        """
    if not cards_html: cards_html = "<div class='empty'>📡 總部雷達守望中，等待 Sister J (8789) 拋轉資料...</div>"
    html_content = f"""
    <!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>五常總部戰情室 (Port: 8000)</title><meta http-equiv="refresh" content="2">
    <style>body {{ background-color: #020617; color: #e2e8f0; font-family: sans-serif; padding: 20px; }} .header {{ border-bottom: 2px solid #ef4444; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }} h1 {{ color: #ef4444; margin: 0; text-transform: uppercase; }} .status {{ background: #1e293b; padding: 5px 15px; border-radius: 20px; border: 1px solid #334155; font-size: 14px; color: #10b981; }} .card {{ background: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #3b82f6; margin-bottom: 15px; border-radius: 4px; overflow: hidden; }} .card-header {{ background: #1e293b; padding: 10px 15px; display: flex; justify-content: space-between; }} .pulse-dot {{ width: 10px; height: 10px; background-color: #3b82f6; border-radius: 50%; display: inline-block; margin-right: 10px; box-shadow: 0 0 8px #3b82f6; }} .time {{ color: #64748b; font-family: monospace; font-size: 12px; }} pre {{ margin: 0; padding: 15px; color: #a3e635; font-family: monospace; font-size: 14px; white-space: pre-wrap; }} .empty {{ text-align: center; color: #475569; padding: 50px; font-size: 18px; border: 1px dashed #334155; border-radius: 8px; }}</style></head>
    <body><div class="header"><h1>🏢 實體總部戰情室 (Workspace HQ)</h1><div class="status">● 8000 埠監聽中</div></div><div id="radar-container">{cards_html}</div></body></html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    print("=" * 60 + "\n 🏢 [總部上線] 實體接收端 (Live Server) 已啟動！\n 👁️ 戰情面板: http://127.0.0.1:8000/\n" + "=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
