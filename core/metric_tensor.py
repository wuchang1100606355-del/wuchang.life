def decide(weights):
    score = (
        weights["P"] * 0.3 +
        weights["E"] * 0.2 +
        weights["L"] * 0.2 +
        weights["S"] * 0.2 +
        weights["R"] * 0.1
    )

    if score > 0.7:
        return "local_model"

    return "cloud_model"
