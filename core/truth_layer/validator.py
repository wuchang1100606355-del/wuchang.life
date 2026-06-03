def validate_output(output, sources):
    score = 0
    for s in sources:
        if s in output:
            score += 1
    confidence = score / (len(sources) + 1e-6)
    if confidence < 0.3:
        return "[UNVERIFIED] " + output
    return output
