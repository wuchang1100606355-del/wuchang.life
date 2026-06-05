def reconstruct(
    genesis_coordinate,
    deltas
):

    current = list(
        genesis_coordinate
    )

    for delta in deltas:

        for item in delta:

            current[
                item["dimension"]
            ] = item["after"]

    return tuple(current)
