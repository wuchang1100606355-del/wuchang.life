from core.stp.governance_search \
    import find_path

SYMBOLS = [
    "乾",
    "震",
    "離",
    "巽",
    "坤",
    "坎",
    "艮",
    "兌"
]


def search_state(
    start,
    end
):

    result = {}

    for symbol in SYMBOLS:

        s = start.get(symbol)
        e = end.get(symbol)

        if s is None or e is None:
            continue

        result[symbol] = find_path(
            symbol,
            s,
            e
        )

    return result
