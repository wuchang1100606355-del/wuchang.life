from core.stp.field_hash import build_field_hash
from core.stp.packet_hash import build_packet_hash

def build_packet(
    packet_ref,
    parent_packet,
    tensor
):

    fh = build_field_hash(
        tensor
    )

    ph = build_packet_hash(
        packet_ref,
        parent_packet,
        fh
    )

    return {
        "packet_ref": packet_ref,
        "parent_packet": parent_packet,
        "tensor": tensor,
        "field_hash": fh,
        "packet_hash": ph
    }
