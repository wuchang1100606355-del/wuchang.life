# WISH TREE COMMUNITY DESIGN UPDATE

STATE: COMMUNITY_DESIGN_UPDATED
LIVE_STATUS: NOT_PRODUCTION
SIDECAR_STATUS: ENABLED_FOR_DRY_RUN

## Business Role

Wish Tree is the community wish realization layer.

It receives resident wishes, routes them through review, checks the dedicated Wish Tree budget, and dispatches approved cases to volunteers or community service teams.

## Fund Logic

Wish Tree is mapped as a public affairs allocation item.

Design ratio:
- system operating cost
- volunteer operation
- wish tree allocation
- flexible / sustainability fund

## Runtime Boundary

Odoo/Postgres remains the source of truth.

ADI sidecar does not replace Odoo/Postgres.
ADI sidecar indexes event references, hashes, causal chain, and verifier state only.

## Current Live Boundary

Installed:
- wuchang_core
- wuchang_pos_topology
- wuchang_member_registration

Repo-level only:
- wuchang_wish_tree_coin

Blocked:
- wuchang_fund_allocation
- blocker: missing wuchang_fund_reserve

## Integration Decision

WISH_TREE_DESIGN = THAWED
WISH_TREE_LIVE_DB = HOLD
ADI_SIDECAR = DRY_RUN_READY
PRODUCTION_LAUNCH = HOLD
