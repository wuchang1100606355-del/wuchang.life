import hashlib

def build_packet_hash(
    packet_ref,
    parent_packet,
    field_hash
):

    raw = (
        str(packet_ref)
        + str(parent_packet)
        + str(field_hash)
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()
