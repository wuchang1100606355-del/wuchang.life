from core.stp.symbol_dictionary import SymbolDictionary

dictionary = SymbolDictionary(
    "configs/dictionaries/stp_symbols.json"
)

def encode_tensor(tensor):

    result = dict(tensor)

    if "震" in result:
        result["震"] = dictionary.encode(
            "intent",
            result["震"]
        )

    if "坎" in result:
        result["坎"] = dictionary.encode(
            "risk",
            result["坎"]
        )

    if "艮" in result:
        result["艮"] = dictionary.encode(
            "governance",
            result["艮"]
        )

    if "兌" in result:
        result["兌"] = dictionary.encode(
            "interaction",
            result["兌"]
        )

    return result
