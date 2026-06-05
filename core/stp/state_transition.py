from core.stp.governance_rules import RULES

def valid_transition(
    symbol,
    old,
    new
):

    if symbol not in RULES:
        return True

    return (
        new in
        RULES[symbol].get(
            old,
            []
        )
    )
