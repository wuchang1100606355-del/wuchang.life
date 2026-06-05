REQUIRED = [
    "乾",
    "震",
    "離",
    "巽",
    "坤",
    "坎",
    "艮",
    "兌"
]

def validate_tensor(tensor):

    missing = []

    for k in REQUIRED:
        if k not in tensor:
            missing.append(k)

    return {
        "valid": len(missing) == 0,
        "missing": missing
    }
