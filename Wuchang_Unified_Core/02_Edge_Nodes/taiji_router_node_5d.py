#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 五常太極大陣 - 微小J 5D 邊緣閘道器 (Async 5D Gateway)
# 落實白皮書架構：uvloop 解耦、GC 節奏凍結、清潔緒脈衝

import asyncio
import uvloop
import gc
import json
import logging
import re
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from concurrent.futures import ProcessPoolExecutor

# 強制將 asyncio 的事件迴圈替換為極速的 C 語言 libuv 引擎
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

PORT = 9005
logging.basicConfig(level=logging.INFO, format='%(asctime)s [5D 閘道器] %(message)s')

app = FastAPI(title="Wuchang 5D Taiji Gateway")

# 建立獨立的行程池 (Process Pool)，落實白皮書 6.3「執行緒解耦」，徹底避開 GIL 爭奪
compute_pool = ProcessPoolExecutor(max_workers=2)

# ---------------------------------------------------------
# 白皮書第 7.3 章：物件凍結與垃圾回收 (GC) 調優
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logging.info("⚙️ 執行系統初始化與物件凍結 (GC Freezing)...")
    # 清理所有現有殘留
    gc.collect(2)
    # 將啟動時載入的所有框架與常駐變數移出 GC 監控清單，視為永久存活
    gc.freeze()
    # 人為提高 GC 觸發閾值，減少系統在 AI 運算時的延遲抖動 (Jitter)
    gc.set_threshold(50000, 1000, 1000)
    logging.info("✅ 記憶體凍結完畢。清潔緒脈衝環境已建立。")

def cpu_bound_slimming_task(raw_text: str) -> str:
    """【重度運算】在獨立 Process 中執行的減肥引擎，絕對不阻擋事件迴圈"""
    if raw_text == "EMPTY_PAYLOAD": return raw_text
    text = re.sub(r'\s+', ' ', raw_text)
    stop_words = ['請幫我', '你能', '謝謝', '麻煩你', '請問一下', '我想知道', '可以幫我', '幫我', '請問']
    for w in stop_words: text = text.replace(w, '')
    return text.strip()

@app.post("/")
async def gateway_intercept(request: Request):
    """5D 閘道器接收端 (Async)"""
    client_ip = request.client.host
    logging.warning(f"🛡️ 警報！城門遭受敲擊！來源維度: {client_ip}")
    
    body_bytes = await request.body()
    raw_payload = body_bytes.decode('utf-8') if body_bytes else "EMPTY_PAYLOAD"
    original_len = len(raw_payload)

    # ---------------------------------------------------------
    # 白皮書第 6.3 章：建構清潔緒脈衝 (await asyncio.sleep(0))
    # ---------------------------------------------------------
    # 主動釋放控制權，讓 uvloop 先去處理累積的底層 TCP 網路封包
    await asyncio.sleep(0)

    # 將耗時的字串比對/正規表示式運算，丟入 Process Pool，徹底避開 GIL 阻塞
    loop = asyncio.get_running_loop()
    slimmed_payload = await loop.run_in_executor(compute_pool, cpu_bound_slimming_task, raw_payload)
    
    slimmed_len = len(slimmed_payload)
    saved_ratio = ((original_len - slimmed_len) / original_len * 100) if original_len > 0 else 0

    logging.warning(f"✂️ [急攤縮減肥] 原始: {original_len} -> 壓縮後: {slimmed_len} (省算力 {saved_ratio:.1f}%)")

    # 再次釋放脈衝，維持動態平衡
    await asyncio.sleep(0)

    response_data = {
        "status": "5D_SUPERPOSITION_COLLAPSED",
        "node": "mu_2 (5D Async Gateway)",
        "commander": "F124771717",
        "message": f"封包已穿越非同步流形！替總司令節省算力 {saved_ratio:.1f}%",
        "slimmed_payload": slimmed_payload
    }
    
    # 節奏性主動回收 (如果空閒的話，在此處觸發輕量回收)
    if saved_ratio > 0: gc.collect(0)

    return JSONResponse(content=response_data, headers={"Access-Control-Allow-Origin": "*"})

@app.get("/")
async def health_check():
    return JSONResponse(content={"status": "ALIVE", "message": "5D 非同步城門運作正常。"})

if __name__ == "__main__":
    import uvicorn
    # 強制關閉 Uvicorn 的 access_log 以避免無謂的 I/O 中斷，實現極致效能
    uvicorn.run("taiji_router_node_5d:app", host="0.0.0.0", port=PORT, loop="uvloop", access_log=False)
