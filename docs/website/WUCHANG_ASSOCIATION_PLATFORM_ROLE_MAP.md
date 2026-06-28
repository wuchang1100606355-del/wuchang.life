# Wuchang Association Platform Role Map

STATE=WUCHANG_ASSOCIATION_PLATFORM_ROLE_MAP_READY
CHECK_DATE=2026-06-27

## Purpose

This file records the Total Field interpretation of each public website platform. The homepage is an association vision page first; it then routes users into the correct operational platform without exposing member plaintext, secrets, payment data, or Odoo private records.

## Platform Role Table

| Platform | Total Field role | Current route | Repo evidence | XiaoJ allowed work | Hard boundary |
| --- | --- | --- | --- | --- | --- |
| 協會願景形象首頁 | Public trust, association identity, service routing, safety promise | `web/index.html` | `docs/legal/ASSOCIATION_BYLAW_AND_COMMUNITY_DEVELOPMENT_AUTHORITY.md`, `docs/system_memory/wuchang_culture_kindness_memory.md` | Explain public services and route users to the right platform | No member plaintext, no secret, no payment data, no backend operation |
| 商業聯合銷售平台 | Local merchant sales, POS/shop entry, service products, welfare return flow | `/shop` | `docs/strategy/wuchang_sovereign_economic_engine_v8_zh.md`, `Taiji_Odoo/addons/wuchang_core/models/pos_config_ext.py` | Candidate product lookup, cart draft, voucher explanation | No silent order, no POS write, no payment capture |
| 物業管理平台 | Resident service, announcement, repair, parcel, committee coordination, management fee payment intent | `/web` | `Taiji_Odoo/addons/wuchang_core/models/property_management.py`, `tools/member_browser/xiaoj_member_browser_1b_controller.py` | Masked resident/owner function routing and payment intent candidate | No Odoo write, no member plaintext read, no payment capture |
| 會員登入平台 | Admission, consent, 8D member_ref, XiaoJ entry, OAuth/BYOK ref connection | `/google/member/login` | `Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py`, `docs/evidence/GROUP_MEMBER_8D_REGISTRATION.md` | Consent summary, member_ref status, API/OAuth ref explanation | Raw API key, OAuth token, cookie, password, phone, address, ID never enter prompt |
| 社區許願樹平台 | Wish cards, public welfare review, approved target support, wish coin ledger | `/web` | `Taiji_Odoo/addons/wuchang_wish_tree_coin/models/wuchang_wish_tree_coin.py`, `docs/system_memory/wuchang_culture_kindness_memory.md` | Wish draft, review checklist, public summary | No sensitive proposer data, no unaudited private transfer |
| 社區幣/票券兌換平台 | Happiness coin, tickets, quota buckets, redemption, expiration, write-off, correction | `/wuchang/tickets` | `Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_ticket_opening.py`, `Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_ticket_quota_buckets.py`, `docs/strategy/wuchang_sovereign_economic_engine_v8_zh.md` | Explain voucher state, prepare redemption candidate, show non-financial boundary | No cash-out promise, no investment wording, no unverified accounting write |
| 社區活動平台 | Event notice, RSVP, volunteer signup, attendance evidence, reminders | `/web` | `web/community_activities.json`, `Taiji_Odoo/addons/wuchang_core/models/jf_gateway.py`, `Taiji_Odoo/addons/wuchang_core/models/volunteer.py`, `Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py` | Activity summary, RSVP candidate, volunteer signup draft, reminder draft | No raw contact data to cloud, no auto enrollment, no raw audio collection |

## Public Activity Seed

Current public activity seed:

- `activity_ref:wuchang_park_hot_dance_weekday_2000`
- Title: 五常公園熱舞社運動社團
- Time: 每週一至週五 20:00-21:00
- Place: 五常公園
- Audience: 社區婦女
- Source file: `web/community_activities.json`

XiaoJ may answer or summarize this public seed through `public_activity_cache_ref:web/community_activities.json`. If a member asks to join, register, or RSVP, XiaoJ must emit a candidate `write_draft_ref` with `transaction_intent=activity_rsvp_candidate`; it must not auto-enroll, expose raw contact data, or send private participation data to cloud.

## XiaoJ 8D Routing Implication

Every platform entry should be converted to a ref-only 8D packet before AI handling:

- `member_ref`
- `platform_ref`
- `odoo_role_ref`
- `odoo_function_item_refs`
- `consent_scope_ref`
- `allowed_actions`
- `forbidden_actions`
- `candidate_only=true`
- `requires_total_field_verify=true`
- `member_plaintext_transferred=false`

## Public Page Copy Boundary

Allowed on the public page:

- Public platform names.
- Public route names.
- Safety posture and no-plaintext rules.
- Association-level purpose.
- Ref-only technical posture.

Forbidden on the public page:

- Full name, phone, address, ID number.
- Raw API key, OAuth token, cookie, password, localStorage.
- Raw payment data or bank/card data.
- Raw audio or private document full text.
- Odoo member plaintext or private governance chain.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_API_KEY_OUTPUT=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
DEPLOY=FALSE
