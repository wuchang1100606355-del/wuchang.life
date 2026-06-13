# W3_8D_PACKET_SCHEMA_SDK_20260613_070707

## Purpose

This run creates the W7TP / XiaoJ 8D Packet Schema SDK for redacted, reference-only packet exchange between member-owned UI, context broker, key/API broker, browser action bus, counter avatar, merchant connector, and committee connector lanes.

No service was started or restarted. No database write, runtime deployment, router change, Tailscale change, DNS change, package install, secret read, raw member plaintext read, or network call was required for generation.

## W0 Preflight Evidence

- current_node: taiji01
- workspace: /home/taiji_admin/Taiji_Hub
- branch_required: main
- dirty_worktree_required: false
- latest_master_deploy_index: docs/ledger/master_deploy_index_ledger.jsonl
- latest_five_in_one_deploy_packet: docs/ledger/five_in_one_generative_deploy_ledger.jsonl
- latest_compliance_settings_packet: docs/ledger/compliance_settings_generative_write_ledger.jsonl
- latest_redteam_paste_integrity_gate: docs/evidence/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.sha256

## Relation To Five-in-One

Five-in-One remains the deployable governance frame. This 8D SDK is a packet contract below that frame: it lets each product lane carry identity references, intent, state, topology, resource references, governance, verification requirements, and replay-safe envelope metadata without exposing plaintext context or raw credentials.

## D1-D8 Definitions

- D1_identity: actor_ref, actor_type, device_ref, role, and plaintext_identity_forbidden=true.
- D2_intent: primary_intent, secondary_intent, transaction_intent, and risk_level.
- D3_state: session_state, task_state, browser_state, order_state, and context_mode.
- D4_topology: channel, site_ref, device_topology, and origin_scope.
- D5_resource: key_policy, selected_key_ref, api_refs, model_tier, cache_policy, and cost_policy.
- D6_governance: allowed_actions, forbidden_actions, no_plaintext_context, human_confirm_required, and staff_confirm_required.
- D7_verification: redaction_check_required, leak_check_required, action_allowlist_required, response_verify_required, and usage_log_required.
- D8_envelope: packet_ref, nonce, counter, ttl_seconds, created_at, schema_version, content_hash, hmac_ref, signature_ref, and replay_protection.

## No-Plaintext Context Rule

Packets carry opaque refs only. Member names, resident records, exact contact data, precise addresses, raw browser state, raw storage values, and full conversation payloads must stay outside the packet. `D6_governance.no_plaintext_context` must be true and `D1_identity.plaintext_identity_forbidden` must be true.

## key_ref / api_ref Rule

`D5_resource.selected_key_ref` must begin with `key_ref:`. `D5_resource.api_refs` must be non-empty and each item must begin with `api_ref:`. Raw API keys, authorization header credentials, private keys, and provider tokens are forbidden in packet JSON.

## Browser Action Allowlist

Browser action packets are dry-run only in this SDK version. Allowed action names are reference-based commands such as navigate_ref, click_ref, fill_ref, select_ref, read_text_ref, screenshot_ref, wait_ref, extract_ref, open_sidebar_ref, close_sidebar_ref, render_sidebar_ref, read_context_ref, write_draft_ref, route_to_connector_ref, broker_api_call_ref, cache_lookup_ref, read_menu_ref, create_order_draft_ref, queue_service_ref, notify_staff_ref, ask_human_confirm, and handoff_to_human.

## Forbidden Fields

Packets must not contain plaintext values for password, cookie, localStorage, bearer token, private key, raw API key, raw access token, Taiwan identity labels, phone, address, birthday, or email fields. The Python verifier scans values and selected dangerous keys while allowing harmless field names such as secret_scan_result.

## Verification Requirements

A packet is acceptable only after the standard-library verifier passes these checks:

- all D1-D8 dimensions and required fields are present;
- no forbidden plaintext/key markers are found;
- key_ref and api_ref discipline is preserved;
- browser action names are allowlisted and dry_run=true;
- D8 envelope contains nonce, counter, ttl_seconds, created_at, schema_version, content_hash, hmac_ref, signature_ref, and replay_protection=true.

## Future Integration Points

- Member-Owned Sidebar XiaoJ: use member_sidebar channel with ref-only context.
- No-Plaintext Context Broker: exchange redacted context refs and cache refs.
- Hybrid Key / API Broker: select broker-managed key_ref and api_ref lanes.
- Browser Action Bus: emit dry-run action packets before human review.
- Counter XiaoJ Avatar: produce response packets without plaintext member data.
- Merchant / Committee Connector: draft service/order packets with staff or human confirmation gates.

## Generated Files

- schemas/8d/xiaoj_8d_packet.schema.json
- schemas/8d/xiaoj_8d_action_packet.schema.json
- schemas/8d/xiaoj_8d_response_packet.schema.json
- sdk/python/w7tp_8d_packet.py
- sdk/typescript/w7tp_8d_packet.ts
- packets/examples/8d/member_sidebar_example.json
- packets/examples/8d/browser_action_example.json
- packets/examples/8d/no_plaintext_context_example.json
- packets/examples/8d/merchant_connector_example.json
- packets/examples/8d/committee_service_example.json
