# -*- coding: utf-8 -*-

class ContextPacketBuilder:
    def build(self, intent_packet: dict):
        text = (intent_packet.get("prompt", "") + " " + intent_packet.get("keyword", "")).lower()
        shards = []

        if any(k in text for k in ["搜尋", "search", "掃描", "scan", "找", "find"]):
            shards.append({"type": "action", "value": "scan"})

        if any(k in text for k in ["摘要", "整理", "判斷", "分析", "reason", "summarize"]):
            shards.append({"type": "action", "value": "reason"})

        if "taiji" in text:
            shards.append({"type": "target", "value": "taiji"})

        if "jules" in text or "小j" in text or "sister" in text:
            shards.append({"type": "target", "value": "xiaoj"})

        shards.append({"type": "scope", "value": "local"})

        return {
            "context_type": "taiji_context_shards",
            "intent": intent_packet.get("intent"),
            "prompt": intent_packet.get("prompt", ""),
            "keyword": intent_packet.get("keyword", ""),
            "shards": shards,
            "raw": intent_packet
        }
