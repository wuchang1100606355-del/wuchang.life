class RequirementDisclosure:
    def build(self,gaps):
        return {"missing":gaps,"must_ask":len(gaps)>0}
