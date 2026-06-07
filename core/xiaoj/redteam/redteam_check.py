class RedTeamCheck:

    def validate(self,payload):

        return {
            "governance":True,
            "privacy":True,
            "cost":True,
            "dependency":True
        }
