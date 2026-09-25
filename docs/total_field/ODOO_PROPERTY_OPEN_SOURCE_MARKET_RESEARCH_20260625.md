# Odoo Property Open Source Market Research

STATE=RESEARCH_COMPLETE
RUN_ID=ODOO_PROPERTY_SOVEREIGN_AI_SYSTEM_OPEN_SOURCE_MARKET_RESEARCH_20260625

## Purpose

Find usable Odoo/open-source property management references, then route them through W7TP / D8 Total Field to design a Wuchang-owned integrated property sovereign AI system.

This document is research and design only. It does not install modules, modify Odoo, write an Odoo database, restart services, deploy, or create payments.

## Verified Local Patent Basis

- Patent certificate: `runtime/evidence/patent/877-24-0046.UTW_證書.PDF`
- Approval disposition: `runtime/evidence/patent/877-24-0046.UTW-核准處分書.pdf`
- Chinese specification: `runtime/evidence/patent/877-24-0046.UTW-中文本.pdf`
- Utility model certificate number: `M663678`
- Application number: `113206785`
- Title: `整合式物業管理系統`
- Patent owners / creators: `江政隆、蔣明諺`
- Patent term: `2024-12-01` to `2034-06-25`

## External Module Shortlist

| Candidate | Source | License / version signal | Useful parts | Boundary |
| --- | --- | --- | --- | --- |
| OCA/pms | https://github.com/OCA/pms | AGPL-3.0 repository; Odoo Store listing says technical name `pms`, version 14.0 | Multi-property, multi-company, rooms inventory, reservations, check-in, reports, board services, rates/availability | More hotel/PMS oriented than Taiwan community property management; not a direct fit for committee governance or sovereign AI |
| OCA/vertical-realestate | https://github.com/OCA/vertical-realestate | AGPL-3.0; GitHub shows 18.0 branch but very small history | Real-estate business structure and OCA style reference | Sparse/early repository; use as reference only until module maturity is verified |
| Advanced Property Management | https://apps.odoo.com/apps/modules/17.0/advanced_property_management | LGPL-3; versions 15.0-19.0 on Odoo Apps | Property website, kanban/list, property brochure, auction/sale/rental, commission, auto rental invoice, map location, blacklist | Third-party app, commercial/vendor dependency risk; useful UX/model reference, not sovereign core |
| Odoo industry_real_estate | https://apps.odoo.com/apps/modules/19.0/industry_real_estate | OEEL-1, Odoo official industry package | Lease agreements, owner reports, facility management, rent collection, maintenance dispatch | Not open source; reference only |
| open-condo | https://github.com/open-condo-software/condo | MIT; non-Odoo property SaaS | Tickets, resident contacts, properties, payment tracking, invoices, service marketplace, mini-app extension model | Not Odoo; architectural inspiration for resident/service marketplace, not an install target |

## Total Field Findings

The local Total Field already contains stronger domain-specific material than a generic Odoo app:

- `docs/patent/taiwan_patent_claims_v1.md` includes property management, committee services, maintenance, emergency events, member governance, and Odoo/POS/ERP integration.
- `docs/patent/taiwan_patent_spec_v1.md` frames Odoo as an implementation carrier for POS, ERP, members, property management, and community services.
- `docs/wuchang_community_system_functional_structure_zh.md` defines Taiji Hub as a community management, AI POS, AI committee equipment management, Odoo governance runtime, topology, and audit platform.
- `docs/project/W7TP_ODOO_COMMITTEE_MODULE_READ.md` and related files show existing recovered/active module candidates around committee, property documents, property management, and AI property expert concepts.
- `docs/legal/ASSOCIATION_BYLAW_AND_COMMUNITY_DEVELOPMENT_AUTHORITY.md` supports public-info indexing for property-management and committee/forum purposes, subject to non-plaintext and review limits.

## Recommendation

Do not install a generic property module directly into the live Odoo as the product.

Use open-source modules as reference and build a Wuchang-owned layer:

1. Reference OCA/Odoo marketplace data models for property, unit, lease, maintenance, and resident workflows.
2. Reuse local Wuchang modules and recovered committee/property concepts where compatible.
3. Add D8/W7TP Total Field governance as the differentiator:
   - no member plaintext by default
   - candidate-only AI
   - verifier before action
   - 8D role/permission packets
   - committee/public-interest evidence trail
   - repair/maintenance/payment actions gated by human approval

## Safe Next Step

Create the Wuchang blueprint and implementation capsule before any code install:

- Base module: `wuchang_property_sovereign_base`
- Committee module: `wuchang_property_committee`
- Maintenance module: `wuchang_property_maintenance`
- Document/evidence module: `wuchang_property_evidence`
- AI candidate module: `wuchang_property_ai_candidate`
- Portal module: `wuchang_property_resident_portal`
- Integration bridge: `wuchang_property_odoo_bridge`

No production install until staging database, backup, module compatibility check, and human approval are complete.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
D8_LOCAL_DB_WRITE=TRUE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
EXTERNAL_API_CALL=TRUE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
