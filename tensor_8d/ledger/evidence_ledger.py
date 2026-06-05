import json
import time
import hashlib

class EvidenceLedger:

    def __init__(self, path="tensor_8d_ledger.jsonl"):
        self.path = path

    def commit(self, tensor: dict, source="local"):

        record = {
            "ts": time.time(),
            "source": source,
            "tensor": tensor
        }

        raw = json.dumps(record, sort_keys=True)
        record["hash"] = hashlib.sha256(raw.encode()).hexdigest()

        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")

        return record["hash"]
