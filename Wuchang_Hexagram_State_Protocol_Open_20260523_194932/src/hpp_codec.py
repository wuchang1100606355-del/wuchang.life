from dataclasses import dataclass

@dataclass(frozen=True)
class HexagramPacket:
    version: int
    hexagram: str
    state_mode: str
    emergency: bool = False

    def __post_init__(self):
        if len(self.hexagram) != 6 or any(c not in "01" for c in self.hexagram):
            raise ValueError("hexagram must be a 6-bit string")

def complement(hexagram: str) -> str:
    return "".join("1" if c == "0" else "0" for c in hexagram)

def reverse(hexagram: str) -> str:
    return hexagram[::-1]

def validate_complement(a: str, b: str) -> bool:
    return complement(a) == b

if __name__ == "__main__":
    pkt = HexagramPacket(version=1, hexagram="101011", state_mode="S1_DEGRADED")
    print({
        "packet": pkt,
        "complement": complement(pkt.hexagram),
        "reverse": reverse(pkt.hexagram),
        "valid_pair": validate_complement(pkt.hexagram, complement(pkt.hexagram))
    })
