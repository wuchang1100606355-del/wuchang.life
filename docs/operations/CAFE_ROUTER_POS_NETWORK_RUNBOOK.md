# Cafe Router POS Network Runbook

STATE=CAFE_ROUTER_POS_NETWORK_RUNBOOK_READY
RUN_ID=ROUTER_TOTAL_FIELD_GOVERNANCE_SPEC

## First Response

When POS, Odoo, domain, Wi-Fi, or cashier network fails:

1. observe the field
2. ask Total Field
3. compare with reports/seals
4. produce the smallest safe path
5. run D8 preflight
6. execute only after gate and approval

## Read-Only Checks

Use read-only checks first:

```bash
pwd
git status --short
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh alerts --limit 20
curl -sS -I --max-time 5 http://127.0.0.1:8069/web || true
curl -sS -I --max-time 5 http://127.0.0.1:8069/pos/ui || true
getent hosts pos.wuchang.life || true
ss -ltnp || true
```

Do not read `.env` or router passwords.

## Human Router Checklist

Only after approval, the human operator may open the router UI and confirm:

- WAN online
- LAN gateway online
- POS/Odoo host IP
- staff Wi-Fi enabled
- guest Wi-Fi isolated
- no direct WAN exposure of SSH/PostgreSQL/Docker/Odoo admin
- no unknown port forward
- rollback screenshot captured

The operator must not paste router credentials into chat or reports.

## Store Operation Priorities

| Priority | Goal | Action Type |
|---|---|---|
| P0 | cashier can sell and take cash | local POS/Odoo reachability |
| P1 | manager can approve changes | staff network and login route |
| P2 | customer network isolated | guest Wi-Fi/VLAN policy |
| P3 | public domain stable | reverse proxy / DNS route after approval |
| P4 | evidence sealed | report and status seal |

## Emergency Boundaries

If a router problem blocks store cash flow, the agent may propose emergency containment, but must still stop before router login, router write, DNS write, reboot, or deploy unless the human explicitly approves that exact action.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ROUTER_SECRET_READ=FALSE
ROUTER_WRITE=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
