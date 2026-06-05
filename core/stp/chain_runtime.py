from core.stp.packet_builder import build_packet
from core.stp.packet_delta import build_packet_delta

def build_chain_packet(
    previous_packet,
    tensor
):

    packet = build_packet(
        tensor
    )

    packet["parent_packet"] = \
        previous_packet[
            "packet_ref"
        ]

    packet["delta"] = \
        build_packet_delta(
            previous_packet[
                "coordinate"
            ],
            packet[
                "coordinate"
            ]
        )

    return packet
