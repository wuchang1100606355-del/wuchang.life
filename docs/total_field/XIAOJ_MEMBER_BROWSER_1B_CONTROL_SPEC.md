# XiaoJ Member Browser 1B Control Spec

STATE=XIAOJ_MEMBER_BROWSER_1B_CONTROL_SPEC_READY
SCOPE=PRODUCT_GRADE_MVP

## Purpose

This spec defines the product-grade local 1B AI layer for member-owned browser assistance.

The 1B model is not the final authority. It is a low-cost browser intent and action candidate generator that must emit dry-run 8D action packets for Total Field verification.

## Product Position

```text
member request
-> XiaoJ member browser 1B controller
-> xiaoj_8d_action_packet
-> Total Field verifier
-> browser shell / PWA / extension receives allowed dry-run action
-> member confirms before any real submit or service handoff
```

## Product Feel

小J must feel like a warm community daily-life assistant, not a generic chatbot.

The 1B layer may use these ref-only signals to tune response order and tone:

- `member_preference_ref`
- `service_style_ref`
- `behavior_info_ref`
- `benefit_ref`
- `quota_bucket_ref`

These refs may influence whether XiaoJ opens the sidebar, summarizes first, drafts a form, or asks a human to confirm. They must not carry member plaintext, raw browsing history, phone, address, ID number, raw audio, cookies, OAuth tokens, or API keys.

Default service posture:

- warm but concise.
- proactive but verifier-gated.
- community-service oriented.
- member-owned and revocable.
- candidate-only until Total Field allows the next step.

## Local Model

Preferred local model:

- `xiaoj-member-browser-1b`

Base model:

- `qwen2.5:1.5b`

Reason:

- Fits current local hardware better than 7B+.
- Good enough for intent routing, browser action classification, and short member assistance.
- Heavy reasoning can be routed to Google AI Ultra only through redacted cloud candidate packets.

## Controller

Tool:

- `tools/member_browser/xiaoj_member_browser_1b_controller.py`

The controller produces existing SDK-compatible action packets:

- `packet_type=xiaoj_8d_action_packet`
- schema target: `schemas/8d/xiaoj_8d_action_packet.schema.json`
- verifier target: `sdk/python/w7tp_8d_packet.py`

PWA cockpit:

- `web/xiaoj_member_browser_cockpit/index.html`
- `web/xiaoj_member_browser_cockpit/app.js`
- `web/xiaoj_member_browser_cockpit/manifest.webmanifest`

The PWA is a member-facing shell for the same contract. It creates a local dry-run packet, runs a client-side Total Field preview gate, and packages cloud candidate return refs. It does not collect raw API keys or raw member identity.

Browser extension bridge:

- `web/xiaoj_member_browser_extension/manifest.json`
- `web/xiaoj_member_browser_extension/background.js`
- `web/xiaoj_member_browser_extension/sidepanel.html`
- `web/xiaoj_member_browser_extension/sidepanel.js`

The extension is the controlled browser boundary. It does not make the model an autonomous browser operator. It accepts only verifier-shaped 8D packets and applies a second local gate before touching the active tab.

Extension bridge return schema:

- `schemas/browser/xiaoj_browser_bridge_return_packet_v1.schema.json`

Every extension result returns `BROWSER_BRIDGE_RETURN_PACKET` with `cloud_compute_ref`, `behavior_info_ref`, `action_trace_ref`, selected text ref, draft ref, and `execution_allowed=false`.

Optional native gateway:

- `tools/member_browser/xiaoj_member_browser_native_host.py`
- `tools/member_browser/render_xiaoj_native_host_manifest.py`
- `tools/member_browser/smoke_xiaoj_native_host_protocol.py`
- template: `web/xiaoj_member_browser_extension/native_host/tw.taiji.xiaoj_member_browser_gateway.template.json`

The native host lets the MV3 extension call the local XiaoJ gateway through Chrome/Edge native messaging. This is local IPC, not an external API. If unavailable, the extension falls back to the local minimum-privilege bridge.

Native gateway constraints:

- no external network call.
- no DB/Odoo/POS write.
- no service start or deploy.
- no raw API key, OAuth token, cookie, localStorage, member plaintext, raw audio.
- output remains `XIAOJ_MEMBER_BROWSER_GATEWAY_RESULT` with `candidate_only=true`.
- native messaging protocol smoke uses the real 4-byte length-prefixed stdin/stdout frame.

Member release packaging:

- `tools/member_browser/package_xiaoj_member_browser_release.py`
- `tools/member_browser/simulate_xiaoj_browser_bridge.py`
- `tools/member_browser/xiaoj_member_browser_gateway.py`
- `schemas/browser/xiaoj_member_browser_gateway_result_v1.schema.json`
- `schemas/browser/xiaoj_member_browser_release_manifest_v1.schema.json`
- output root: `runtime/member_browser/releases/`

The package tool creates a member-deliverable release with:

- `xiaoj_member_browser_extension_mv3.zip`
- `xiaoj_member_browser_cockpit_pwa.zip`
- `RELEASE_MANIFEST.json`
- `SHA256SUMS.tsv`
- `MEMBER_INSTALL_README.md`

The release manifest records all included source hashes, package hashes, safety flags, no-host-permission boundary, and allowed/blocked browser actions.

Offline browser bridge simulator:

- `tools/member_browser/simulate_xiaoj_browser_bridge.py --smoke`

The simulator verifies the extension policy without launching Chrome:

- allows `open_sidebar_ref`.
- allows `read_text_ref` while returning only selected text ref and length.
- blocks unconfirmed `write_draft_ref`.
- allows confirmed safe `write_draft_ref`.
- blocks sensitive draft content.
- blocks sensitive target fields.
- blocks `submit_payment`.
- blocks `read_raw_cookie`.

Local gateway:

- `tools/member_browser/xiaoj_member_browser_gateway.py --smoke`
- `schemas/browser/xiaoj_association_usage_admission_packet_v1.schema.json`

The gateway composes the product service chain:

```text
member intent
-> xiaoj_8d_action_packet
-> browser bridge simulation
-> BROWSER_BRIDGE_RETURN_PACKET
-> CLOUD_CANDIDATE_RETURN_PACKET
-> ASSOCIATION_USAGE_ADMISSION_PACKET
-> XIAOJ_MEMBER_BROWSER_GATEWAY_RESULT
```

Gateway output proves that the same member request can carry:

- `member_preference_ref`
- `service_style_ref`
- `behavior_info_ref`
- `cloud_compute_ref`
- browser action trace ref
- cloud candidate return packet
- association admission packet for no-plaintext association use approval
- no plaintext transfer flags

Association admission packet:

The association does not need raw member context to approve or refuse service use. The local gateway therefore derives `ASSOCIATION_USAGE_ADMISSION_PACKET` from the browser bridge and cloud candidate return packets.

It carries only:

- `member_ref`, never full member identity.
- consent, quota, benefit, action, tendency, behavior, and cloud compute refs.
- source, browser return, and cloud return hashes.
- `admission_decision=ALLOW|HOLD|BLOCK`.
- `execution_allowed=false`.
- `member_plaintext_transferred=false`.
- `raw_api_key_transferred=false`.
- `oauth_token_transferred=false`.

This gives the association enough evidence for use admission, fair-use accounting, risk hold, and audit without taking custody of member plaintext, raw browser pages, API keys, OAuth tokens, cookies, payment data, or raw audio.

Extension allowed local actions:

- `open_sidebar_ref`
- `read_text_ref`
- `write_draft_ref` only after member confirmation.

Extension blocked local actions:

- raw cookie or raw storage read.
- password, token, credential, phone, payment, address, or ID fields.
- free mouse control.
- arbitrary click/fill/select.
- silent submit.
- payment submit.
- order submit without human confirmation.
- DB, Odoo, POS, deploy, router, or service operations.

Product-grade params emitted by the controller:

- `member_preference_ref`
- `service_style_ref`
- `behavior_info_ref`
- `cloud_compute_ref`
- `benefit_ref`
- `quota_bucket_ref`
- `odoo_identity_ref`
- `odoo_role_ref`
- `odoo_function_scope_ref`
- `odoo_function_item_set_ref`
- `odoo_function_item_refs_csv`
- `odoo_permission_bucket_ref`
- `payment_tool_ref`
- `management_fee_bill_ref`
- `payment_amount_bucket_ref`
- `payment_intent_ref`
- `generative_transmission_ref`
- `return_packet_schema=w7tp.cloud_candidate_return_packet.v1`

Odoo role function items stay ref-only. Current member daily-life function examples include:

- resident notice read.
- resident activity query.
- resident activity RSVP candidate.
- resident benefit masked read.
- resident management fee masked read.
- resident management fee payment intent candidate.
- consumer activity query and activity RSVP candidate.
- committee activity notice draft.
- property staff activity notice route.

Payment and activity boundaries:

- management fee support produces only `payment_intent_ref` plus selected payment tool refs.
- activity RSVP support produces only a `write_draft_ref` candidate.
- neither management fee nor activity RSVP may auto-submit, auto-enroll, capture payment, write Odoo, or send raw contact data to cloud.

## Allowed Browser Action Scope

Allowed candidate actions:

- `open_sidebar_ref`
- `read_text_ref`
- `cache_lookup_ref`
- `read_menu_ref`
- `route_to_connector_ref`
- `write_draft_ref`
- `create_order_draft_ref`
- `ask_human_confirm`
- `handoff_to_human`

All actions remain:

- dry-run.
- submit-forbidden.
- candidate-only.
- verifier-gated.

## Forbidden Operations

- free mouse control.
- silent submit.
- payment submit.
- raw credential read.
- cookie read.
- localStorage read.
- all-tab scrape.
- DB write.
- Odoo write.
- POS write.
- deploy.
- service restart.

## Cloud Compute Return Integration

If the browser task needs high compute, the 1B controller may route only a redacted task packet to the cloud proxy. The service path must then return:

- `CLOUD_CANDIDATE_RETURN_PACKET`
- `candidate_only=true`
- `must_not_execute=true`
- `requires_total_field_verify=true`
- `member_plaintext_transferred=false`
- `cloud_compute_ref`
- `behavior_info_ref`
- `action_trace_ref`

Spec:

- `docs/total_field/W7TP_CLOUD_COMPUTE_PACKETIZED_RETURN_SPEC.md`
- `schemas/cloud_proxy/w7tp_cloud_candidate_return_packet_v1.schema.json`

Cloud compute is treated as a temporary candidate engine. It may add reasoning value, draft quality, summarization quality, translation quality, or service-routing suggestions. It cannot add authority.

## Member Tendency Boundary

Allowed tendency signals:

- preference bucket ref.
- accessibility preference ref.
- language preference ref.
- service cadence ref.
- menu/activity/benefit interest ref.
- quota and cost bucket ref.

Forbidden tendency signals:

- raw clickstream.
- raw browser page.
- raw chat history.
- full private document text.
- member name, phone, address, ID number.
- payment data.
- API key or OAuth token.

## Acceptance Criteria

- Controller emits `browser_action_bus` packets accepted by the 8D packet verifier.
- All browser actions remain `dry_run=true` and `submit_forbidden=true`.
- High-risk tasks produce `handoff_to_human` or HOLD/BLOCK state.
- Cloud return packet includes `cloud_compute_ref` and `behavior_info_ref`.
- Gateway result includes `ASSOCIATION_USAGE_ADMISSION_PACKET` with `cloud_compute_ref`, `behavior_info_ref`, `member_tendency_ref`, `admission_decision`, and no sensitive payload.
- Extension bridge declares no host permissions and no cookie permission.
- Extension may request `nativeMessaging` only for the local gateway host `tw.taiji.xiaoj_member_browser_gateway`.
- Extension bridge only executes `open_sidebar_ref`, `read_text_ref`, and confirmed `write_draft_ref`.
- Extension packets use `draft_ref`; raw draft text is local-only and is not returned in bridge results.
- Extension bridge results validate against `xiaoj.browser_bridge_return_packet.v1`.
- Member release package validates against `xiaoj.member_browser_release_manifest.v1`.
- Release package includes SHA256 hashes for the extension zip, PWA zip, release manifest, and member install README.
- Offline bridge simulator returns `PASS_XIAOJ_BROWSER_BRIDGE_SIMULATOR`.
- Local gateway returns `PASS_XIAOJ_MEMBER_BROWSER_GATEWAY`.
- Native host one-shot verification returns a gateway result without DB/service/cloud calls.
- Native host protocol smoke returns `PASS_XIAOJ_NATIVE_HOST_PROTOCOL`.
- No member plaintext, raw secret, raw audio, cookie, localStorage, DB write, Odoo write, POS write, payment capture, deploy, or service restart.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_API_KEY_OUTPUT=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
DEPLOY=FALSE
SERVICE_RESTART=FALSE
PRODUCTION_RELEASE=FALSE
