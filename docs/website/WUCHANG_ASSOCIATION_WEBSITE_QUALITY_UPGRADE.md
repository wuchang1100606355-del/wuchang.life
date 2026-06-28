# Wuchang Association Website Quality Upgrade

STATE=WUCHANG_ASSOCIATION_WEBSITE_QUALITY_UPGRADE_READY
CHECK_DATE=2026-06-27

## Purpose

This package upgrades the association website from scattered demo pages into an association vision homepage that routes residents, members, merchants, property users, wish-tree participants, activity participants, cloud candidate tools, and Total Field review without exposing sensitive data.

## Official And Public Design Sources Checked

- W3C Web Content Accessibility Guidelines 2.2: https://www.w3.org/TR/WCAG22/
- web.dev Core Web Vitals: https://web.dev/articles/vitals
- U.S. Web Design System usability and accessibility guidance: https://designsystem.digital.gov/usability-accessibility/

## Integrated Website Entry

- `web/index.html`

The entry integrates:

- association vision identity.
- commercial joint sales route.
- property management route.
- Google member login route.
- community wish tree route.
- community coin / ticket exchange route.
- community activity route.
- XiaoJ member browser cockpit.
- ref-only XiaoJ and W7TP safety posture.
- no-plaintext, ref-only, verifier-gated safety posture.

## Website Quality Rules

### Accessibility

- Every page entry must keep `<html lang="zh-Hant">`.
- Every primary static page must have viewport metadata.
- Main entry must provide a skip link.
- Navigation must be semantic and keyboard reachable.
- Click targets must be at least 40px high for ordinary actions.
- Text must avoid overlap and must wrap inside cards on mobile.

### Performance

- Static pages should avoid external blocking assets for the first viewport.
- Homepage should not depend on third-party JavaScript.
- Cards and layout use CSS grid with stable dimensions to reduce layout shift.
- Heavy runtime surfaces such as Odoo, VRM, or cloud workbench remain linked, not embedded.

### Governance And Safety

- Public pages must not display raw API keys, OAuth tokens, cookies, localStorage, raw audio, member phone, address, ID number, payment data, or Odoo member plaintext.
- Payment support for resident management fees is expressed as `payment_intent_ref`, `payment_tool_ref`, `management_fee_bill_ref`, and `payment_amount_bucket_ref`.
- Payment capture remains outside XiaoJ and requires member confirmation plus formal payment/Odoo workflow.
- Cloud compute remains candidate-only.
- Odoo remains a business/runtime carrier; 8D packets remain the identity, permission, function, risk, and governance layer.

## Current Static Page Inventory

| Page | Role | Upgrade status |
| --- | --- | --- |
| `web/index.html` | Association service entry | upgraded |
| `web/xiaoj_member_browser_cockpit/index.html` | XiaoJ PWA cockpit | linked |
| `/shop` | Commercial joint sales / Odoo shop route | linked only |
| `/google/member/login` | Google member login route | linked only |
| `/web` | Odoo login route | linked only |
| `/wuchang/tickets` | Community coin / ticket exchange route | linked only |
| `web/community_activities.json` | Public community activity seed | public cache only |

## UX Information Architecture

1. Association vision image and public trust first.
2. Six platform routes: sales, property, member login, wish tree, coin/ticket exchange, activity.
3. XiaoJ sovereign AI as a member-side assistant, not the homepage subject.
4. Cloud candidate compute remains behind no-plaintext packets.
5. Total Field / 8D verifier remains the admission and execution boundary.
6. Safety and payment boundaries stay visible in the public page.

## Six Platform Roles

| Platform | Purpose | Public route | XiaoJ posture |
| --- | --- | --- | --- |
| Commercial joint sales | Local merchant products, POS/shop entry, service products, public welfare return flow | `/shop` | Candidate shopping helper only; formal order/payment still needs approved workflow |
| Property management | Announcements, repairs, parcels, resident service, management fee payment intent | `/web` | Masked resident/owner refs only; payment capture forbidden |
| Member login | Admission, consent, 8D member_ref, XiaoJ/BYOK/OAuth connection | `/google/member/login` | Consent-gated, key_ref/api_ref only |
| Community wish tree | Wish cards, public welfare review, donation targets, wish coin ledger | `/web` | Summaries and drafts only; proposer sensitive data stays private |
| Community coin / ticket exchange | Happiness coin, tickets, vouchers, quota buckets, redemption and correction | `/wuchang/tickets` | Non-financial voucher posture; no cash-out or investment claim |
| Community activity | Events, RSVP, activity notices, volunteer signup, reminders, attendance evidence | `/web` + `web/community_activities.json` | Activity summary and RSVP candidate only; no raw contact data to cloud |

Current public activity seed:

- 五常公園熱舞社運動社團。
- 每週一至週五 20:00-21:00。
- 五常公園。
- 社區婦女可參與。
- RSVP remains candidate-only and member-confirmed.

## Resident Management Fee Payment Boundary

Supported:

- resident or owner sees an allowed function item ref.
- XiaoJ can produce payment intent candidate.
- website can route member to a selected payment tool.
- total field can HOLD until member confirmation.

Forbidden:

- XiaoJ cannot capture payment.
- XiaoJ cannot read payment card data.
- cloud cannot receive payment data.
- association website cannot expose bill plaintext on public pages.
- Odoo write or invoice reconciliation requires a formal approved backend workflow.

## Verification

Verifier:

- `scripts/verify/verify_wuchang_website_quality.py`

Expected final state:

```text
STATE=PASS_WUCHANG_WEBSITE_QUALITY
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_API_KEY_OUTPUT=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
DEPLOY=FALSE
```
