from core.stp.packet_ref \
    import build_packet_ref

from core.stp.runtime \
    import build_runtime_state

def build_packet(
    tensor
):

    runtime = build_runtime_state(
        tensor
    )

    return {

        "packet_ref":
            build_packet_ref(),

        "state_hash":
            runtime["state_hash"],

        "coordinate":
            runtime["coordinate"],

        "tensor":
            tensor
    }
