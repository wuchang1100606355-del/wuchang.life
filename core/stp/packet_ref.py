from datetime import datetime

def build_packet_ref():

    return datetime.utcnow().strftime(
        "STP-%Y%m%d-%H%M%S"
    )
