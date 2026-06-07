class TensorCoordinate:

    ORDER = [
        "D1_identity",
        "D2_duality",
        "D3_structure",
        "D4_events",
        "D5_resources",
        "D6_mesh",
        "D7_intent",
        "D8_commit"
    ]

    @classmethod
    def build(cls,tensor):

        return tuple(
            hash(
                str(
                    tensor.get(k,"")
                )
            ) & 65535
            for k in cls.ORDER
        )
