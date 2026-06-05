def build_delta_packet(
    old_coordinate,
    new_coordinate
):

    delta = []

    for idx, (a, b) in enumerate(
        zip(
            old_coordinate,
            new_coordinate
        )
    ):

        if a != b:

            delta.append(
                {
                    "dimension": idx,
                    "before": a,
                    "after": b
                }
            )

    return delta
