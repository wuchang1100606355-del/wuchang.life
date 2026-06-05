class W7TPMemory:
    def __init__(self):
        self.store = []

    def write(self, packet):
        self.store.append(packet)

    def read_all(self):
        return self.store
