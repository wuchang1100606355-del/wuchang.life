#!/usr/bin/env python3
import argparse, json
from pathlib import Path

NO_D8 = {"READ_ONLY", "ISOLATED_CANDIDATE", "STATIC_ANALYSIS"}
REQUIRES_D8 = {
    "MUTATION", "DEPLOY", "ACTIVATION", "CANONICAL_CHANGE", "POINTER_CHANGE",
    "AUTHORITY_CHANGE", "CREDENTIAL_USE", "PROTECTED_DATA_DISCLOSURE",
    "EXTERNAL_MESSAGE", "MONEY_EFFECT",
}

def main():
    ap = argparse.ArgumentParser(description="Deterministic structural W7TP effect gate.")
    ap.add_argument("request")
    args = ap.parse_args()
    r = json.loads(Path(args.request).read_text(encoding="utf-8"))

    for k in ("request_id", "effect_class", "target", "exact_effect"):
        if not r.get(k):
            print("DECISION=HOLD_MISSING_FIELD")
            print(f"MISSING={k}")
            raise SystemExit(2)

    cls = str(r["effect_class"]).upper()
    if cls in NO_D8:
        print("DECISION=ALLOW_FAST_LANE")
        print("D8_REQUIRED=false")
        return

    if cls not in REQUIRES_D8:
        print("DECISION=HOLD_UNKNOWN_EFFECT_CLASS")
        raise SystemExit(2)

    a = r.get("d8_authorization") or {}
    checks = [
        a.get("status") == "VALID",
        a.get("target") == r["target"],
        a.get("exact_effect") == r["exact_effect"],
        bool(a.get("authorization_ref")),
    ]
    if not all(checks):
        print("DECISION=HOLD_EXACT_D8_AUTHORIZATION_REQUIRED")
        print("D8_REQUIRED=true")
        raise SystemExit(3)

    print("DECISION=ALLOW_EXECUTE")
    print("D8_REQUIRED=true")
    print(f"AUTHORIZATION_REF={a['authorization_ref']}")

if __name__ == "__main__":
    main()
