class NativeRuleEvidenceMissing(RuntimeError):
    """Raised when a native ADI rule lacks Founder-source evidence."""

    code = "HOLD_NATIVE_RULE_EVIDENCE_MISSING"

    def __init__(self, rule: str):
        self.rule = rule
        super().__init__(f"{self.code}:{rule}")


class LedgerParseFailure(RuntimeError):
    code = "HOLD_LEDGER_PARSE_FAILURE"

    def __init__(self, path: str, detail: str):
        self.path = path
        super().__init__(f"{self.code}:{path}:{detail}")
