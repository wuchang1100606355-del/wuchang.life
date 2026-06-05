def build_packet_delta(
    old_coordinate,
    new_coordinate
):

    delta = []

    for i in range(
        len(old_coordinate)
    ):

        if old_coordinate[i] != new_coordinate[i]:

            delta.append({
                "dimension": i,
                "before": old_coordinate[i],
                "after": new_coordinate[i]
            })

    return delta
