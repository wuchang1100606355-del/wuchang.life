from typing import Dict, Any
import json

class W7TPKernelOrchestrator:
    def __init__(self, router, engine, memory):
        self.router = router
        self.engine = engine
        self.memory = memory

    def run(self, text: str) -> Dict[str, Any]:
        packet = self.engine.translate_text(text)
        route = self.router.resolve(packet)

        result = self.dispatch(route, packet)

        self.memory.write({
            "packet_ref": packet.packet_ref,
            "route": route,
            "result": result
        })

        return {
            "packet": packet.as_dict(),
            "route": route,
            "result": result
        }

    def dispatch(self, route: str, packet: Any):
        if "odoo" in route:
            return {"exec": "odoo_triggered"}

        if "voice" in route:
            return {"exec": "voice_triggered"}

        if "cloud" in route:
            return {"exec": "cloud_llm"}

        return {"exec": "local_runtime"}
