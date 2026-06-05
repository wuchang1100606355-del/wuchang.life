from copy import deepcopy

from core.stp.governance_rules \
    import RULES

SYMBOL_ORDER = [
    "乾",
    "震",
    "離",
    "巽",
    "坤",
    "坎",
    "艮",
    "兌"
]


def expand_dimension(
    symbol,
    start,
    end
):

    if start == end:
        return [start]

    if symbol not in RULES:
        return [start, end]

    path = [start]

    current = start

    while current != end:

        current = RULES[symbol][current][0]

        path.append(current)

    return path


def reconstruct(
    start_state,
    end_state
):

    current = deepcopy(start_state)

    history = [deepcopy(current)]

    for symbol in SYMBOL_ORDER:

        start_value = current.get(symbol)

        end_value = end_state.get(symbol)

        if start_value == end_value:
            continue

        path = expand_dimension(
            symbol,
            start_value,
            end_value
        )

        for value in path[1:]:

            current[symbol] = value

            history.append(
                deepcopy(current)
            )

    return history
