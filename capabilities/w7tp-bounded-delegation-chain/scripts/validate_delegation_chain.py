#!/usr/bin/env python3
import argparse, datetime as dt, json
from pathlib import Path

def subset(child, parent, key):
    return set(child.get(key, [])) <= set(parent.get(key, []))

def parse_time(v):
    return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))

def main():
    ap = argparse.ArgumentParser(description="Validate structural attenuation of a W7TP delegation chain.")
    ap.add_argument("chain")
    args = ap.parse_args()
    doc = json.loads(Path(args.chain).read_text(encoding="utf-8"))
    grants = doc.get("grants") or []
    if not grants:
        raise SystemExit("STATE=FAIL_NO_GRANTS")
    root = grants[0]
    if root.get("parent_grant_id") is not None or not root.get("founder_grant_ref"):
        raise SystemExit("STATE=FAIL_ROOT_FOUNDER_GRANT_REF_REQUIRED")

    by_id = {}
    for g in grants:
        gid = g.get("grant_id")
        if not gid or gid in by_id:
            raise SystemExit("STATE=FAIL_GRANT_ID")
        by_id[gid] = g

    for g in grants[1:]:
        pid = g.get("parent_grant_id")
        if pid not in by_id:
            raise SystemExit(f"STATE=FAIL_PARENT_MISSING:{pid}")
        p = by_id[pid]
        if not p.get("delegation_allowed", False):
            raise SystemExit(f"STATE=FAIL_PARENT_DELEGATION_DISABLED:{pid}")
        for key in ("capabilities", "targets", "purposes", "effect_classes"):
            if not subset(g, p, key):
                raise SystemExit(f"STATE=FAIL_PRIVILEGE_EXPANSION:{g['grant_id']}:{key}")
        if parse_time(g["valid_from"]) < parse_time(p["valid_from"]):
            raise SystemExit(f"STATE=FAIL_VALIDITY_EXPANSION:{g['grant_id']}")
        if parse_time(g["expires_at"]) > parse_time(p["expires_at"]):
            raise SystemExit(f"STATE=FAIL_EXPIRY_EXPANSION:{g['grant_id']}")

    print("STATE=PASS_BOUNDED_DELEGATION_CHAIN")
    print(f"GRANT_COUNT={len(grants)}")
    print("AUTHENTICITY_PROVEN=false")

if __name__ == "__main__":
    main()
