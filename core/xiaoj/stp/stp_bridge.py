from core.xiaoj.runtime import XiaoJRuntime
from core.stp.packet_builder import build_packet
from core.xiaoj.mapping.w7tp_to_stp import convert

class XiaoJSTPBridge:

    def run(self,text):

        result = XiaoJRuntime().run(text)

        tensor = result["tensor"]

        stp_tensor = convert(
            tensor
        )

        packet = build_packet(
            stp_tensor
        )

        return {
            "tensor": tensor,
            "stp_tensor": stp_tensor,
            "packet": packet
        }
