import time
import hashlib
import json

class Tensor8D:

    def __init__(self, payload: dict):
        self.timestamp = time.time()
        self.payload = payload

    def to_dict(self):
        return {
            "D1_identity": self.payload.get("D1_identity"),
            "D2_duality": self.payload.get("D2_duality"),
            "D3_structure": self.payload.get("D3_structure"),
            "D4_events": self.payload.get("D4_events"),
            "D5_resources": self.payload.get("D5_resources"),
            "D6_mesh": self.payload.get("D6_mesh"),
            "D7_intent": self.payload.get("D7_intent"),
            "D8_commit": self.payload.get("D8_commit"),
            "ts": self.timestamp
        }

    def hash(self):
        raw = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
