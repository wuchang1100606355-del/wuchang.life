def reconstruct_coordinate(
    coordinate,
    delta
):

    result = list(
        coordinate
    )

    for item in delta:

        result[
            item["dimension"]
        ] = item["after"]

    return tuple(result)
