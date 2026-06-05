def reconstruct_state(
    previous_state,
    delta
):

    result = dict(previous_state)

    for k,v in delta.items():

        result[k] = v["after"]

    return result
