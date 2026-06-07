class IntentDiscovery:

    def discover(self,text:str):

        intent="xiaoj.reason"

        if any(k in text for k in [
            "搜尋","搜索","scan","search"
        ]):
            intent="claw.scan"

        return {
            "raw":text,
            "intent":intent,
            "confidence":0.8,
            "known":[],
            "missing":[]
        }
