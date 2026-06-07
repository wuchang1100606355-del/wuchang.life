def classify(intent:str):

    if "治理" in intent:
        return "approve"

    if "照護" in intent:
        return "validate"

    if "公益" in intent:
        return "publish"

    if "協作" in intent:
        return "submit"

    return "draft"
