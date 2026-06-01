from dataclasses import dataclass

@dataclass
class State7D:
    trust: int
    rate: int
    entropy: int
    protocol: int
    role: int
    emergency: int
    history: int

def clamp(v: float) -> int:
    return max(0, min(100, int(v)))

def score_7d(s: State7D) -> int:
    if s.emergency >= 90:
        return 100
    return clamp(
        0.22 * s.trust +
        0.18 * (100 - s.rate) +
        0.12 * s.entropy +
        0.18 * s.protocol +
        0.12 * s.role +
        0.08 * s.emergency +
        0.10 * s.history
    )

def decide(score: int, degraded: bool = False) -> str:
    if degraded:
        if score >= 80:
            return "ALLOW"
        if score >= 50:
            return "RATE_LIMIT"
        return "DROP"

    if score >= 80:
        return "ALLOW"
    if score >= 50:
        return "CHALLENGE"
    if score >= 20:
        return "RATE_LIMIT"
    return "DROP"

if __name__ == "__main__":
    s = State7D(80, 15, 60, 90, 70, 0, 75)
    score = score_7d(s)
    print({"score": score, "decision": decide(score)})
