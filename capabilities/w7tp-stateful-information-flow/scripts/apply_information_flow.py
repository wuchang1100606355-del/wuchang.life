#!/usr/bin/env python3
import argparse, json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="Apply a declared W7TP information-flow policy.")
    ap.add_argument("input")
    args = ap.parse_args()
    d = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rank = d.get("label_rank") or {}
    if not rank:
        raise SystemExit("STATE=FAIL_LABEL_RANK_REQUIRED")

    labels = sorted(set(d.get("current_labels", [])) | set(d.get("incoming_labels", [])))
    unknown = [x for x in labels if x not in rank]
    if unknown:
        raise SystemExit("STATE=FAIL_UNKNOWN_LABEL:" + ",".join(unknown))
    dest = d.get("destination_max_label")
    if dest not in rank:
        raise SystemExit("STATE=FAIL_DESTINATION_LABEL")

    max_rank = max([rank[x] for x in labels], default=0)
    if max_rank <= rank[dest]:
        decision, out_labels = "ALLOW", labels
    elif d.get("declassification_authorized"):
        out_labels = d.get("declassified_output_labels") or []
        if any(x not in rank for x in out_labels) or max([rank[x] for x in out_labels], default=0) > rank[dest]:
            raise SystemExit("STATE=FAIL_INVALID_DECLASSIFICATION_OUTPUT")
        decision = "ALLOW_WITH_DECLARED_DECLASSIFICATION"
    elif d.get("redaction_available"):
        out_labels = d.get("redaction_output_labels") or []
        if any(x not in rank for x in out_labels) or max([rank[x] for x in out_labels], default=0) > rank[dest]:
            print("DECISION=DENY")
            print("REASON=REDACTION_INSUFFICIENT")
            return
        decision = "ALLOW_WITH_REDACTION"
    else:
        decision, out_labels = "DENY", labels

    print(f"DECISION={decision}")
    print("NEXT_LABELS=" + ",".join(out_labels))
    print("D8_AUTHORITY_CREATED=false")

if __name__ == "__main__":
    main()
