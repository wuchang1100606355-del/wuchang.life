# W7TP Audio Video Ordering AI Architecture

STATE=READONLY_TOTAL_FIELD_PRODUCT_ALIGNMENT_DONE
RUN_ID=TOTAL_FIELD_PRODUCT_AV_ORDERING_AI_20260621_230000
ROOT=/home/taiji_admin/Taiji_Hub

## Product

聊國咖啡館｜小J 主權式影音點餐 AI

This is an Odoo-integrated product architecture. It is not a sidecar, not a fake demo, not a standalone HTML service, and not a rewrite of POS, membership, or AI.

## Existing Alignment

EXISTING_MODULES:

- `wuchang_core`: Odoo menu, POS extensions, device/display/audio models, customer display music, route/controller surface, POS config extension, reports.
- `wuchang_google_member_login`: Google OAuth member login, `res.partner` join source.
- `wuchang_line_login`: LINE OAuth login and `wuchang.line.user`.
- `wuchang_member_registration`: provisional registration, external auth hash, consent ledger, 7D identity, group 8D registration patch.
- `wuchang_pos_topology`: store/company topology split.
- `wuchang_cafe_menu_options`: menu option groups, option questions/items, price deltas, product template menu metadata.

Missing in this workspace:

- `/mnt/extra-addons/*` did not expose readable addon content.
- Repo-local `wuchang_association_member_trust` and `wuchang_cafe_ai_gateway` were not present.
- `wuchang_cafe_menu_options` depends on `wuchang_cafe_ai_gateway`; operator must verify module availability in the actual Odoo container before upgrade.

NO_SECRET_READ=TRUE
NO_MEMBER_PLAINTEXT_READ=TRUE

## Existing Routes

- `/api/menu/import`
- `/api/menu/items`
- `/api/menu/policy/fit`
- `/api/customer_display/music/check`
- `/api/customer_display/music/config`
- `/api/customer_display/music/compliance`
- `/api/device/enroll/chrome_os`
- `/api/device/chrome_os/status`
- `/api/device/chrome_os/heartbeat`
- `/api/device/enroll/android`
- `/api/device/enroll/customer_display`
- `/wuchang/ui/heartbeat`
- `/wuchang/ui/proxy/status`
- `/google/member/login`
- `/google/member/callback`
- `/google/member/welcome`
- `/line/login`
- `/line/callback`
- `/wuchang/member/register/start`
- `/wuchang/member/register/status/<provisional_member_id>`
- `/wuchang/member/register/group/<packet_ref>`
- `/wuchang/member/register/group/<packet_ref>/claim`
- `/wuchang/member/register/group/<packet_ref>/confirm_dry_run`
- `/wuchang/member/register/group/<packet_ref>/status`

## Existing Models

- POS/menu: `wuchang.menu.item`, `wuchang.menu.addon`, `wuchang.menu.attribute`, `wuchang.cafe.option.group`, `wuchang.cafe.option.question`, `wuchang.cafe.option.item`, `product.template`
- Member: `wuchang.member.registration`, `wuchang.member.identity.code`, `wuchang.member.external.auth`, `wuchang.member.consent.ledger`, `wuchang.member.group.registration.batch`, `wuchang.member.group.registration.packet`
- Device/display/audio: `wuchang.device.node`, `wuchang.device.display`, `wuchang.device.audio`, `wuchang.ui.proxy`, `wuchang.customer.display.music.config`
- POS/Odoo embodiment: `pos.config`, `pos.order`, `wuchang.order`, `wuchang.pos.expense`
- Governance/evidence: `wuchang.audit.log`, `wuchang.router.certificate`, `wuchang.ai.hallucination.monitor`

## Existing Views And Data

- Member registration admin views and group 8D registration views.
- POS config, POS expense, POS simulator, order website, delivery pages.
- Device control and customer display music views.
- Menu data in `breakfast_pos_menu.xml` and `menu_setup.xml`.
- POS topology data in `res_company_topology.xml`.

## System Shape

```text
Browser GUI inside Odoo route / web asset / POS extension
  -> W7TP 8D operation packet
  -> cloud / 70B candidate brain
  -> No-LLM backbrain lookup and verifier
  -> UI projection and voice/display adapter
  -> human confirm gate
  -> formal POS action only after separate authorization
  -> evidence seal
```

## Integration Priority

1. Existing `wuchang_*` Odoo module route.
2. Odoo website/controller route.
3. Odoo POS screen extension.
4. Odoo static web asset.
5. Standalone page only if Total Field explicitly authorizes it.

## Lightweight Browser GUI Mount Plan

The first Odoo-integrated GUI should be a route in `wuchang_core` or a small dedicated Odoo addon depending on existing module availability:

- Route: `/wuchang/xiaoj/ordering`
- Controller: reads menu/options through Odoo ORM, not local fake files.
- Asset: Odoo static JS/CSS bundled by manifest, no separate server.
- Screen modes: `customer_display`, `staff_display`, `creditor_demo_display`, `evidence_display`.
- Panels: cloud anchor placeholder, order candidate, 8D packet scanner/input, group member registration entry, menu cards, cart, confirm dry-run, hold warning, proof/seal.

## Cloud Anchor Boundary

Cloud anchor is an adapter only:

- iframe / SDK / stream URL placeholder is allowed.
- Anchor service secret is not stored in repo.
- Member plaintext is not sent to anchor service.
- Anchor display receives product/menu/order candidate refs, never formal authority.

## SUNMI / Voice Boundary

Voice adapter priority:

1. SUNMI container/device voice adapter when operator confirms available API.
2. Browser SpeechSynthesis fallback.
3. Silent/offline prompt mode.

Voice can read menu, candidate order, confirm prompt, queue call. It must not speak or transmit payment secrets, tokens, or member plaintext.

## Patent Product Demonstration

The product demonstration must show:

1. Cloud/70B AI generates candidates only.
2. Candidate is converted into an 8D packet.
3. 8D packet calls registered operations by `packet_ref`.
4. No-LLM backbrain validates menu, price, rules, topology, and permissions.
5. Human confirm gate decides whether a formal POS action can be requested.
6. Evidence seal preserves packet hash, candidate hash, verifier output, and gate result.
7. Odoo/POS is the embodiment, not direct LLM-controlled DB.

