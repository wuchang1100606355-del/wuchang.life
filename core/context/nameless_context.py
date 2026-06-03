# 無名文上下文總成核心
def build_nameless_context(records):
    records = list(records)
    return {
        "context_type": "nameless_context_aggregate",
        "count": len(records),
        "records": records,
        "principles": [
            "local_first",
            "data_sovereignty",
            "user_controlled_tool_invocation",
            "minimum_disclosure",
            "community_public_interest"
        ]
    }
