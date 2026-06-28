# Association Machine Upgrade and Sealed Migration Plan

STATE=SEALED_MIGRATION_REQUIRED
OWNER=五常社區發展協會
SOURCE=temporary cafe operation bridge
TARGET=future association-owned machine

## Purpose

This plan defines the future migration path from the current cafe-side temporary operation bridge to an association-owned machine and association-governed vault.

The current Odoo/POS/local/external-disk arrangement exists to restore cafe operations and cash flow. It must not become permanent custody of association member data.

## Migration Chain

```text
State
→ Coordinate
→ Hash
→ Packet
→ Verify
→ Reconstruct
→ Evidence
→ Action
```

## Target Architecture

| Workload | Temporary Location | Future Location |
|---|---|---|
| member vault | not cafe permanent storage | association-owned machine |
| local vault | temporary operation vault only | association local vault |
| governance reports | runtime evidence | association-governed backup |
| permission state | refs/status/TTL only | association governance workload |
| POS operation | cafe Odoo/POS | cafe operation only |

## Sealed Migration Requirements

Before migration:

- confirm association hardware owner and physical custody
- define encrypted storage path and backup path
- verify no member plaintext is exported to POS
- produce migration packet and hash manifest
- produce pre-migration report
- obtain human/association approval

During migration:

- transfer only approved references and governed vault payloads
- preserve hash/evidence chain
- avoid Odoo/POS member plaintext expansion
- keep cafe POS operational data separate from association member vault

After migration:

- verify association machine owns long-term vault workload
- confirm cafe machine no longer acts as final member vault
- seal migration report
- write Total Field status seal

## Stop Conditions

Stop if any of these occur:

- member plaintext is requested outside association rule
- Odoo/POS is proposed as permanent member custody
- external disk is proposed as permanent association infrastructure
- DNS/deploy/runtime work is mixed into this governance migration without a new packet

## Safety

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
PRODUCTION_DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
