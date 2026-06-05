SYMBOL_MAP = {
    "乾": "identity",
    "震": "intent",
    "離": "authority",
    "巽": "relation",
    "坤": "resource",
    "坎": "risk",
    "艮": "governance",
    "兌": "interaction",
}

def resolve(symbol):
    return SYMBOL_MAP.get(symbol)
