from runtime_ab.a_runtime.a_runtime import ARuntime
from runtime_ab.b_kernel.b_kernel import BKernel

class ABBridge:
    """
    A/B OS dispatcher
    """

    def __init__(self):
        self.a = ARuntime()
        self.b = BKernel()

    def dispatch(self, packet):
        decision = self.b.route(packet)

        if decision["status"] != "APPROVED":
            return decision

        return self.a.execute(packet)
