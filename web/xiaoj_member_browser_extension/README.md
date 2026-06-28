# XiaoJ Member Browser Extension Bridge

STATE=XIAOJ_MEMBER_BROWSER_EXTENSION_BRIDGE_READY
SCOPE=PRODUCT_GRADE_MVP

## Purpose

This Chrome/Edge MV3 extension bridge turns verified XiaoJ 1B browser action packets into minimum-privilege local browser operations.

It is not an autonomous browser agent. It is an execution gate for candidate-only 8D packets.

## Allowed Local Actions

- `open_sidebar_ref`: open the XiaoJ side panel.
- `read_text_ref`: collect only selected-text refs and length from the active tab.
- `write_draft_ref`: write a local draft only after member confirmation and only into non-sensitive editable fields.

## Blocked Actions

- payment submit.
- order submit without human confirmation.
- raw cookie read.
- raw local storage read.
- password, token, or credential entry.
- free mouse control.
- arbitrary click/fill/select.
- DB, Odoo, POS, deploy, service restart, or router actions.

## No-Plaintext Contract

8D packets must contain refs only:

- `member_preference_ref`
- `service_style_ref`
- `behavior_info_ref`
- `cloud_compute_ref`
- `draft_ref`
- `safe_context_ref`

The side panel may hold local draft text briefly so the bridge can write it into the currently focused field after member confirmation. The packet carries only `draft_ref`, and the bridge result never returns raw draft text.

## Bridge Return Packet

Every bridge result includes:

- `schema_version=xiaoj.browser_bridge_return_packet.v1`
- `packet_type=BROWSER_BRIDGE_RETURN_PACKET`
- `cloud_compute_ref`
- `behavior_info_ref`
- `action_trace_ref`
- `selected_text_ref`
- `draft_ref`
- `execution_allowed=false`
- `raw_browser_page_transferred=false`
- `raw_text_returned=false`

Schema:

- `schemas/browser/xiaoj_browser_bridge_return_packet_v1.schema.json`

## Browser Boundary

Manifest permissions:

- `activeTab`
- `nativeMessaging`
- `scripting`
- `sidePanel`
- `storage`

No host permissions are declared. No cookie permission is declared.

## Optional Native Gateway

The side panel can call the local native host first:

- host name: `tw.taiji.xiaoj_member_browser_gateway`
- host tool: `tools/member_browser/xiaoj_member_browser_native_host.py`
- gateway tool: `tools/member_browser/xiaoj_member_browser_gateway.py`

Render a local host manifest after Chrome/Edge shows the loaded extension id:

```bash
tools/member_browser/render_xiaoj_native_host_manifest.py --extension-id <extension_id>
```

This writes only:

```text
runtime/member_browser/native_host/tw.taiji.xiaoj_member_browser_gateway.json
```

Manual browser installation is still required. The renderer does not write system directories and does not use sudo.

If the native host is unavailable, the extension falls back to the local minimum-privilege bridge.

## Verification

Run:

```bash
scripts/verify/verify_xiaoj_member_browser_cockpit.py
```

Offline bridge policy smoke:

```bash
tools/member_browser/simulate_xiaoj_browser_bridge.py --smoke
```

Native messaging protocol smoke:

```bash
tools/member_browser/smoke_xiaoj_native_host_protocol.py
```

Expected:

```text
EXTENSION_ASSETS_PRESENT=PASS
EXTENSION_NO_HOST_PERMISSIONS=PASS
EXTENSION_NO_COOKIE_PERMISSION=PASS
EXTENSION_DRAFT_REF_ONLY=PASS
NATIVE_HOST_ONCE_JSON=PASS
NATIVE_HOST_PROTOCOL_SMOKE=PASS
BRIDGE_SIMULATOR_SMOKE=PASS
STATE=PASS_XIAOJ_MEMBER_BROWSER_COCKPIT
```

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
