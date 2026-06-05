from core.stp.governance_rules import RULES

def neighbors(symbol, state):

    if symbol not in RULES:
        return []

    return RULES[symbol].get(state, [])
