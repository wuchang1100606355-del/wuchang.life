from w7tp_nodes import W7TPNodeRegistry

class W7TPRouter:
    def __init__(self):
        self.registry = W7TPNodeRegistry()

    def resolve(self, packet):
        route_hint = str(packet)
        return self.registry.resolve(route_hint)
