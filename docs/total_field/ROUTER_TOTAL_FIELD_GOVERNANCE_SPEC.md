# Router Total Field Governance Spec

STATE=ROUTER_TOTAL_FIELD_GOVERNANCE_SPEC_DEFINED
RUN_ID=ROUTER_TOTAL_FIELD_GOVERNANCE_SPEC
ROOT=/home/taiji_admin/Taiji_Hub

## Purpose

Total Field may govern router intent, network health, approval rules, and evidence. It must not become a silent router administrator.

The router is a hardware boundary node for the cafe, POS, Odoo, VPN, and association workloads. It may be represented in Total Field as a governed coordinate, but credentials and direct mutation authority remain outside D8 memory and reports.

## Current Field References

Existing repository evidence names the local network profile as:

- ISP: Chunghwa Telecom fixed public IP network
- Router/Gateway: ASUSWRT
- Hardware example: ASUS RT-BE86U
- VPN node: taiji01 / subnet-router

These facts are infrastructure references, not permission grants.

## Governance Levels

| Level | Name | Allowed |
|---|---|---|
| L0 | observe | WAN/LAN/POS reachability checks, DNS lookup, port status, seal review |
| L1 | propose | generate router setting proposal, rollback plan, human checklist |
| L2 | supervised apply | human-approved router change with human entering credentials |
| L3 | emergency containment | human-approved containment for external exposure or POS outage |
| BLOCK | forbidden | secret capture, silent router login, unmanaged port exposure |

## Router-Control Boundary

Allowed by Total Field:

- describe desired DNS / port-forward / VLAN / Wi-Fi / guest-network state
- compare observed state to approved policy
- generate one-paste human checklist
- record redacted evidence and router setting fingerprints
- require approval before mutation

Forbidden by Total Field:

- read router password
- store router password
- print router password
- silently log into router admin
- call router admin API without a task packet and human approval
- reboot router without human approval
- expose Odoo, PostgreSQL, SSH, Docker, member vault, or key broker directly to WAN
- treat Wi-Fi presence as member identity

## Managed Objects

| Object | Governance Goal | Default Action |
|---|---|---|
| WAN | confirm internet/public route health | observe only |
| LAN | keep POS/Odoo/cashier devices reachable | observe only |
| Wi-Fi staff | role-bound store operations | proposal only |
| Wi-Fi guest | isolate customers from POS/Odoo | proposal only |
| DNS | manual review, no provider API automation | HOLD for human |
| port forward | expose only approved gateway/proxy | HOLD for human |
| DHCP reservation | keep POS/Odoo devices stable | proposal only |
| VPN/subnet route | private admin access path | proposal only |
| firmware update | router stability/security | HOLD for human |

## Router Packet Chain

```text
State
-> Coordinate
-> Hash
-> Packet
-> Generative Transfer
-> Verify
-> Reconstruct
-> Evidence
-> Action
```

Router actions must not skip field observation, Total Field consult, preflight, human approval, and rollback evidence.

## Safe Credential Pattern

Credentials stay with the human operator. A future XiaoJ browser-control flow may guide the operator through router UI steps, but it must not capture or retain password/token values.

Allowed evidence:

- router model
- firmware version
- redacted WAN status
- redacted LAN client count
- setting name
- intended value category
- screenshot hash
- operator confirmation
- rollback status

Forbidden evidence:

- router admin password
- ISP account password
- Wi-Fi password in plaintext
- private key
- provider token
- full external admin URL with embedded credential

## Default Decision

```text
STATE=ROUTER_TOTAL_FIELD_GOVERNANCE_READY
ROUTER_RUNTIME_WRITE=FALSE
ROUTER_SECRET_READ=FALSE
HUMAN_APPROVAL_REQUIRED_FOR_MUTATION=TRUE
```
