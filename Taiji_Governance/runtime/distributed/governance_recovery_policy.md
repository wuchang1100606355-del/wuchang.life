# Governance Recovery Policy

Recovery after laptop poweroff, node split, or stale topology requires:

1. read-only inventory
2. baseline hash comparison
3. replay index validation
4. audit continuity check
5. authority continuity check
6. topology verification
7. human decision for L2/L3

No distributed node may overwrite production runtime during recovery.
