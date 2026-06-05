from core.stp.tensor_coordinate \
    import build_coordinate

def coordinate_delta(
    before,
    after
):

    c1 = build_coordinate(before)
    c2 = build_coordinate(after)

    result = []

    for i in range(len(c1)):

        if c1[i] != c2[i]:

            result.append(
                (
                    i,
                    c1[i],
                    c2[i]
                )
            )

    return result
