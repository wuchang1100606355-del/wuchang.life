# W3 Generative Transfer Deploy

RUN_ID=W3_GENERATIVE_TRANSFER_DEPLOY_20260621
STATE=W3_GENERATIVE_TRANSFER_DEPLOY_INDEXABLE

## Safe Mode
- runtime_change=false
- service_restart=false
- odoo_db_write=false
- tailscale_change=false
- lineworks_send=false
- chrome_display_control=false
- secret_read=false
- raw_pii_read=false

## Purpose
Create the first indexed W3 package for candidate-only generative transfer in the Chongxin store dual-node POS maintenance system.

## Main Chain
State -> Coordinate -> Hash -> Packet -> Generative Transfer -> Verify -> Reconstruct -> Evidence -> Action

## Indexed Capability
- Cloud or LLM workers may return candidate results only.
- Local GT8D lookup remains route authority.
- Local reconstruction is required before any action can land.
- Total Field review and human final authorization are required for high-risk runtime action.
- Product-market demo requires the POS market competitiveness gate before any commercial claim.
- Cloud compute may be triggered only as redacted candidate labor: no authority, no memory benefit, no data benefit, no Land.
- User stance integrity requires readonly Total Field discovery, fact labels, and one unified question queue for missing information.

## Dual Node Boundary
- NODE_POS_MAINT: POS maintenance candidate node.
- NODE_XIAOJ_DISPLAY_COMPUTE: Linux compute node, Chrome customer display, external TV XiaoJ image display.
- Tailscale invite links are access-bearing secrets and must not be stored in this package.

## Claim Labels
- FACT: local GT8D lookup is the routing authority for configured routes.
- FACT: generated artifacts in this package are evidence/spec/dry-run only.
- NOT_YET_VERIFIED: live Odoo POS state, POS ID 3/4 collision resolution, current device binding.
- DESIGN_PROPOSAL: 64-gua bitmask, five-element tensor, Hetu-Luoshu engineering mapping.

## Stopline
If a requested next step requires DB write, Odoo write, LINE WORKS send, service restart, Tailscale change, or live Chrome control, output:

STATE=HOLD_REQUIRES_STAGE_2_OR_3_REVIEW

If product copy or demo claims direct POS/DB/LINE WORKS/payment action, or claims unverified 64-gua implementation as fact, output:

STATE=HOLD_PRODUCT_MARKET_OVERCLAIM

If a cloud compute lane requests secrets, member plaintext, token printing, API enablement, memory/data benefit, or final Land authority, output:

STATE=HOLD_CLOUD_COMPUTE_BOUNDARY

If a plan invents facts, skips Total Field discovery, omits FACT/INFERENCE/DESIGN_PROPOSAL/NOT_YET_VERIFIED/INFO_REQUIRED labels, or scatters unresolved questions, output:

STATE=HOLD_USER_STANCE_INTEGRITY
