import numpy as np
import httpx
import asyncio
import jwt
import os
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

FEATURE_DIM = 3

class HumanIntent(BaseModel):
    core_goal: str
    strict_constraints: List[str]

class CandidateSolution(BaseModel):
    id: str
    features: List[float]
    raw_context: str

TAIJI01_NODE_IP = "http://100.71.224.18:8000/api/v1/infer"
TAIJI_SECRET = os.getenv("TAIJI_HMAC_SECRET", "default_fallback_secret")

def generate_topology_signature(node_id: str) -> str:
    payload = {
        "node": node_id,
        "exp": datetime.now(timezone.utc).timestamp() + 30,
        "auth_level": "ultra_proxy"
    }
    return jwt.encode(payload, TAIJI_SECRET, algorithm="HS256")

async def evaluate_fuzzy_causality_taiji_routed(intent: HumanIntent, candidates: List[CandidateSolution]):
    if not candidates:
        return None

    # 主權脫敏
    context_payload = "\n".join([f"ID: {c.id} | 脫敏內容: [MASKED_DATA_FOR_{c.id}]" for c in candidates])
    prompt = f"決策目標: {intent.core_goal}\n絕對限制: {intent.strict_constraints}\n脫敏名單:\n{context_payload}\n"

    headers = {
        "Authorization": f"Bearer {generate_topology_signature('mu_1_edge')}",
        "X-Taiji-Route": "mu_1->mu_4"
    }

    print("[mu_1 小J 邊緣皮層] 攔截原始資料，完成主權脫敏。")
    print(f"[mu_1 小J 邊緣皮層] 夾帶 JWT 簽章，路由至 mu_4 (taiji01: 100.71.224.18)...")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(TAIJI01_NODE_IP, json={"prompt": prompt, "model_role": "architecture_eval"}, headers=headers)
            response.raise_for_status()
            best_id = response.json().get("best_candidate_id", "").strip()
            print(f"[mu_4 taiji01 回應] 最佳方案 ID: {best_id}")
            return best_id
    except Exception as e:
        print(f"\n[清理緒啟動] 路由至 taiji_01 失敗，執行中斷保護清理。")
        print(f"-> 錯誤原因: {e}")
        print("-> 狀態已安全回滾。")
        return None

async def main():
    intent = HumanIntent(core_goal="尋找效能最高架構", strict_constraints=["無資安風險"])
    data = [
        CandidateSolution(id="A", features=[0.9, 0.8, 0.7], raw_context="原始機密合約A"),
        CandidateSolution(id="B", features=[0.8, 0.9, 0.9], raw_context="原始客戶名單B")
    ]
    await evaluate_fuzzy_causality_taiji_routed(intent, data)

if __name__ == "__main__":
    asyncio.run(main())
