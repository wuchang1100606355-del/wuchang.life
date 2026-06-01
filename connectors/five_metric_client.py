#!/usr/bin/env python3
import json
import urllib.request

BASE_URL = "http://127.0.0.1:8105"

def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))

def get_json(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))

def health():
    return get_json("/health")

def nearest(current, memory_pool, weights=None):
    payload = {
        "current": current,
        "memory_pool": memory_pool
    }
    if weights is not None:
        payload["weights"] = weights
    return post_json("/nearest", payload)

def hazard_check(current, memory_pool, weights=None):
    payload = {
        "current": current,
        "memory_pool": memory_pool
    }
    if weights is not None:
        payload["weights"] = weights
    return post_json("/hazard-check", payload)

if __name__ == "__main__":
    print("=== FIVE METRIC CLIENT CHECK ===")
    print(json.dumps(health(), ensure_ascii=False, indent=2))

    memory_pool = [
        [0.0, 0.0, 0.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 5.0, 1.0],
        [2.0, 2.0, 2.0, 6.0, 1.0]
    ]

    print("=== NEAREST ===")
    print(json.dumps(
        nearest([1.0, 1.0, 1.0, 5.0, 1.0], memory_pool),
        ensure_ascii=False,
        indent=2
    ))

    print("=== HAZARD CHECK ===")
    print(json.dumps(
        hazard_check([10.0, 10.0, 10.0, 50.0, 1.0], memory_pool),
        ensure_ascii=False,
        indent=2
    ))
