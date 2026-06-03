# -*- coding: utf-8 -*-
"""
👑 五常太極大陣 V10.0 - 主戰艦大腦戰情網關 👑
(太極陰陽解耦版：主戰艦負責指揮，邊緣老機負責實體商店運作)
"""
import os
import json
import time
import fastapi
import uvicorn
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from google.oauth2.service_account import Credentials

app = fastapi.FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

KEY_PATH = 'my-j-483304-23978329de4c.json'

class WorkspaceData(BaseModel):
    kind: str
    title: str
    content: str
    meta: dict = {}

class AvatarMsg(BaseModel):
    message: str
    node: str

class OdooSyncData(BaseModel):
    node_id: str
    transaction_count: int
    total_amount: float
    sync_payload: list

latest_avatar_state = {"message": "總司令，Sister J 待命中...", "node": "System", "timestamp": time.time(), "speaking": False}

@app.get("/")
async def serve_ui():
    with open("wuchang_control_center.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

active_connections: list[WebSocket] = []

async def broadcast_message(message: str):
    for connection in list(active_connections):
        try:
            await connection.send_text(message)
        except WebSocketDisconnect:
            if connection in active_connections:
                active_connections.remove(connection)
        except Exception as e:
            print(f"Error broadcasting message: {e}")
            if connection in active_connections:
                active_connections.remove(connection)

@app.websocket("/ws/live_updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received WebSocket message from client: {data}")
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.post('/api/workspace/write')
async def write_to_workspace(data: WorkspaceData):
    if not os.path.exists(KEY_PATH):
        return {'ok': False, 'error': f'找不到 GCP 金鑰：{KEY_PATH}'}
    try:
        creds = Credentials.from_service_account_file(KEY_PATH, scopes=['https://www.googleapis.com/auth/drive.file'])
        response_msg = {'ok': True, 'msg': f'Sister J 已成功透過 GCP 憑證認證！準備寫入: {data.title}'}
        await broadcast_message(json.dumps({"type": "workspace_write", "data": data.model_dump(), "response": response_msg}))
        return response_msg
    except Exception as e:
        response_msg = {'ok': False, 'error': f'憑證驗證失敗: {str(e)}'}
        await broadcast_message(json.dumps({"type": "workspace_write_error", "data": data.model_dump(), "response": response_msg}))
        return response_msg

@app.post("/api/odoo/edge_sync")
async def receive_edge_odoo_sync(data: OdooSyncData):
    sync_msg = f"🔄 收到來自 {data.node_id} 的 Odoo 商店同步！共 {data.transaction_count} 筆訂單，總額 ${data.total_amount}"
    print(sync_msg)
    response_msg = {'ok': True, 'msg': sync_msg}
    await broadcast_message(json.dumps({"type": "odoo_edge_sync", "data": data.model_dump(), "response": response_msg}))
    return response_msg
    except Exception as e:
        response_msg = {'ok': False, 'error': f'憑證驗證失敗: {str(e)}'}
        await broadcast_message(json.dumps({"type": "workspace_write_error", "data": data.dict(), "response": response_msg}))
        return response_msg

@app.post("/api/odoo/edge_sync")
async def receive_edge_odoo_sync(data: OdooSyncData):
    sync_msg = f"🔄 收到來自 {data.node_id} 的 Odoo 商店同步！共 {data.transaction_count} 筆訂單，總額 ${data.total_amount}"
    print(sync_msg)
    response_msg = {'ok': True, 'msg': sync_msg}
    await broadcast_message(json.dumps({"type": "odoo_edge_sync", "data": data.dict(), "response": response_msg}))
    return response_msg

@app.get("/api/map/sync")
def sync_map():
    return {
        "ok": True,
        "updates": {
            "dev_local": {"status": "ok", "metrics": {"cpu": "正常運作", "ram": "穩定", "role": "大腦主戰艦 (MSI)"}},
            "domain_backend": {"status": "ok", "metrics": {"odoo": "邊緣獨立商店 (.249)", "state": "自主營運中 (Autonomous)"}},
            "dev_router": {"status": "ok", "metrics": {"wan": "連線中", "ip": "220.135.21.74"}},
            "org_association": {"status": "ok", "metrics": {"state": "治理正常"}},
            "zero_trust": {"status": "ok", "metrics": {"tunnel": "headscale/cloudflared 待命中"}}
        }
    }

@app.post("/api/avatar/speak")
async def trigger_avatar_speech(data: AvatarMsg):
    global latest_avatar_state
    latest_avatar_state.update({
        "message": data.message, "node": data.node, "timestamp": time.time(), "speaking": True
    })
    response_msg = {"ok": True}
    await broadcast_message(json.dumps({"type": "avatar_speak", "data": data.model_dump(), "response": response_msg}))
    return response_msg

@app.get("/api/avatar/status")
def get_avatar_status():
    if time.time() - latest_avatar_state["timestamp"] > 6:
        latest_avatar_state["speaking"] = False
    return latest_avatar_state

if __name__ == '__main__':
    print('\n' + '='*60)
    print('👑 [五常系統 V10.0] 活體戰情網關已啟動！')
    print('🛡️ 執行檔案: taiji_v10_gateway.py')
    print('👉 請打開瀏覽器進入：http://127.0.0.1:8788')
    print('='*60 + '\n')
    uvicorn.run(app, host='0.0.0.0', port=8788, log_level='warning')