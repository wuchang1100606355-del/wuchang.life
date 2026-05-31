# M009 Git Baseline Master Index

## Completed Baselines

- M001 Sub-Universe Governance Foundation
- M002 W7TP Atlas Universe Baseline
- M003A Patent Core Universe Baseline
- M003B Secret Redaction Policy
- M003C Cloud Drive Evidence Index and Download Policy
- M003D Cloud Taiji Architecture Evidence Index Batch 001
- M004A Odoo Safe Core Universe Baseline
- M004B Odoo Risk Module Index
- M005A Runtime Code Core Universe Baseline
- M005B Runtime Generated / State Exclusion Index
- M006A Boot / Systemd / Scripts Safe Core Baseline
- M006B Scripts Risk Index
- M007A Tests / Validation Safe Core Baseline
- M007B Runtime Reports Evidence Index
- M008 Git Bundle Cold Backup

## System Coverage

This Git baseline now covers:

- governance and memory gate
- sub-universe registry and Atlas field model
- patent core and evidence chain
- cloud-drive evidence indexing policy
- Odoo safe implementation core
- Odoo risk modules index
- runtime code core
- runtime generated-state exclusion rules
- boot/systemd/scripts safe core
- scripts risk index
- tests and validation core
- runtime reports evidence index
- D-drive removable cold backup bundle record

## Explicitly Not Included

- raw secrets
- service account JSON
- API keys
- OAuth tokens
- raw private keys
- cookies / sessions
- raw runtime outbox
- raw runtime state/cache/ledger/memos
- raw Drive dump
- raw .git folders
- Odoo high-risk credential/OAuth files before review
- backup copies and generated artifacts

## Current Strategy

Source and governance files are tracked in Git.
Generated state, historical outputs, risky credential surfaces, and raw evidence dumps are indexed first and committed only after redaction/review.

## Next Possible Milestones

- M010 Git status cleanup policy
- M011 .gitignore refinement
- M012 selected high-risk file redaction templates
- M013 release manifest
- M014 patent filing package sync
