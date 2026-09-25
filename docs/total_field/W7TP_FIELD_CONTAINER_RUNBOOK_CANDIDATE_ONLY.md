# W7TP Field Container Runbook Candidate Only

STATE=FIELD_CONTAINER_RUNBOOK_CANDIDATE_ONLY
AUTHORITY=TOTAL_FIELD
MODE=CANDIDATE_ONLY
DELETE=NO
RESTORE=NO
WEB_TOUCH=NO
RUNTIME_BULK_OUTPUT=NO
DEPLOY=NO
RESTART=NO
DB_WRITE=NO
ROUTER_WRITE=NO

## Purpose

This runbook defines the forward-only container field path.

It does not deploy containers.
It does not restart services.
It does not write databases.
It does not create live URLs.
It does not create production routes.

## Execution Order

1. Private transport is prepared by host or sidecar.
2. Service fields are container-governed.
3. Persistent data is externalized into volumes or authority references.
4. 8D+7D packets define the state contract.
5. ADI 5D provides the absolute index reference.
6. Verifier / redteam / final_state_gate checks the candidate.
7. Total Field decides PASS / HOLD / BLOCK.
8. Owner/admin approval is required before production activation.

## Containerized Service Fields

- Odoo / POS
- Cafe Gateway
- LINE webhook gateway
- AI candidate lane
- verifier / redteam / gate sidecar
- OpenWebUI workbench
- D8 DB / PostgreSQL with persistent volume

## Externalized Authority Fields

- Total Field authority
- 8D+7D packets
- ADI 5D refs
- member identity
- merchant organization state
- consent records
- verifier rules
- evidence records

## Forbidden Runtime Actions

- docker compose up
- docker compose down
- docker compose restart
- docker system prune
- docker volume rm
- database migration
- router write
- live URL creation
- payment capture
- production activation

## Required Gate Before Deploy

- 8D+7D packet PASS
- ADI 5D ref PASS
- verifier PASS
- redteam PASS
- final_state_gate PASS
- Total Field PASS
- owner/admin approval

## Final Lock

Container is execution carrier.
Volume is persistence.
8D+7D is state contract.
ADI 5D is absolute index.
Total Field is final authority.
