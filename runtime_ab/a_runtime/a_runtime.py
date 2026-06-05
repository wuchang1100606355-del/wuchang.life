class ARuntime:
    """
    A層：純執行層（不可做決策）
    """

    def __init__(self):
        self.buffer = []

    def execute(self, packet):
        self.buffer.append(packet)

        return {
            "layer": "A",
            "status": "EXECUTED",
            "mode": "execution_only",
            "packet": packet
        }
