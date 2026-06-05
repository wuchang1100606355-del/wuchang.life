from core.stp.governance_rules import RULES

def expand_dimension(symbol,start,end):

    if symbol not in RULES:
        return [start,end]

    result = [start]

    current = start

    while current != end:

        current = RULES[symbol][current][0]

        result.append(current)

    return result
