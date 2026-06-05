from core.stp.delta_engine import \
    build_delta

def build_next_packet(
    previous_packet,
    next_tensor
):

    delta = build_delta(
        previous_packet["tensor"],
        next_tensor
    )

    return {
        "parent_packet":
            previous_packet["packet_hash"],

        "tensor":
            next_tensor,

        "delta":
            delta
    }
