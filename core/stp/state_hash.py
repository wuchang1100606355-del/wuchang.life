import hashlib

def state_hash(
    coordinate
):

    raw = "|".join(
        map(
            str,
            coordinate
        )
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()
