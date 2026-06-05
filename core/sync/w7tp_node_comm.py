from sync.w7tp_state_sync import W7TPStateSync

class W7TPNodeComm:
    def __init__(self):
        self.sync = W7TPStateSync()

    def broadcast(self, packet):
        for node in ["taiji01", "cloud", "ollama"]:
            self.sync.push(node, packet)

    def query_all(self):
        return self.sync.mesh()
