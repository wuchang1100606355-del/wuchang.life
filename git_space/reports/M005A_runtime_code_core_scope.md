# M005A Runtime Code Core Scope

Purpose:
Commit only runtime code/control-plane source files.

Include:
- runtime/*.py
- runtime/*.sh
- runtime/*.yaml
- runtime/agents/
- runtime/bridges/
- runtime/core/
- runtime/dead_letter/
- runtime/dual_state/
- runtime/events/
- runtime/governance/
- runtime/hexagram/
- runtime/identity/
- runtime/memory/*.py
- runtime/openwebui_bridge.py

Exclude:
- runtime/archive/
- runtime/build/
- runtime/checkpoints/
- runtime/consensus/
- runtime/memory/conversations/
- runtime/memory/*.json
- runtime/memory_bus/
- runtime/metrics/
- runtime/mock/
- runtime/outbox/
- runtime/state/
- runtime/cache/
- runtime/ledger/
- runtime/memos/
- generated outputs
- copied Odoo artifacts
