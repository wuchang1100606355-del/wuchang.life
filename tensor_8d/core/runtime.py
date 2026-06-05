from tensor_8d.compiler.compiler import TensorCompiler
from tensor_8d.validator.validator import TensorValidator
from tensor_8d.ledger.evidence_ledger import EvidenceLedger
from tensor_8d.core.tensor_schema import Tensor8D

class TensorRuntime8D:

    def __init__(self):
        self.compiler = TensorCompiler()
        self.validator = TensorValidator()
        self.ledger = EvidenceLedger()

    def run(self, prompt: str):

        raw = self.compiler.compile(prompt)

        ok, reason = self.validator.validate(raw)

        if not ok:
            return {
                "state": "REJECTED",
                "reason": reason,
                "raw": raw
            }

        tensor = Tensor8D(raw)

        commit_hash = self.ledger.commit(tensor.to_dict(), source="w7tp_runtime")

        return {
            "state": "COMMITTED",
            "hash": commit_hash,
            "tensor": tensor.to_dict()
        }
