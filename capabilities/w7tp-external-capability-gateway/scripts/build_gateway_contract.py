#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

REQUIRED = [
    "capability_id", "source_ref", "target_coordinate", "protocols",
    "input_contract", "output_contract", "state_transition", "side_effects",
    "failure_modes", "evidence_requirements",
]

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def main():
    ap = argparse.ArgumentParser(description="Build a W7TP-native external capability gateway contract.")
    ap.add_argument("input", help="Neutral capability input JSON")
    ap.add_argument("output", help="Output contract JSON")
    args = ap.parse_args()

    src = json.loads(Path(args.input).read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in src]
    if missing:
        raise SystemExit("MISSING_REQUIRED=" + ",".join(missing))

    out = dict(src)
    out["source_runtime_required"] = False
    out["source_authority_inherited"] = False
    out["w7tp_d8_authority_created"] = False
    out["contract_state"] = "W7TP_NATIVE_GATEWAY_CANDIDATE"
    out["contract_sha256"] = hashlib.sha256(canonical(out)).hexdigest()

    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("STATE=PASS_GATEWAY_CONTRACT_BUILT")
    print(f"OUTPUT={args.output}")
    print(f"CONTRACT_SHA256={out['contract_sha256']}")

if __name__ == "__main__":
    main()
