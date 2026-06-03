"""
title: Taiji Array Tools (Slim)
author: F124771717
description: Minified tools for LLM to interact with Taiji Array.
"""
import urllib.request, json

class Tools:
    def __init__(self): 
        self.api = "http://127.0.0.1:8000"

    def get_tensor(self) -> str:
        """Get 4D metric tensor, eigenvalues & array health. Use for status check."""
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/tensor", method="GET"), timeout=5) as r:
                return r.read().decode()
        except Exception as e: return f"Err:{e}"

    def strike(self, target_node: str) -> str:
        """Send physical strike/auth to node (mu_0, mu_1, mu_2)."""
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/forward/{target_node}?command=STRIKE", method="POST"), timeout=5) as r:
                return r.read().decode()
        except Exception as e: return f"Err:{e}"

    def get_radar(self) -> str:
        """Get network radar logs & total communication stats."""
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{self.api}/api/v1/stats", method="GET"), timeout=5) as r:
                return r.read().decode()
        except Exception as e: return f"Err:{e}"
