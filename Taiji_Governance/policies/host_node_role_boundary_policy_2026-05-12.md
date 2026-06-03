# Host Node Role Boundary Policy

Version: 2026-05-12  
Status: ACTIVE

## Core Rule

MSI and taiji01 are separate host nodes.

They may run the same container stack names, but they are not the same Docker daemon unless Docker context / DOCKER_HOST explicitly points to the same daemon.

## Node Roles

### MSI

Role:

- wuchang.life representative node
- association portable representative node
- local development and test node
- Odoo / POS / AI window validation node
- may be shut down after service handoff or local-only shutdown

Authority:

- operated by taiji_admin
- may perform development, validation, local Odoo test writes, runtime testing
- must not be assumed to provide 24/7 community service

### taiji01

Role:

- community resident edge node
- deployment node
- non-container community workspace node
- optional production / service node depending on active service status

Authority:

- taiji_admin owns full write / sudo / docker / production maintenance authority
- taiji_01 may write only governed non-container community workspace
- taiji_01 should not directly control Docker or production DB if hard separation is required

## Account Model

taiji_admin:

- full write owner
- system maintenance account
- docker / sudo authority holder
- production change window executor

taiji_01:

- community operator account
- non-container community workspace writer
- not the complete-write authority
- should not bypass taiji_admin for container / DB mutation

## Shutdown Rule

MSI may be shut down because it is a portable representative / development node.

taiji01 should not be shut down if it is serving community workloads unless:

1. service is stopped,
2. service is transferred,
3. service is intentionally degraded,
4. shutdown is logged.

## Security Interpretation

Same accountable natural person reduces internal adversarial risk.

It does not eliminate:

- external intrusion risk
- device loss risk
- malware risk
- secret leakage risk
- sync pollution risk
- production wrong-write risk
- subject/entity merge risk

## Hard Boundary

Same person does not mean same legal subject.

Same stack names do not mean same Docker daemon.

Same device may have multiple roles, but every role must remain auditable.
