# M005 Runtime Scope Decision

Total runtime/services candidate files were too large for one commit.

Excluded from M005A:
- runtime/archive/
- runtime/build/
- runtime/cache/
- runtime/state/
- runtime/ledger/
- runtime/memos/
- __pycache__
- copied Odoo build artifacts
- generated runtime output

Reason:
- Avoid duplicate Odoo code already covered by M004A.
- Avoid committing runtime state/cache/ledger/memo outputs.
- Avoid old archived variants before redaction review.

M005A will include runtime safe control-plane files only.
