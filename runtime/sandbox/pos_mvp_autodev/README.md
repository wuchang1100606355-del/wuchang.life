# POS MVP Sandbox Autodev

STATE=SANDBOX_ONLY

FACT: This sandbox uses repo-local Odoo XML menu evidence to generate `menu/menu.json`.

FACT: This sandbox writes only under `runtime/sandbox/pos_mvp_autodev`, `docs/evidence/pos_mvp`, and `packets/pos_mvp`.

FACT: It does not deploy, restart services, write databases, mutate Odoo core, send production LINE/LINE WORKS, or call Google production actions.

Run:

```bash
python3 scripts/pos_mvp/run_pos_mvp_sandbox.py demo
bash scripts/verify/verify_pos_mvp_sandbox.sh
```
