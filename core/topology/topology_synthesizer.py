# -*- coding: utf-8 -*-

class TopologySynthesizer:
    def build(self, tensor_packet: dict):
        nodes = [
            {"id": "xiaoj.intent", "role": "intent_manager"},
            {"id": "context.shards", "role": "context_fragmentation"},
            {"id": "dugui.metric_tensor", "role": "metric_mapping", "weights": tensor_packet.get("metric_tensor")},
        ]

        if tensor_packet.get("target") == "claw":
            nodes.append({"id": "claw.executor", "role": "automation_claw", "action": "scan_physical"})

        nodes.append({
            "id": "xiaoj.llm",
            "role": "topology_reconstruction",
            "model": tensor_packet.get("model")
        })

        return {
            "topology": "dugui_shard_reconstruction_graph",
            "nodes": nodes,
            "route": tensor_packet
        }
