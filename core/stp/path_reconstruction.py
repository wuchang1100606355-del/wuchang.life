from copy import deepcopy

from core.stp.tensor_coordinate \
    import build_coordinate

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

def reconstruct_path(
    start,
    end
):

    current = deepcopy(start)

    path = [deepcopy(current)]

    for key in SYMBOL_ORDER:

        if current.get(key,0) != end.get(key,0):

            current[key] = end.get(key,0)

            path.append(
                deepcopy(current)
            )

    return path
