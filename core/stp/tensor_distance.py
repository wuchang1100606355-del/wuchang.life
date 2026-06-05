from core.stp.tensor_coordinate \
    import build_coordinate

def tensor_distance(a, b):

    ca = build_coordinate(a)
    cb = build_coordinate(b)

    total = 0

    for x, y in zip(ca, cb):

        total += abs(y - x)

    return total
