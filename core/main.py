from w7tp_kernel_glue import KernelGlue
from w7tp_router import W7TPRouter
from bridge.execution_bridge import ExecutionBridge
from sync.w7tp_node_comm import W7TPNodeComm

class W7TPRuntime:
    def __init__(self):
        self.glue = KernelGlue()
        self.router = W7TPRouter()
        self.bridge = ExecutionBridge()
        self.comm = W7TPNodeComm()

    def run(self, text):
        packet = {"input": text}

        route = self.router.resolve(self.glue.route(packet))
        result = self.bridge.execute_packet(route)

        self.comm.broadcast({
            "input": text,
            "route": route,
            "result": result
        })

        return {
            "route": route,
            "result": result
        }

if __name__ == "__main__":
    r = W7TPRuntime()
    print(r.run("查詢專利相似技術"))
