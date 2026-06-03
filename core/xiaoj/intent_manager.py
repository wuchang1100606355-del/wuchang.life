# -*- coding: utf-8 -*-

class XiaoJIntentManager:
    def analyze(self, payload: dict):
        prompt = payload.get("prompt", "")
        keyword = payload.get("keyword", "")
        text = f"{prompt} {keyword}".lower()

        if any(k in text for k in ["搜尋", "掃描", "找", "search", "scan", "find"]):
            intent = "claw.scan"
        else:
            intent = "xiaoj.reason"

        return {
            "core": "XiaoJ",
            "intent": intent,
            "prompt": prompt,
            "keyword": keyword,
            "raw": payload
        }
