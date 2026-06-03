# -*- coding: utf-8 -*-
from math import exp

def _sigmoid(x): return 1/(1+exp(-x))

class MetricTensorEngine:
    """
    G(intent, context, runtime) → 決策分數
    """

    def build_G(self, intent, shards, runtime):
        # 基本權重（可後續學習/調整）
        w_intent  = 1.0 if intent.startswith("claw") else 0.6
        w_context = min(1.0, 0.2 + 0.1*len(shards))
        w_runtime = 1.0 if runtime.get("claw") else 0.3
        w_risk    = 0.8 if any(s.get("value")=="scan" for s in shards) else 0.3
        w_cost    = 0.5  # 可接入實際資源/時間成本

        G = {
            "intent": w_intent,
            "context": w_context,
            "runtime": w_runtime,
            "risk": w_risk,
            "cost": w_cost
        }
        return G

    def features(self, intent, shards, runtime):
        # φ 向量（0~1）
        has_scan = 1.0 if any(s.get("value")=="scan" for s in shards) else 0.0
        need_reason = 1.0 if any(s.get("value")=="reason" for s in shards) else 0.0
        claw_up = 1.0 if runtime.get("claw") else 0.0
        ollama_up = 1.0 if runtime.get("ollama") else 0.0

        phi_claw = {
            "intent": has_scan,
            "context": 0.7,
            "runtime": claw_up,
            "risk": has_scan,
            "cost": 0.6
        }
        phi_llm = {
            "intent": need_reason,
            "context": 0.9,
            "runtime": ollama_up,
            "risk": 0.3,
            "cost": 0.7
        }
        phi_edge = {
            "intent": 0.5,
            "context": 0.5,
            "runtime": 0.8,
            "risk": 0.2,
            "cost": 0.4
        }
        return phi_claw, phi_llm, phi_edge

    def score(self, G, phi):
        return sum(G[k]*phi[k] for k in G.keys())

    def route(self, intent, shards, runtime):
        G = self.build_G(intent, shards, runtime)
        phi_c, phi_l, phi_e = self.features(intent, shards, runtime)

        s_claw = self.score(G, phi_c)
        s_llm  = self.score(G, phi_l)
        s_edge = self.score(G, phi_e)

        # 溫和壓縮，避免極端
        S = {
            "claw": _sigmoid(s_claw),
            "llm":  _sigmoid(s_llm),
            "edge": _sigmoid(s_edge)
        }

        # 決策
        if S["claw"] >= max(S["llm"], S["edge"]):
            target, action = "claw", "scan_physical"
        elif S["llm"] >= max(S["claw"], S["edge"]):
            target, action = "xiaoj_llm", "reason"
        else:
            target, action = "edge", "dispatch"

        return {
            "G": G,
            "scores": S,
            "decision": {"target": target, "action": action}
        }
