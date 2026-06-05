from core.stp.tensor_encoder \
    import encode_tensor

from core.stp.tensor_coordinate \
    import build_coordinate

from core.stp.state_hash \
    import state_hash


def build_runtime_state(
    tensor
):

    encoded = encode_tensor(
        tensor
    )

    coordinate = build_coordinate(
        encoded
    )

    hash_value = state_hash(
        coordinate
    )

    return {
        "tensor": tensor,
        "encoded": encoded,
        "coordinate": coordinate,
        "state_hash": hash_value
    }
