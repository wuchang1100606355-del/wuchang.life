#!/usr/bin/env python3
"""
W7TP Local Verifier
Intercepts cloud compute candidates via stdin, enforces JSON Delta schema,
and routes to PASS or HOLD state.
"""
import sys
import json

def verify_payload():
    print("STATE=VERIFIER_START")
    try:
        payload = sys.stdin.read().strip()
        if not payload:
            print("STATE=HOLD_EMPTY_PAYLOAD")
            sys.exit(1)

        data = json.loads(payload)

        # 1. Strict Schema Enforcement
        required_keys = {"patch_type", "file_ref", "content_delta"}
        actual_keys = set(data.keys())
        
        if not required_keys.issubset(actual_keys):
            print("STATE=HOLD_SCHEMA_VIOLATION_MISSING_KEYS")
            sys.exit(2)
            
        if len(actual_keys) > len(required_keys):
            print("STATE=HOLD_SCHEMA_VIOLATION_EXTRA_PROPERTIES")
            sys.exit(3)

        # 2. Static Security & Hallucination Check
        delta = data.get("content_delta", "")
        # Basic heuristic to prevent obvious execution escape attempts
        banned_terms = ["os.system", "subprocess.", "eval(", "exec(", "rm -rf"]
        for term in banned_terms:
            if term in delta:
                print(f"STATE=HOLD_SECURITY_VIOLATION_BANNED_TERM")
                sys.exit(4)

        # 3. Success Routing
        print("STATE=PASS_VERIFIED_CANDIDATE_READY_FOR_LAND")
        sys.exit(0)

    except json.JSONDecodeError:
        print("STATE=HOLD_INVALID_JSON_FORMAT")
        sys.exit(5)
    except Exception as e:
        print("STATE=HOLD_VERIFIER_UNEXPECTED_EXCEPTION")
        sys.exit(6)

if __name__ == "__main__":
    verify_payload()
