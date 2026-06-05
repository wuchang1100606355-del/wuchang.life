from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class SymbolicTensorPacket:
    packet_ref: str
    tensor: Dict[str, Any]
    delta: Dict[str, Any]

    def to_dict(self):
        return {
            "packet_ref": self.packet_ref,
            "tensor": self.tensor,
            "delta": self.delta,
        }
