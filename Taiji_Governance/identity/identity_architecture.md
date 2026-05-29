# Taiji Multi-Governance Identity Architecture

Status: governance architecture, non-secret  
Principle: the owner is not represented as a single super-admin identity.

## Core Model

The human authority is represented as a Multi-Governance Identity Holder. Each identity has its own governance window, authority vector, audit boundary, legal/operational meaning, runtime permission scope, and separation requirement.

No identity may bypass Five Metric Governance, Replay Governance, Tensor Deadbox, Human Decision Boundary, Audit Runtime, or Plaintext-Free Context Policy.

## Primary Identities

| Identity | Chinese | Primary window | Core boundary |
| --- | --- | --- | --- |
| Runtime Owner | Runtime 擁有者 | governance | cannot erase audit or silently alter locked metric law |
| System Architect | 系統架構師 | design/development | must produce dry-run, rollback, and no production deployment without approval |
| Community Governor | 公益治理者 / 社區治理者 | public-interest governance | cannot privatize public-interest assets |
| Technology Sponsor | 技術捐贈者 / 技術支援者 | technology transfer | donation/support does not create control over public-interest assets |
| Runtime Operator | Runtime 維運者 | maintenance/recovery | cannot issue credentials or approve payment |
| Private Commercial Operator | 私人商業營運者 | commercial operation | must separate private store data/assets from community governance |
| Community Industry Operator | 社區產業營運者 | community industry | must preserve accounting, Odoo, and audit separation |

## Governance Rule

Authority is routed by `IdentityTensorState`, not by a single all-powerful account label.
