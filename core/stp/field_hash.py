import hashlib
import json

def build_field_hash(tensor):

    payload = json.dumps(
        tensor,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()
