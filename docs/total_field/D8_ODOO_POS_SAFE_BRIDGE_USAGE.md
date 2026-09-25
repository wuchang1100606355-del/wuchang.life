# D8 Odoo POS Safe Bridge Usage

The safe bridge creates a read-only Odoo/POS readiness manifest for D8.

Run:

```bash
python tools/d8_odoo_pos_safe_bridge.py --dry-run
```

Rules:

- Read-only manifest only
- No Odoo DB writes
- No POS DB writes
- No orders
- No payments
- No member plaintext reads
- No service restarts
- No deploys
- No external API calls

The bridge may check container presence and hash explicitly allowed non-secret files for integrity. It must not modify Odoo addons, LINE login files, compose files, or production services.
