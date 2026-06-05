import json

class BKernel:
    """
    B層：治理核心（intent + policy）
    """

    REQUIRED_KEYS = ["intent_type", "target", "action", "payload"]

    def validate(self, packet: dict):
        if not isinstance(packet, dict):
            return False, "NOT_DICT"

        for k in self.REQUIRED_KEYS:
            if k not in packet:
                return False, f"MISSING_{k}"

        return True, "OK"

    def route(self, packet):
        ok, reason = self.validate(packet)

        if not ok:
            return {
                "layer": "B",
                "status": "REJECTED",
                "reason": reason
            }

        return {
            "layer": "B",
            "status": "APPROVED",
            "route": "A_RUNTIME",
            "packet": packet
        }
