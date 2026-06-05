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

def build_coordinate(tensor):

    return tuple(
        tensor.get(k, 0)
        for k in SYMBOL_ORDER
    )
