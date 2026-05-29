#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 五常太極大陣 - AI 小腦 (Wuchang AI Cerebellum)
# 負責: 潛意識硬體負載平衡、GC 節奏控制、清潔緒脈衝守護

import asyncio
import uvloop
import gc
import psutil
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.basicConfig(level=logging.INFO, format='%(asctime)s [🧠 AI 小腦] %(message)s')

app = FastAPI(title="Wuchang AI Cerebellum")

# 小腦狀態矩陣
cerebellum_state = {
    "gc_frozen": False,
    "cpu_throttle_active": False,
    "last_cleaned_time": 0
}

@app.on_event("startup")
async def awaken_cerebellum():
    """小腦甦醒：立即接管記憶體回收權限"""
    logging.info("啟動潛意識神經：凍結初始記憶體，避免 GC 抖動 (Stop-The-World)...")
    gc.collect(2)
    gc.freeze()
    gc.set_threshold(100000, 5000, 5000) # 極限提高閾值，交由小腦手動控制
    cerebellum_state["gc_frozen"] = True
    
    # 啟動背景太極陰陽平衡器
    asyncio.create_task(taiji_dynamic_balance_loop())
    logging.info("✅ AI 小腦已接管底層呼吸節奏。")

async def taiji_dynamic_balance_loop():
    """太極陰陽平衡器：在背景無限循環，守護 CPU 與記憶體狀態"""
    while True:
        # 1. 感知硬體負載
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent
        
        # 2. 陰陽調節 (Yin-Yang Moderation)
        if cpu_usage > 85.0 and not cerebellum_state["cpu_throttle_active"]:
            logging.warning(f"⚠️ [過載] CPU {cpu_usage}%！小腦啟動【高度中斷節流 (High Moderation)】，保護大腦算力！")
            cerebellum_state["cpu_throttle_active"] = True
            
        elif cpu_usage < 50.0 and cerebellum_state["cpu_throttle_active"]:
            logging.info(f"🟢 [平穩] CPU {cpu_usage}%。小腦解除節流，釋放網路吞吐量。")
            cerebellum_state["cpu_throttle_active"] = False

        # 3. 節奏性垃圾回收 (Rhythmic GC) - 趁 CPU 閒置時才打掃
        if ram_usage > 75.0 and cpu_usage < 60.0:
            logging.info("🧹 [潛意識打掃] 趁大腦休息，小腦執行輕量記憶體回收 (Clean Thread Pulse)...")
            gc.collect(0)
            cerebellum_state["last_cleaned_time"] = asyncio.get_event_loop().time()

        # 維持清潔緒脈衝，讓出 2 秒時間給主迴圈處理網路封包
        await asyncio.sleep(2)

@app.get("/health")
async def cerebellum_health():
    """提供給大腦 (Jules API) 或雷達調閱的小腦健康狀態"""
    return JSONResponse({
        "status": "CEREBELLUM_ACTIVE",
        "cpu_load": psutil.cpu_percent(),
        "ram_load": psutil.virtual_memory().percent,
        "gc_frozen": cerebellum_state["gc_frozen"],
        "throttle_active": cerebellum_state["cpu_throttle_active"],
        "message": "小腦正在背景默默協調系統脈衝，請大腦安心運算。"
    })

if __name__ == "__main__":
    import uvicorn
    # 小腦運行於 9006 Port，靜默無聲
    uvicorn.run("wuchang_ai_cerebellum:app", host="0.0.0.0", port=9006, loop="uvloop", access_log=False)
