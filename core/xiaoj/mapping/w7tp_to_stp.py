from core.xiaoj.mapping.intent_taxonomy import classify

def convert(t):

    intent_code = classify(
        t.get("D7_intent","")
    )

    return {

        "乾": 1,

        "震": intent_code,

        "離": 1,

        "巽": 0,

        "坤": 1,

        "坎": "low",

        "艮": "validate",

        "兌": "agent"
    }
