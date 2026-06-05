import time

class W7TPStateSync:
    def __init__(self):
        self.global_state = {}
        self.nodes = ["taiji01", "cloud", "ollama"]

    def push(self, node, packet):
        self.global_state.setdefault(node, []).append({
            "packet": packet,
            "timestamp": time.time()
        })

    def mesh(self):
        merged = []
        for n, ps in self.global_state.items():
            for p in ps:
                merged.append({
                    "node": n,
                    "packet": p["packet"],
                    "ts": p["timestamp"]
                })
        return merged
