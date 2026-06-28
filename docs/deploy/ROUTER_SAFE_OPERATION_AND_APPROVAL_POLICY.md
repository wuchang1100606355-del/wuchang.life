# Router Safe Operation and Approval Policy

STATE=ROUTER_SAFE_OPERATION_POLICY_DEFINED
RUN_ID=ROUTER_TOTAL_FIELD_GOVERNANCE_SPEC

## Policy

Router work is split into observation, proposal, supervised execution, and evidence. Total Field may prepare and verify the route, but router mutation requires an explicit human release.

## Always Allowed Without Router Login

- `ping` or HTTP reachability checks against local services
- local port status checks
- DNS lookup
- reverse-proxy existence checks
- report and seal review
- comparison against prior approved policy
- generating human checklist and rollback plan

## Requires Human Approval

- router login
- port-forward change
- DNS/DDNS target change
- Wi-Fi SSID/password change
- VLAN or guest isolation change
- DHCP reservation change
- firewall rule change
- router reboot
- firmware update
- enabling remote admin

## Never Allowed By Default

- store router password in repo, D8 DB, report, seal, CSV, screenshot, or chat
- expose SSH, PostgreSQL, Docker, Odoo admin, member vault, key broker, or raw internal ports directly to WAN
- use Cloudflare or DNS provider API token without a separate secret-safe packet
- open public admin surfaces for convenience
- use LINE, Wi-Fi presence, or device presence as sole identity authority

## Router Change Packet Minimum

A future router mutation packet must include:

- task name
- observed state
- target state
- allowed paths
- forbidden paths
- exact setting names
- rollback steps
- human approval statement
- secret handling statement
- preflight result
- post-change verification
- report path
- seal path

## DNS Note

The existing DNS manual policy remains binding. DNS changes for `wuchang.life` are manual-review work unless a new explicit packet authorizes a secret-safe provider workflow.

## Service Continuity Rule

Store operation priority:

1. keep cafe POS reachable on the local network
2. keep Odoo reachable for cashier login
3. preserve cash collection
4. isolate guest/customer network from POS/Odoo
5. avoid WAN exposure of internal services

## Final Gate

```text
ROUTER_LOGIN=HOLD_HUMAN_APPROVAL_REQUIRED
ROUTER_WRITE=HOLD_HUMAN_APPROVAL_REQUIRED
ROUTER_REBOOT=HOLD_HUMAN_APPROVAL_REQUIRED
DNS_WRITE=HOLD_HUMAN_APPROVAL_REQUIRED
SECRET_READ=BLOCK
```
