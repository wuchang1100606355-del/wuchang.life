#!/usr/bin/env python3
"""
W7TP Evidence Ledger Logger
Appends state transitions and payload hashes to an immutable append-only ledger.
"""
import sys
import json
import hashlib
import time
from pathlib import Path

LEDGER_FILE = Path("logs/evidence_ledger.jsonl")

def log_evidence(state, source, payload=""):
    payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest() if payload else "NO_PAYLOAD"
    
    entry = {
        "timestamp": time.time(),
        "state": state,
        "source": source,
        "payload_hash": payload_hash
    }
    
    with LEDGER_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        
    print(f"STATE=PASS_EVIDENCE_LOGGED payload_hash={payload_hash}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("STATE=HOLD_EVIDENCE_LOGGER_MISSING_ARGS")
        sys.exit(1)
        
    state_arg = sys.argv[1]
    source_arg = sys.argv[2]
    payload_arg = sys.argv[3] if len(sys.argv) > 3 else ""
    
    log_evidence(state_arg, source_arg, payload_arg)
