from core.stp.state_hash \
    import state_hash

def build_genesis():

    coordinate = (
        0,0,0,0,0,0,0,0
    )

    return {

        "packet_ref":
            "GENESIS",

        "coordinate":
            list(coordinate),

        "state_hash":
            state_hash(
                coordinate
            )
    }
