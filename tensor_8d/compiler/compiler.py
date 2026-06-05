import subprocess
import json
import re

class TensorCompiler:

    def __init__(self, model="qwen2.5-coder:7b-instruct"):
        self.model = model

    def compile(self, prompt: str):

        system = """
Return ONLY valid JSON with 8D fields:
D1_identity, D2_duality, D3_structure, D4_events,
D5_resources, D6_mesh, D7_intent, D8_commit
"""

        result = subprocess.run(
            ["ollama", "run", self.model, system + "\n" + prompt],
            capture_output=True,
            text=True
        )

        raw = result.stdout

        match = re.search(r"\{.*\}", raw, re.S)

        if not match:
            return {
                "error": "INVALID_TENSOR_OUTPUT",
                "raw": raw
            }

        try:
            return json.loads(match.group(0))
        except:
            return {
                "error": "PARSE_FAILED",
                "raw": raw
            }
