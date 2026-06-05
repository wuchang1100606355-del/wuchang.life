import hashlib
import json

def packet_hash(data):
    payload = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False
    )
    return hashlib.sha256(
        payload.encode()
    ).hexdigest()
