# -*- coding: utf-8 -*-
import requests

class OllamaClient:
    def __init__(self, model="sister-j-brain:latest"):
        self.model = model
        self.url = "http://localhost:11434"

    def generate(self, prompt, system=""):
        r = requests.post(
            f"{self.url}/api/generate",
            json={
                "model": self.model,
                "prompt": f"{system}\n\n{prompt}",
                "stream": False
            },
            timeout=120
        )
        r.raise_for_status()
        return r.json()
