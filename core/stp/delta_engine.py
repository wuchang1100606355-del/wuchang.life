def build_delta(before, after):

    delta = {}

    keys = set(before.keys()) | set(after.keys())

    for k in keys:

        old = before.get(k)
        new = after.get(k)

        if old != new:

            delta[k] = {
                "before": old,
                "after": new
            }

    return delta
