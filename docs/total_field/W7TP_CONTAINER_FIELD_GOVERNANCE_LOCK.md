# W7TP Container Field Governance Lock

STATE=CONTAINER_FIELD_GOVERNANCE_LOCK
AUTHORITY=TOTAL_FIELD
DELETE=NO
RESTORE=NO
WEB_TOUCH=NO

## Core Rule

All executable service fields should be container-governed.

Authority, identity, packets, state indexes, and evidence must not be trapped inside container lifecycle.

## Layer Split

| Layer | Containerized | Rule |
|---|---:|---|
| Odoo / POS / Cafe Gateway | YES | service container |
| LINE / webhook / API gateway | YES | edge service container |
| AI candidate lane | YES | candidate compute container |
| Verifier / redteam / gate | YES or sidecar | executable verifier; rules externalized |
| D8 DB / PostgreSQL | YES | DB container with persistent volume |
| 8D+7D packet | NO | state envelope / governance contract |
| ADI 5D | NO | absolute index / authority reference |
| Total Field authority | NO | final decision chain, not container-owned |
| Member / merchant / organization | NO | identity and state subject |
| Runtime evidence | NO | external mounted volume / archive |
| VPN / Tailscale | HOST or SIDECAR | private transport layer |

## Hard Boundary

Container = execution carrier  
Volume = persistence  
8D+7D = state packet and governance contract  
ADI 5D = absolute index  
Total Field = final authority  

## Required Deployment Principle

Executable services may be replaced, restarted, or moved.

Authority records, ADI references, 8D+7D packets, verifier rules, member consent, and evidence must remain reconstructable outside the service container.

## Forbidden

- one member = one long-running container
- one merchant = production container without Total Field approval
- storing authority only inside container filesystem
- treating cloud sync as generative transmission
- treating file transfer as state reconstruction
- deploying container from candidate packet without verifier PASS

## Final Lock

Services are containerized.
Authority is externalized.
Data is persisted.
Packets are reconstructable.
Total Field is not container-owned.
