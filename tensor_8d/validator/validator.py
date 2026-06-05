class TensorValidator:

    REQUIRED = [
        "D1_identity","D2_duality","D3_structure","D4_events",
        "D5_resources","D6_mesh","D7_intent","D8_commit"
    ]

    def validate(self, tensor: dict):

        if not isinstance(tensor, dict):
            return False, "NOT_DICT"

        for k in self.REQUIRED:
            if k not in tensor:
                return False, f"MISSING_{k}"

        return True, "OK"
