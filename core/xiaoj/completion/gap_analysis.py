class GapAnalysis:

    REQUIRED=[
        "identity",
        "intent",
        "resource",
        "governance"
    ]

    def analyze(self,payload):

        missing=[]

        for k in self.REQUIRED:
            if k not in payload:
                missing.append(k)

        return missing
