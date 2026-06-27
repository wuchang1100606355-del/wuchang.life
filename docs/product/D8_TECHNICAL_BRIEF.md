# D8 Technical Brief

## Architecture

D8 DB -> RedTeam -> Possible Alerts -> Guard -> Preflight -> Task Capsule -> Writeback -> Recovery Seal -> Dashboard / Voice / POS Safe Bridge

## D8 Metadata

Each memory packet is indexed with:

- domain
- object_type
- source
- time_version
- actor_scope
- intent
- risk
- semantic_key

## Redteam Isolation

Redteam and possible-alert artifacts are constrained by:

- executable=false
- quarantine=true
- retrieval_scope=redteam_only
- pollution_guard=true
- reverse_index_only=true

They are evidence for guard decisions, not instructions to execute.

## Action Policy

- PASS: proceed
- INFO: proceed with informational note
- WARN: sandbox only, do not land without human release
- HOLD: stop and wait
- BLOCK: stop and block action

## Product Surface

The demo package exposes local-only operator surfaces:

- local dashboard on 127.0.0.1
- text-mode voice operator
- read-only Odoo/POS safe bridge
- smoke-test and package manifest launcher
