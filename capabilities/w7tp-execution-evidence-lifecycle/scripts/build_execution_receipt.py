#!/usr/bin/env python3
import argparse, hashlib, json, os
from pathlib import Path

REQUIRED = [
    "execution_id", "request_ref", "target", "exact_effect", "started_at", "ended_at",
    "outcome", "evidence_refs", "artifact_hashes", "authority_ref", "previous_receipt_hash",
]

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def main():
    ap = argparse.ArgumentParser(description="Build a W7TP execution evidence receipt.")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--ledger", help="Optional JSONL file to append the receipt to")
    args = ap.parse_args()
    d = json.loads(Path(args.input).read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        raise SystemExit("MISSING_REQUIRED=" + ",".join(missing))

    r = dict(d)
    r["receipt_state"] = "W7TP_EXECUTION_EVIDENCE"
    r["authority_created"] = False
    r.setdefault("canonical_changed", False)
    r["receipt_sha256"] = hashlib.sha256(canon(r)).hexdigest()

    Path(args.output).write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.ledger:
        line = json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        fd = os.open(args.ledger, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    print("STATE=PASS_EXECUTION_RECEIPT_BUILT")
    print(f"RECEIPT_SHA256={r['receipt_sha256']}")
    print(f"OUTPUT={args.output}")

if __name__ == "__main__":
    main()
