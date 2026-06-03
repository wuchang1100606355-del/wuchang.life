# W7TP Indexer Server Deployment Checklist

Status: `plan-only`

This checklist prepares a future human-reviewed deployment of the
`wuchang_indexer_oneshot` job on a pure Linux server. It authorizes no SSH,
no transfer, and no container start.

## Server Prerequisite Checklist

- [ ] Confirm the target host is an explicitly reviewed `pure_linux_server`.
- [ ] Confirm an accountable human reviewer and operator are recorded.
- [ ] Confirm host resource limits, storage capacity, and result retention plan.
- [ ] Confirm the task remains one-shot only or separately approved scheduled execution.

## Docker / Compose Prerequisite

- [ ] Review the compose template as configuration only, before any real execution.
- [ ] Confirm the reviewed image identifier is `w7tp-indexer:latest`.
- [ ] Confirm `restart: "no"` remains unchanged.
- [ ] Confirm `network_mode: "none"` remains unchanged, unless a minimal network exception is explicitly documented and approved by a human reviewer.
- [ ] Confirm the runtime would remain read-only except for reviewed result/proof output paths.

## Directory Prerequisite

- [ ] Create no server path through this document; proposed paths must be reviewed separately.
- [ ] Permit only a read-only project snapshot, read-only job manifest, and reviewed writable output/proof locations.
- [ ] Reject root filesystem mounts and any unreviewed path mapping.

## Hardwall Rules

- [ ] No secrets: do not provide `.env`, credentials, passwords, tokens, keys, or private keys.
- [ ] No raw member data: do not provide source data containing raw member PII.
- [ ] No router access: this package does not authorize router or Merlin access.
- [ ] No formal DB write: do not write to formal Odoo or Postgres data stores.
- [ ] No SSH, no server transfer, and no automated container execution.

## Human Review Gate

- [ ] Confirm all artifacts and SHA256 evidence are listed before real server execution.
- [ ] Confirm the server path mapping and dry-run record have separate human approval.
- [ ] Record the reviewer decision before any future execution task is opened.

## Rollback / Abort Criteria

Abort preparation and return to `pending_human_review` if any of the following occurs:

- `restart: "no"` is removed or changed.
- Network access exceeds `network_mode: "none"` without documented minimal-network approval.
- A secret, raw member data source, router operation, or formal database write is requested.
- A root or forbidden path mount is proposed.
- Human review, proof collection, or accountability records are incomplete.
