# -*- coding: utf-8 -*-
"""
☯️ 五常太極大陣 - 本地數據重組服務 (Local Reconstruction Service) ☯️
==============================================================================
[造物主] 江政隆 (F124771717)
[核心功能]
 1. 接收碎片化數據 (來自 llm_core.py 的分片與虛假流量處理)。
 2. 執行專利中的 TEE 隔離解碼與記憶體歸零邏輯。
 3. 提供 FastAPI 接口供本地其他服務調用。
==============================================================================
"""

import os
import sys
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from functools import reduce
import binascii
import gc # For memory zeroization

logging.basicConfig(level=logging.INFO, format='[本地重組服務] %(asctime)s - %(message)s')

app = FastAPI(title="Wuchang Local Reconstruction Service")

class ReconstructionRequest(BaseModel):
    parts: List[str]
    k: int = 2 # Default k value

# TEE 隔離與記憶體歸零（專利 V3 Claim 1,4,5） - 實作於此服務
def _tee_decode_logic(parts: List[str], k: int) -> Optional[str]:
    """
    執行碎片化數據的重組與記憶體歸零。
    這是從 llm_core.py 移過來的核心邏輯。
    """
    # XOR 合成（示意）
    if len(parts) < k:
        logging.warning(f"重組失敗: 碎片數量 {len(parts)} 少於門檻 {k}")
        return None
    
    try:
        bparts = [binascii.unhexlify(p) for p in parts[:k]]
        # 確保所有碎片長度一致，避免 zip 錯誤
        if not all(len(p) == len(bparts[0]) for p in bparts):
            logging.error("重組失敗: 碎片長度不一致。")
            return None

        res = reduce(lambda x, y: bytes([a ^ b for a, b in zip(x, y)]), bparts)
        
        # 記憶體歸零（示意）
        for i in range(len(bparts)):
            bparts[i] = b"\x00" * len(bparts[i]) # 覆寫記憶體
        del bparts # 刪除變數引用
        gc.collect() # 強制垃圾回收

        return res.decode(errors="ignore")
    except binascii.Error as e:
        logging.error(f"重組失敗: 無法解碼十六進制碎片 - {e}")
        return None
    except Exception as e:
        logging.error(f"重組失敗: 未知錯誤 - {e}")
        return None

@app.post("/reconstruct")
async def reconstruct_data(request: ReconstructionRequest):
    try:
        decoded_text = _tee_decode_logic(request.parts, request.k)
        if decoded_text is None:
            raise HTTPException(status_code=400, detail="重組失敗，可能碎片不足或數據損壞。")
        
        logging.info(f"✅ 成功重組數據，長度: {len(decoded_text)} 字元。")
        return {"decoded_text": decoded_text}
    except HTTPException:
        raise # Re-raise HTTPExceptions
    except Exception as e:
        logging.error(f"❌ 重組過程中發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"重組失敗: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 啟動本地重組服務於 http://127.0.0.1:11436")
    uvicorn.run(app, host="127.0.0.1", port=11436, log_level="warning")