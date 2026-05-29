# -*- coding: utf-8 -*-

class DuguiTensorMapper:
    def map(self, context_packet: dict):
        shards = context_packet.get("shards", [])
        intent = context_packet.get("intent")

        weights = {
            "use_claw": 0.0,
            "use_llm": 0.0,
            "reconstruct_topology": 1.0,
            "context_shard_density": float(len(shards))
        }

        for s in shards:
            if s["type"] == "action" and s["value"] == "scan":
                weights["use_claw"] += 1.0
            if s["type"] == "action" and s["value"] == "reason":
                weights["use_llm"] += 1.0

        if intent == "claw.scan":
            weights["use_claw"] += 1.0
            weights["use_llm"] += 0.8
            target = "claw"
            action = "scan_physical_then_llm_reconstruct"
        else:
            weights["use_llm"] += 1.0
            target = "xiaoj_llm"
            action = "reason"

        model = "sister-j-brain:latest"
        if weights["use_llm"] >= 1.5:
            model = "Sister_J_DeepSeek:latest"

        return {
            "engine": "dugui_tensor_mapper",
            "metric_tensor": weights,
            "intent": intent,
            "target": target,
            "action": action,
            "model": model,
            "keyword": context_packet.get("keyword", ""),
            "prompt": context_packet.get("prompt", ""),
            "shards": shards,
            "tensor_state": "mapped"
        }
