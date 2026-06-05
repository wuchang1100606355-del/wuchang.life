import json

class SymbolDictionary:

    def __init__(self, path):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            self.data = json.load(f)

    def encode(self, group, value):
        return self.data[group][value]

    def decode(self, group, code):

        for k, v in self.data[group].items():

            if v == code:
                return k

        return None
