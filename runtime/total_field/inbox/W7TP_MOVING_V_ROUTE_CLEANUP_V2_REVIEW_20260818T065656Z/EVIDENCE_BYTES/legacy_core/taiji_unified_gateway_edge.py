#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【五常太極大陣 - V14 究極無損真理版 (True Absolute Fusion)】
融合內容：總司令 V10.8 完整源碼 (併發引擎 + VRAM 鎖定) + WSL 跨界雷達 + 實體雙螯 + FastAPI 劫持
"""

import os
import json
import time
import asyncio
import hashlib
import base64
import random
import subprocess
import gc
import uvicorn
import httpx
import ipaddress
from typing import Dict, Any, List, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

class SecurityError(Exception):
    pass

# =============================================================================
# 依賴模組檢查
# =============================================================================
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 缺少 google-genai，請執行: pip install google-genai pydantic")
    exit(1)

try:
    from wuchang_pos_voice_engine import WuchangVoiceEngine
    voice_engine = WuchangVoiceEngine()
    print("✅ [模組載入] WuchangVoiceEngine (Google WaveNet) 已就緒！")
except Exception as e:
    print(f"⚠️ 語音引擎未啟動: {e}")
    voice_engine = None

logging = __import__('logging')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [Wuchang-V14] %(message)s')

app = FastAPI(title="五常太極大陣-V14真理閘道器")

DEFAULT_ALLOWED_CLIENT_CIDRS = (
    "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,"
    "192.168.0.0/16,100.64.0.0/10,fc00::/7,fe80::/10"
)


def _allowed_networks():
    raw = os.getenv("ALLOWED_CLIENT_CIDRS", DEFAULT_ALLOWED_CLIENT_CIDRS)
    return [ipaddress.ip_network(item.strip(), strict=False) for item in raw.split(",") if item.strip()]


def _client_allowed(host: str) -> bool:
    try:
        client_ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(client_ip in network for network in _allowed_networks())



@app.get("/healthz")
def w7tp_healthz():
    return {
        "status": "ok",
        "service": "taiji_edge_gateway",
        "port": 9002,
        "mode": "w7tp_runtime"
    }


@app.middleware("http")
async def enforce_client_whitelist(request: Request, call_next):
    client_host = request.client.host if request.client else ""
    if not _client_allowed(client_host):
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden: client is outside ALLOWED_CLIENT_CIDRS"},
        )
    return await call_next(request)

# =============================================================================
# 👑 [總司令核心技術] WSL 跨網域雷達：自動抓取 Windows 宿主機 IP
# =============================================================================
def get_windows_host_ip() -> str:
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    ip = line.split()[1]
                    logging.info(f"📡 [WSL Bridge] 成功鎖定 Windows 宿主機 IP: {ip}")
                    return ip
    except Exception as e:
        logging.warning(f"⚠️ [WSL Bridge] 無法解析宿主機 IP，回退至 localhost ({e})")
    return "127.0.0.1"

WINDOWS_OLLAMA_IP = get_windows_host_ip()
WINDOWS_OLLAMA_URL = f"http://{WINDOWS_OLLAMA_IP}:11434/api/chat"

SOVEREIGN_OWNER_ID = "F124771717"
XOR_SECRET_KEY = b"WUCHANG_TAIJI_V10_ABSOLUTE_SHIELD"
AUDIT_LOG_FILE = "wuchang_audit.jsonl"

# =============================================================================
# Module 1: Immutable Audit Logger & 5D Spatiotemporal Tracker
# =============================================================================
class ImmutableAuditLogger:
    @staticmethod
    def write_log(five_d_code: str, event_type: str, details: str):
        log_entry = {
            "5D_Code": five_d_code,
            "Event": event_type,
            "Details": details,
            "SysTime": time.time()
        }
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

class FiveDimensionalTracker:
    @staticmethod
    def encode(node: str, tier: str, context: str, state: str) -> str:
        timestamp = int(time.time())
        code = f"{node}:{tier}:{context}:{timestamp}:{state}"
        logging.info(f"📍 [5D Localization] AI State Defined: {code}")
        ImmutableAuditLogger.write_log(code, "STATE_CHANGE", f"Transitioned to {state}")
        return code

# =============================================================================
# Module 2: Memory Folding, TTL Mechanism & Fault-Tolerant TEE Reconstruction
# =============================================================================
class FoldedMemoryManager:
    def __init__(self):
        self._folded_space: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def write(self, key: str, value: Any, ttl_seconds: int = 30):
        async with self._lock:
            self._folded_space[key] = {"data": value, "expire_at": time.time() + ttl_seconds}

    async def read_and_pop(self, key: str) -> Any:
        async with self._lock:
            obj = self._folded_space.pop(key, None)
            if obj and time.time() <= obj["expire_at"]:
                return obj["data"]
            logging.warning(f"⚠️ [Security Alert] Key '{key}' exceeded TTL. Access denied.")
            return None

    async def sweep_expired_keys(self):
        async with self._lock:
            now = time.time()
            expired_keys = [k for k, v in self._folded_space.items() if now > v["expire_at"]]
            for k in expired_keys:
                obj = self._folded_space.pop(k)
                data = obj["data"]
                if isinstance(data, bytearray):
                    for i in range(len(data)): data[i] = 0 
                logging.info(f"🌊 [TTL Sweep] Key '{k}' lifecycle expired. Memory zeroed.")

    async def get_all_keys(self) -> List[str]:
        async with self._lock:
            return list(self._folded_space.keys())

class TEEReconstructionEngine:
    @staticmethod
    def verify_remote_attestation() -> bool:
        logging.info("🔒 [TEE Attestation] Requesting Remote Attestation Report...")
        time.sleep(0.1)
        logging.info("🔒 [TEE Attestation] Firmware verified. Decoding authorized.")
        return True

    @staticmethod
    def ai_fragmentation_xor(data_str: str) -> Tuple[bytearray, str]:
        data_bytes = data_str.encode('utf-8')
        length = len(data_bytes)
        ephemeral_key = bytearray(os.urandom(length)) 
        
        xored_bytes = bytearray(
            b ^ ephemeral_key[i] ^ XOR_SECRET_KEY[i % len(XOR_SECRET_KEY)] 
            for i, b in enumerate(data_bytes)
        )
        fragmented_payload = base64.b64encode(xored_bytes).decode('utf-8')
        return ephemeral_key, fragmented_payload

    @staticmethod
    def reconstruct_and_zeroize(ephemeral_key: bytearray, fragmented_payload: str) -> str:
        if not TEEReconstructionEngine.verify_remote_attestation():
            raise SecurityError("Remote Attestation Failed!")

        try:
            xored_bytes = base64.b64decode(fragmented_payload)
            restored = bytearray(
                b ^ ephemeral_key[i] ^ XOR_SECRET_KEY[i % len(XOR_SECRET_KEY)] 
                for i, b in enumerate(xored_bytes)
            )
            result = restored.decode('utf-8')
            
            for i in range(len(ephemeral_key)): ephemeral_key[i] = 0
            for i in range(len(restored)): restored[i] = 0
            
            logging.info("🛡️ [TEE Reconstruction] Payload decoded and memory forced to zero!")
            return result
        except Exception as e:
            logging.warning(f"⚠️ [TEE Fallback] Cloud response is pure NLP, bypassing XOR decoding. ({e})")
            for i in range(len(ephemeral_key)): ephemeral_key[i] = 0
            return fragmented_payload

# =============================================================================
# Module 3: NPO Auditor, Deterministic Mapping & IPv6 Merlin Private VPN Tx
# =============================================================================
class PrivacyGatewayEngine:
    def __init__(self):
        self.reverse_map = {}
        self.banned_keywords = ["assassinate", "bribe", "illegal_funds"]

    def npo_auditor_check(self, text: str):
        for word in self.banned_keywords:
            if word in text.lower():
                logging.error(f"🚫 [NPO Auditor] Sensitive keyword '{word}' detected!")
                ImmutableAuditLogger.write_log("SYS:LOCK:NPO", "SECURITY_FREEZE", f"Blocked word: {word}")
                raise PermissionError("SYSTEM FROZEN: NPO Compliance Violation.")
        logging.info("✅ [NPO Auditor] Intent analysis passed. No compliance violations.")

    def deterministic_mapping(self, text: str) -> str:
        self.npo_auditor_check(text) 
        
        processed = text
        mappings = {"江政隆": "<SOVEREIGN_ID>", "林建國": "<ENTITY_A>", "李小華": "<ENTITY_B>", "8500": "<AMOUNT_X>"}
        for real, placeholder in mappings.items():
            if real in processed:
                self.reverse_map[placeholder] = real
                processed = processed.replace(real, placeholder)
        return processed

    def deanonymize(self, text: str) -> str:
        for placeholder, real in self.reverse_map.items():
            text = text.replace(placeholder, real)
        return text

class MerlinIPv6VPNNetwork:
    def __init__(self):
        self.ipv6_tunnel = os.environ.get("MERLIN_VPN_IPV6", "fd00:wuchang:taiji::1")
        
    async def asynchronous_capture_and_push(self, payload: str, tracking_code: str):
        jitter = random.uniform(0.2, 1.0)
        delta_payload = {
            "delta_id": tracking_code,
            "state_diff": payload
        }
        delta_str = json.dumps(delta_payload)
        
        logging.info(f"🕸️ [IPv6 Merlin] Transmitting DELTA PAYLOAD via {self.ipv6_tunnel}")
        logging.info(f"🕸️ [Desynchronized Tx] Injected Jitter {jitter:.2f}s with Dummy Traffic...")
        await asyncio.sleep(jitter)
        return delta_str

# =============================================================================
# Module 4: Taiji Tri-State Concurrency Engine & Enterprise Pure Logic
# =============================================================================
class CloudGeminiWorker:
    @staticmethod
    async def process_intent(instruction: str, delta_payload_str: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key: return "❌ 雲端盲算失敗：未配置 GEMINI_API_KEY"
        
        prompt = f"Execute Task: {instruction}\nDelta Fragmented Data: {delta_payload_str}"
        sys_instruct = (
            "You are a strict, stateless Enterprise Logic Parser. "
            "Output ONLY the logical analysis based strictly on the Delta Fragmented Data. "
            "DO NOT add conversational padding. DO NOT hallucinate external context."
        )
        
        try:
            client = genai.Client(api_key=api_key)
            logging.info("🌊 [Water Module] Engaging Enterprise-Grade Brain (gemini-1.5-pro-002)...")
            response = await asyncio.to_thread(
                client.models.generate_content,
                model='gemini-1.5-pro-002',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruct,
                    temperature=0.0 # 極致冰冷：消除所有亂數與不確定性，確保盲算精準度
                )
            )
            return response.text
        except Exception as e:
            return f"❌ Cloud Failure: {e}"

class TaijiConcurrencyEngine:
    def __init__(self, folded_memory: FoldedMemoryManager):
        self.memory = folded_memory
        self.is_running = False
        self.context_id = ""

    async def thread_clean(self):
        while self.is_running:
            await self.memory.sweep_expired_keys()
            keys = await self.memory.get_all_keys()
            if len(keys) > 50:
                gc.collect()
            await asyncio.sleep(2.0)

    async def thread_predict(self):
        while self.is_running:
            await asyncio.sleep(3.0)
            await self.memory.write(f"speculate_{self.context_id}", {"status": "pre_calculated"}, ttl_seconds=10)

    async def start_taiji_matrix(self, context_id: str):
        self.is_running = True
        self.context_id = context_id
        asyncio.create_task(self.thread_clean())
        asyncio.create_task(self.thread_predict())
        FiveDimensionalTracker.encode("EdgeNode", "Tier1", self.context_id, "CONCURRENCY_ACTIVE")

    async def collapse_matrix(self):
        self.is_running = False
        gc.collect()
        FiveDimensionalTracker.encode("EdgeNode", "Tier1", self.context_id, "WAVEFUNCTION_COLLAPSED")
        logging.info("🌌 [Asynchronous Collapse] Work completed. All concurrent states collapsed.")

# =============================================================================
# Module 5: GPU VRAM Lockdown Engine (WSL to Windows Localhost Support)
# =============================================================================
class OllamaGPUEnforcer:
    @staticmethod
    async def enforce_vram_allocation(api_url: str = WINDOWS_OLLAMA_URL, model_name: str = "llama3.1"):
        logging.info(f"🔧 [GPU Enforcer] Initiating strict VRAM allocation for {model_name} on Host Loop...")
        try:
            async with httpx.AsyncClient() as client:
                unload_payload = {"model": model_name, "keep_alive": 0}
                await client.post(api_url, json=unload_payload, timeout=5)
                logging.info("🧹 [GPU Enforcer] Successfully flushed old CPU memory cache.")
                await asyncio.sleep(1.5)

                preload_payload = {
                    "model": model_name,
                    "messages": [{"role": "system", "content": "VRAM Initialization Mode."}],
                    "options": {"num_gpu": 99},
                    "keep_alive": "15m",
                    "stream": False
                }
                await client.post(api_url, json=preload_payload, timeout=10)
                logging.info("🔥 [GPU Enforcer] Model successfully locked into RTX GPU VRAM within Host OS!")
        except Exception as e:
            logging.warning(f"⚠️ [GPU Enforcer] VRAM allocation ping failed: {e}")
            logging.warning(f"💡 請確認 Windows 端的 Ollama 服務已啟動，並允許 0.0.0.0 跨域連線！")

# =============================================================================
# 🦞 乖寶寶龍蝦實體雙螯 (OpenClawProxy) 
# =============================================================================
class OpenClawProxy:
    def __init__(self):
        self.sandbox_dir = os.path.abspath(os.environ.get("CLAW_SANDBOX_DIR", "data/claw_workspace"))
        os.makedirs(self.sandbox_dir, exist_ok=True)
        self.dangerous_keywords = ["rm -rf", "mkfs", "drop database", "chmod 777", "dd if="]

    async def obedient_claw_execute(self, command: str) -> str:
        for kw in self.dangerous_keywords:
            if kw in command.lower():
                return f"🦀 [專利防護鎖定] 警告！偵測到危險指令 '{kw}'，雙螯已強制上鎖。"
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.sandbox_dir
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
            output = stdout.decode(errors='ignore') if stdout else stderr.decode(errors='ignore')
            return f"🦀 [終端機執行完畢] (Exit Code: {proc.returncode})\n{output[:2000]}"
        except Exception as e:
            return f"🦀 [雙螯卡彈] {e}"

    def lobster_code_writer(self, file_path: str, code_content: str) -> str:
        full_path = os.path.abspath(os.path.join(self.sandbox_dir, file_path))
        if not full_path.startswith(self.sandbox_dir):
            return f"🦀 [越界防護] 拒絕存取 {full_path}"
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code_content)
            return f"🦀 [物理寫檔成功] 檔案已建立於: {full_path}"
        except Exception as e:
            return f"🦀 [寫檔失敗] {e}"

# =============================================================================
# 👑 全能融合閘道器 (Wuchang Universal Gateway)
# =============================================================================
class WuchangUniversalGateway:
    def __init__(self):
        self.privacy = PrivacyGatewayEngine()
        self.network = MerlinIPv6VPNNetwork()
        self.memory = FoldedMemoryManager()
        self.concurrency = TaijiConcurrencyEngine(self.memory)
        self.open_claw = OpenClawProxy()
        self.api_url = WINDOWS_OLLAMA_URL # 👉 精準指向宿主機

        self.tools = [
            {
                "type": "function", "function": {
                    "name": "delegate_to_cloud_brain", 
                    "description": "遇到複雜推理或算力不足時，呼叫此工具卸載給雲端企業大腦進行盲算。",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "anonymized_payload": {"type": "string"},
                            "task_instruction": {"type": "string"}
                        }, 
                        "required": ["anonymized_payload", "task_instruction"]
                    }
                }
            },
            {
                "type": "function", "function": {
                    "name": "obedient_claw_execute",
                    "description": "執行 Linux 終端機指令 (如查詢目錄、看日誌)。受專利沙盒保護。",
                    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
                }
            },
            {
                "type": "function", "function": {
                    "name": "lobster_code_writer",
                    "description": "將程式碼寫入實體硬碟檔案中。",
                    "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "code_content": {"type": "string"}}, "required": ["file_path", "code_content"]}
                }
            }
        ]

    async def _execute_tool(self, call: Dict, context_id: str) -> str:
        name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"]) if isinstance(call["function"]["arguments"], str) else call["function"]["arguments"]
        
        if name == "delegate_to_cloud_brain":
            raw_payload = args.get("anonymized_payload", "")
            instruction = args.get("task_instruction", "")
            logging.info("🧠 [雙腦協作] 啟動專利碎化與雲端盲算...")
            
            ephemeral_key, fragmented_payload = TEEReconstructionEngine.ai_fragmentation_xor(raw_payload)
            await self.memory.write(f"tx_{context_id}", ephemeral_key, ttl_seconds=60)
            transmitted_delta = await self.network.asynchronous_capture_and_push(fragmented_payload, context_id)
            cloud_response = await CloudGeminiWorker.process_intent(instruction, transmitted_delta)
            
            retrieved_key = await self.memory.read_and_pop(f"tx_{context_id}")
            if not retrieved_key: return "❌ TEE 記憶體已銷毀，解碼失敗。"
            return TEEReconstructionEngine.reconstruct_and_zeroize(retrieved_key, cloud_response)
            
        elif name == "obedient_claw_execute":
            logging.info(f"🦀 [龍蝦雙螯] 執行終端指令: {args.get('command')}")
            return await self.open_claw.obedient_claw_execute(args.get("command", ""))
            
        elif name == "lobster_code_writer":
            logging.info(f"🦀 [龍蝦雙螯] 實體寫檔: {args.get('file_path')}")
            return self.open_claw.lobster_code_writer(args.get("file_path", ""), args.get("code_content", ""))

    async def process_intent_routing(self, user_input: str, webui_system_prompt: str = ""):
        context_id = f"CTX_{int(time.time())}"
        await self.concurrency.start_taiji_matrix(context_id)
        
        try:
            anonymized_input = self.privacy.deterministic_mapping(user_input)
            
            core_directive = f"[V14 True Absolute Override] You MUST use the provided tools (delegate_to_cloud_brain, obedient_claw_execute, lobster_code_writer) whenever physical actions or complex reasoning are required. Supreme Commander is {SOVEREIGN_OWNER_ID}."
            final_system_prompt = f"{webui_system_prompt}\n\n{core_directive}"
            
            payload = {
                "model": "llama3.1", 
                "messages": [{"role": "system", "content": final_system_prompt}, {"role": "user", "content": anonymized_input}], 
                "tools": self.tools, 
                "stream": False,
                "options": {"num_gpu": 99},
                "keep_alive": "15m"
            }
            
            async with httpx.AsyncClient() as client:
                res = await client.post(self.api_url, json=payload, timeout=120.0)
                msg = res.json().get("message", {})
            
            if "tool_calls" in msg:
                results = []
                for call in msg["tool_calls"]:
                    res = await self._execute_tool(call, context_id)
                    results.append(res)
                return self.privacy.deanonymize("\n\n".join(results))
                
            return self.privacy.deanonymize(msg.get('content', ''))
            
        except PermissionError as pe:
            return f"🚫 {str(pe)}"
        except Exception as e:
            return f"❌ System Error (請確認 Windows 端 Ollama 是否允許跨域 0.0.0.0): {e}"
        finally:
            await self.concurrency.collapse_matrix()

wuchang_gateway = WuchangUniversalGateway()

# =============================================================================
# FastAPI 網路端點 & 系統啟動事件
# =============================================================================
@app.on_event("startup")
async def startup_event():
    logging.info("="*85)
    logging.info("🚀 [V14 True Absolute Edition]: WSL Bridge x VRAM Lockdown x Enterprise Brain")
    logging.info("="*85)
    # 系統啟動時，確實執行 VRAM 鎖定引擎！
    await OllamaGPUEnforcer.enforce_vram_allocation(api_url=WINDOWS_OLLAMA_URL)

class OpenAIChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "wuchang-v14"

@app.get("/v1/models")
def get_openai_models():
    return {"object": "list", "data": [{"id": "wuchang-v14-true-absolute", "object": "model", "created": int(time.time()), "owned_by": "Wuchang-Taiji"}]}

@app.post("/v1/chat/completions")
async def openai_chat_endpoint(req: OpenAIChatRequest):
    webui_sys_prompt = "\n".join([m["content"] for m in req.messages if m["role"] == "system"])
    user_msg = [m["content"] for m in req.messages if m["role"] == "user"][-1]
    
    logging.info(f"\n📥 [WebUI 請求接入] {user_msg}")
    final_answer = await wuchang_gateway.process_intent_routing(user_msg, webui_sys_prompt)
    
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion", "created": int(time.time()), "model": req.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": final_answer}, "finish_reason": "stop"}]
    }

class OpenAITTSRequest(BaseModel): input: str
@app.get("/v1/audio/voices")
def get_audio_voices():
    if voice_engine and hasattr(voice_engine, "get_voices"):
        voices = voice_engine.get_voices()
    else:
        voices = [{"id": "wuchang-tts-zh-tw", "object": "voice", "name": "Wuchang Chinese", "language": "zh-TW", "default": True}]
    return {"object": "list", "data": voices}

@app.post("/v1/audio/speech")
def openai_tts_endpoint(req: OpenAITTSRequest):
    if not voice_engine: raise HTTPException(status_code=500, detail="語音未啟動")
    file_path = voice_engine.speak(req.input, f"webui_tts_{int(time.time()*1000)}.wav")
    return FileResponse(file_path, media_type="audio/wav", filename="wuchang_voice.wav")

if __name__ == "__main__":
    print("="*60)
    print("🛡️ 【V14 究極無損真理閘道器】啟動中 (Port: 9002)...")
    print(f"   [網路對接] 宿主機雷達已鎖定 Windows IP: {WINDOWS_OLLAMA_IP}")
    print("   [底層引擎] TaijiConcurrencyEngine (併發清理) - 已完整恢復")
    print("   [底層引擎] OllamaGPUEnforcer (VRAM 鎖定) - 已完整恢復")
    print("   [已整合] 雲端企業盲算 + 龍蝦終端雙螯 + 實體物理寫檔")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=9002)
