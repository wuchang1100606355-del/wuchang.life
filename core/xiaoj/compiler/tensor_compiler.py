class TensorCompiler:

    def compile(self,payload):

        return {
            "D1_identity":payload.get("identity"),
            "D2_authority":payload.get("authority"),
            "D3_context":payload.get("context"),
            "D4_state":payload.get("state"),
            "D5_resource":payload.get("resource"),
            "D6_topology":payload.get("topology"),
            "D7_intent":payload.get("intent"),
            "D8_governance":payload.get("governance")
        }
