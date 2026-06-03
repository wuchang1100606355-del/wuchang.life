import requests
import json
from dataclasses import dataclass

OLLAMA_API_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "llama3.2:1b"

@dataclass
class ProcessedPacket:
    original_text: str
    masked_text: str
    detected_intent: str
    token_map: dict

class XiaoJ_LocalDriver:
    def __init__(self):
        print(f"[系統初始化] 正在連線至本地算力端點: {OLLAMA_API_URL}")

    def smart_desensitize(self, user_text: str, user_profile: dict) -> ProcessedPacket:
        system_prompt = f"""你現在是五常社區的隱私守護者。請找出以下句子中的個人資訊（如姓名），並用 <ENTITY: USER_NAME> 替換。目前登入使用者為：{user_profile.get('name', '未知')}。你只需回傳替換後的句子，不要回覆其他多餘對話。"""
        
        payload = {
            "model": LOCAL_MODEL,
            "prompt": f"{system_prompt}\n\n使用者輸入: {user_text}",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        try:
            response = requests.post(OLLAMA_API_URL, json=payload)
            masked_text = response.json().get("response", "").strip()
            token_map = {"<ENTITY: USER_NAME>": user_profile.get('name', '未知')}
            intent = "community_care" if "掛號" in user_text or "看診" in user_text else "unknown"
            return ProcessedPacket(user_text, masked_text, intent, token_map)
        except Exception as e:
            print(f"[錯誤] {e}")
            return None
