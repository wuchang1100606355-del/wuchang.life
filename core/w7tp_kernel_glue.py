from metric_tensor import decide

class KernelGlue:
    def route(self, packet):
        weights = {"P":0.8,"E":0.5,"L":0.6,"S":0.4,"R":0.3}
        model = decide(weights)

        return {
            "model": model,
            "packet": str(packet)
        }
