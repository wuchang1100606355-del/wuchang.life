# -*- coding: utf-8 -*-
"""
☯️ 五常太極大陣 - 雙腦協同路由器 (Dual-Brain Router) ☯️
==============================================================================
[造物主] 江政隆 (F124771717)
[本地大腦] Sister J (Ollama DeepSeek) - 守護地端主權，防範資料外洩
[雲端大腦] Gemini 3.1 (Google GenAI) - 提供超維度邏輯推演與盲算
==============================================================================
"""

import os
import json
import urllib.request
import urllib.error

# ==========================================
# ⚙️ 戰術設定區
# ==========================================
# Legacy router safety:
# This module is archive/legacy only. It must fail closed unless a local operator
# explicitly enables legacy cloud routing and provides a key through env vars.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ALLOW_LEGACY_CLOUD = os.environ.get("TAIJI_ALLOW_LEGACY_CLOUD", "").lower() == "true"

# 本地 Sister J (Ollama) 的通訊埠
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def ask_local_sister_j(prompt: str) -> str:
    """呼叫地端裝甲 (Sister J) 進行初步處理或脫敏"""
    print(f"🛡️ [地端 Sister J] 正在思考...")
    data = {
        "model": "Sister_J_DeepSeek", 
        "prompt": prompt,
        "stream": False
    }
    print(f"[即時訊息] 送出 payload: {json.dumps(data, ensure_ascii=False)}")
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read().decode('utf-8')
            print(f"[即時訊息] Sister J 回傳原始資料: {raw}")
            result = json.loads(raw)
            return result.get("response", "")
    except Exception as e:
        print(f"[即時訊息] Sister J 連線失敗，錯誤細節: {str(e)}")
        return f"Sister J 連線失敗，請確認 Ollama 正在運行。錯誤: {str(e)}"

def ask_cloud_gemini(prompt: str) -> str:
    """呼叫雲端大腦 (Gemini) 進行高維度推演"""
    if not ALLOW_LEGACY_CLOUD or not GEMINI_API_KEY:
        return "BLOCKED: legacy cloud router is disabled; use Taiji Gateway/Five Metric audited path."
    print(f"☁️ [雲端 Gemini 3.1] 正在進行高維度推演...")
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    print("[即時訊息] 送出 payload: redacted")
    req = urllib.request.Request(gemini_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read().decode('utf-8')
            result = json.loads(raw)
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"[即時訊息] Gemini API 拒絕連線，錯誤碼: {e.code}，細節: {e.read().decode('utf-8') if hasattr(e, 'read') else str(e)}")
        return f"Gemini API 拒絕連線 (請檢查 API Key 是否正確)。錯誤碼: {e.code}"
    except Exception as e:
        print(f"[即時訊息] Gemini 連線異常，錯誤細節: {str(e)}")
        return f"Gemini 連線異常: {str(e)}"

def execute_moa_consensus(user_input: str):
    """執行多腦共識機制"""
    print("\n" + "="*50)
    print(f"👤 總司令下達指令: {user_input}")
    print("="*50)
    
    # 階段 1：地端主權防禦
    local_response = ask_local_sister_j(f"總司令說了這句話：『{user_input}』。請以您的本地守護者人格，給出簡短的戰術建議或審查意見。")
    print(f"\n🔥 [Sister J 回報]:\n{local_response}\n")
    
    # 階段 2：雲端盲算推演
    cloud_response = ask_cloud_gemini(f"這是來自五常太極大陣的指令：『{user_input}』。請以雲端大腦 Jules 的身分，給出最詳盡的執行方案。")
    print(f"\n🌊 [Gemini 3.1 回報]:\n{cloud_response}\n")
    
    print("="*50)
    print("✅ 雙腦推演完畢！雲地神經網路貫通成功。")
    print("="*50 + "\n")

if __name__ == "__main__":
    print("☯️ 五常太極大陣 - 雙腦協同路由器啟動 ☯️")
    while True:
        try:
            cmd = input("\n請輸入指令 (或輸入 exit 退出) >>> ")
            if cmd.lower() in ['exit', 'quit']:
                break
            if cmd.strip():
                execute_moa_consensus(cmd)
        except KeyboardInterrupt:
            print("\n系統中斷，關閉神經連結。")
            break
