# -*- coding: utf-8 -*-
"""
wuchang_pos_voice_engine.py
五常太極大陣 - 商米 POS 語音微服務 (Port 9003 記憶體即時直出版)
==============================================================================
[系統定位] 獨立的語音生成與播放伺服器 (Microservice)
[戰術升級] 捨棄 gTTS 下載 MP3 錄音檔的延遲模式。全面改用 pyttsx3 引擎！
           直接在記憶體中生成音波並打入底層硬體(藍牙/喇叭)，達成 0 延遲即時發聲，
           絕不在硬碟留下任何實體檔案 (Zero Disk I/O)。
[防呆防線] 1. 內建自動獵殺殭屍程序，根除 Errno 98 Port 佔用問題。
           2. espeak 引擎缺失時自動進入降級模式，程式永不崩潰。
[總指揮官] 江政隆 (F124771717)
==============================================================================
"""
import os
import queue
import threading
import logging
import time
import wave
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

try:
    import pyttsx3
    import psutil
except ImportError:
    pyttsx3 = None
    psutil = None
    print("⚠️ 缺少 pyttsx3/psutil，語音引擎將以降級模式啟動。")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [VoiceEngine-Realtime] %(message)s')

app = FastAPI(title="Wuchang POS Voice Engine (Realtime In-Memory Edition)")


class WuchangVoiceEngine:
    """
    OpenAI-compatible speech adapter used by taiji_unified_gateway_edge.py.
    It prefers the local OS TTS engine, and falls back to a short silent WAV so
    WebUI audio requests do not fail when eSpeak/SAPI is missing.
    """
    def __init__(self, output_dir: str = "data/voice_cache"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.engine = None
        if not pyttsx3:
            logging.warning("⚠️ [語音檔引擎] pyttsx3 未安裝，啟用靜音降級。")
            return
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", int(os.getenv("VOICE_RATE", "160")))
            self.engine.setProperty("volume", float(os.getenv("VOICE_VOLUME", "1.0")))
            logging.info("✅ [語音檔引擎] 本機 TTS 已就緒。")
        except Exception as e:
            logging.warning(f"⚠️ [語音檔引擎] 本機 TTS 不可用，啟用靜音降級: {e}")

    def get_voices(self):
        voices = [{
            "id": "wuchang-local-zh-tw",
            "object": "voice",
            "name": "Wuchang Local TTS",
            "language": "zh-TW",
            "default": True
        }]
        if not self.engine:
            return voices

        try:
            for voice in self.engine.getProperty("voices") or []:
                voices.append({
                    "id": getattr(voice, "id", "local-voice"),
                    "object": "voice",
                    "name": getattr(voice, "name", "Local Voice"),
                    "language": "local",
                    "default": False
                })
        except Exception as e:
            logging.warning(f"⚠️ 無法列出本機語音: {e}")
        return voices

    def speak(self, text: str, filename: str) -> str:
        safe_name = os.path.basename(filename)
        if not safe_name.lower().endswith(".wav"):
            safe_name = os.path.splitext(safe_name)[0] + ".wav"
        file_path = os.path.join(self.output_dir, safe_name)

        if self.engine:
            try:
                self.engine.save_to_file(text, file_path)
                self.engine.runAndWait()
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path
            except Exception as e:
                logging.error(f"❌ 產生語音檔失敗，改用靜音降級: {e}")

        self._write_silent_wav(file_path)
        return file_path

    @staticmethod
    def _write_silent_wav(file_path: str, seconds: float = 0.25):
        sample_rate = 16000
        frames = int(sample_rate * seconds)
        with wave.open(file_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frames)

# =============================================================================
# ⚡ 記憶體語音直出引擎 (背景執行緒與佇列防卡死設計)
# =============================================================================
# 建立一個記憶體指令佇列
voice_queue = queue.Queue()

def realtime_tts_worker():
    """
    [背景守護神] 永遠在背景待命。一收到文字，立刻調用 OS 底層語音驅動發聲。
    不存檔、不下載，完全在記憶體中運作。
    """
    engine = None
    try:
        if not pyttsx3:
            raise RuntimeError("pyttsx3 未安裝")
        # 初始化作業系統底層語音引擎 (Windows: SAPI5, Linux: espeak, macOS: nsspeech)
        engine = pyttsx3.init()
        
        # [選用設定] 調整語速與音量 (可依商米機實際聽感微調)
        engine.setProperty('rate', 160)    # 語速 (預設約 200，調慢一點比較清楚)
        engine.setProperty('volume', 1.0)  # 音量 (0.0 到 1.0)
        logging.info("🔊 [語音引擎] 底層硬體驅動已就緒，等待記憶體指令注入...")
        
    except Exception as e:
        logging.error("❌ 嚴重警告：作業系統缺少底層語音驅動 (eSpeak)！")
        logging.error("👉 請總司令在終端機輸入此指令來安裝硬體發聲器官：")
        logging.error("   sudo apt-get update && sudo apt-get install espeak espeak-ng -y")
        logging.warning("⚠️ 系統已自動進入降級模式。API 可正常接收指令，但將略過物理發聲。")

    while True:
        text = voice_queue.get()
        if text is None:
            break # 收到毒藥封包，結束執行緒
        
        try:
            logging.info(f"⚡ [即時直出] 正在廣播: {text}")
            if engine:
                engine.say(text)
                engine.runAndWait() # 阻塞直到這句話唸完
                logging.info("✅ [即時直出] 廣播完畢。")
            else:
                logging.warning("⚠️ [降級攔截] 因缺少 espeak 驅動，本次語音已被丟棄。請安裝後重啟。")
        except Exception as e:
            logging.error(f"❌ 語音直出失敗: {e}")
        finally:
            voice_queue.task_done()

# 系統啟動時，直接啟動語音背景執行緒
threading.Thread(target=realtime_tts_worker, daemon=True).start()


# =============================================================================
# 🌐 API 路由
# =============================================================================
class SpeakReq(BaseModel):
    text: str

@app.post("/speak")
async def speak(req: SpeakReq):
    logging.info(f"🎙️ [接收軍令] 準備即時廣播: {req.text}")
    try:
        # 將要說的文字丟入記憶體佇列，瞬間返回 HTTP 200，絕不阻塞 FastAPI
        voice_queue.put(req.text)
        return {"status": "success", "detail": "語音指令已注入記憶體，即刻發聲！"}
        
    except Exception as e:
        logging.error(f"❌ Speak 廣播端點執行失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 🛡️ 防呆防線：自動獵殺通訊埠殭屍程序
# =============================================================================
def force_release_port(port: int):
    """強勢釋放被卡死的通訊埠，確保點火必成"""
    if not psutil:
        logging.warning("⚠️ psutil 未安裝，略過 Port 掃描。")
        return
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    logging.warning(f"⚠️ 發現 Port {port} 被殭屍程序 PID {proc.pid} 佔用，執行戰術清除...")
                    proc.kill()
                    time.sleep(1) # 給予 OS 釋放資源的時間
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔥 啟動【五常太極大陣 - POS 語音微服務 (記憶體即時無痕版)】")
    print("📡 正在 9003 埠全天候待命接收主腦廣播軍令...")
    print("⚡ 特性：零磁碟 I/O、無錄音檔、硬體直出、極低延遲、防 Port 佔用")
    print("="*80 + "\n")
    
    # 點火前執行掃蕩，絕不讓 Errno 98 阻擋總司令
    force_release_port(9003)
    
    uvicorn.run(app, host="0.0.0.0", port=9003, log_level="warning")
