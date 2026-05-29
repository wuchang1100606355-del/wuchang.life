"""
title: Taiji Array Tools (Slim)
author: F124771717
description: Minified tools for LLM.
"""
import urllib.request, json
class Tools:
    def __init__(self): self.api = "http://host.docker.internal:8000" # Docker 穿透專用
    def get_tensor(self) -> str:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/tensor", method="GET"), timeout=5) as r: return r.read().decode()
        except Exception as e: return f"Err:{e}"
    def strike(self, target_node: str) -> str:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/forward/{target_node}?command=STRIKE", method="POST"), timeout=5) as r: return r.read().decode()
        except Exception as e: return f"Err:{e}"
    def get_radar(self) -> str:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/stats", method="GET"), timeout=5) as r: return r.read().decode()
        except Exception as e: return f"Err:{e}"
