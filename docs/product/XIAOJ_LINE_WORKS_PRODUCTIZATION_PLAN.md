# XiaoJ LINE WORKS Productization Plan

STATE=LINE_WORKS_PRODUCTIZATION_P1_CANDIDATE_GATE_READY

## Product Goal

Add LINE WORKS as the merchant/member notification surface for XiaoJ without
letting AI or browser UI send messages directly.

```text
member / staff / community event
  -> total-field subfield query
  -> LINE WORKS notification candidate
  -> protocol-carrying authority packet
  -> local reconstruction
  -> LINE WORKS bot config + audience + consent + message policy verifier
  -> HOLD / READY_FOR_HUMAN_ACTIVATION
  -> evidence seal and UI status
```

## Total Field Digital Delegate Boundary

The total field may act as the operator's bounded digital delegate for
decision support and preflight governance, but it is not a credential owner and
does not exceed the human owner/admin root of trust.

Allowed delegate work:

- query total-field subfield information before generation
- classify merchant/member/social/LINE WORKS tasks into candidate intents
- build protocol-carrying authority packets
- run local verifier decisions
- prepare release readiness reports
- return HOLD / READY_FOR_HUMAN_ACTIVATION / DEAD_LETTER status

Forbidden delegate work in P1:

- hold Google Workspace, LINE WORKS, Odoo, router, or payment credentials as plaintext
- bypass the human owner/admin for high-risk external-platform changes
- grant itself super-admin authority
- send LINE WORKS messages without verified release refs
- read member plaintext when a hashed or referenced identity is sufficient

Design rule:

```text
total_field_delegate = policy_authority + evidence_verifier + preflight_agent
human_owner_admin = root_of_trust + break_glass_authority
```

## Current Implementation

- Candidate API: `/wuchang/xiaoj/api/lineworks-notify`
- Send preflight API: `/wuchang/xiaoj/api/lineworks-send-preflight`
- Release refs draft API: `/wuchang/xiaoj/api/lineworks-release-refs-draft`
- Execution envelope API: `/wuchang/xiaoj/api/lineworks-execution-envelope`
- Runtime activation draft API: `/wuchang/xiaoj/api/lineworks-runtime-activation-draft`
- Runtime dry-run API: `/wuchang/xiaoj/api/lineworks-runtime-dry-run`
- Operator handoff API: `/wuchang/xiaoj/api/lineworks-operator-handoff`
- Runtime resolver contract API: `/wuchang/xiaoj/api/lineworks-runtime-resolver-contract`
- API auth: `user`
- Intent: `lineworks_notify_candidate`
- Formal send gate: `lineworks_send`
- Odoo operator model: `wuchang.lineworks.notification.candidate`
- Odoo safe actions:

```text
action_build_candidate
action_build_release_refs_draft
action_run_preflight
action_build_execution_envelope
action_build_runtime_activation_packet
action_build_runtime_resolver_contract
action_run_runtime_dry_run
action_build_operator_handoff_pack
action_dead_letter
```

- P1 side effects:

```text
external_api_call=false
formal_lineworks_send=false
secret_read=false
token_read=false
member_plaintext_read=false
```

## Official API Shape

The formal send path is designed around the LINE WORKS Bot API:

```text
POST https://www.worksapis.com/v1.0/bots/{botId}/users/{userId}/messages
```

Required API scopes recorded for the release packet:

```text
bot
bot.message
```

## Connector Preflight

P1 now includes a no-secret connector preflight helper:

```text
wuchang_cafe_ai_gateway.services.lineworks_connector.build_lineworks_send_preflight
```

The helper builds a redacted request envelope and refuses to allow send unless:

- the candidate payload is `lineworks_notify_candidate`
- `lineworks_send` release gate is `RELEASE_READY_FOR_HUMAN_ACTIVATION`
- connector refs are present
- connector refs are uppercase opaque refs containing `REF`
- connector refs do not contain token, JWT, private key, client secret, raw bearer value, or long bare credential value

The JSON route does not trust client-supplied `release_status_payload`. It
always recomputes release readiness from `release_refs` before preflight.

The execution-envelope and runtime-dry-run JSON routes follow the same rule:
they recompute release readiness from `release_refs`; the dry-run route never
honors a client-supplied `enable_external_call` value and always calls the
runtime connector with `enable_external_call=false`.

Required connector refs:

```text
lineworks_bot_ref
lineworks_target_user_ref
lineworks_access_token_runtime_ref
```

Human-fill template:

```text
packets/product_av_ordering_ai/lineworks_release_refs_template.json
```

Release refs draft builder:

```bash
python3 tools/xiaoj_lineworks_release_refs_builder.py \
  --input packets/product_av_ordering_ai/lineworks_release_refs_template.json \
  --pretty
```

Odoo operators can run the same normalization from the candidate form:

```text
action_build_release_refs_draft
```

It rewrites `release_refs_json` into the expected `lineworks_send` +
`connector_refs` shape, keeps `verified=true` only when the refs are safe, and
surfaces warnings without reading secrets or sending LINE WORKS.

Operator handoff pack:

```bash
python3 tools/xiaoj_lineworks_operator_handoff_pack.py \
  --refs packets/product_av_ordering_ai/lineworks_release_refs_template.json \
  --pretty
```

The handoff pack aggregates release refs draft state, readiness blockers,
execution envelope status, runtime activation status, runtime dry-run status,
and the next human actions. It is the fastest way to see what still needs to be
configured in LINE WORKS or the local release registry.

The same pack is also available through:

```text
POST /wuchang/xiaoj/api/lineworks-operator-handoff
Odoo action: action_build_operator_handoff_pack
Service: wuchang_cafe_ai_gateway.services.lineworks_handoff.build_lineworks_operator_handoff_pack
```

The API and Odoo action are evidence aggregation paths only. They do not honor
client-supplied `enable_external_call`, do not send LINE WORKS messages, and do
not read runtime token values.

The builder writes a draft under `runtime/product_av_ordering_ai/lineworks/`.
It accepts refs only and keeps entries unverified unless `--allow-verified` is
used with safe refs, allowlisted verifiers, and non-placeholder 64-hex packet
hashes.

The template is intentionally not pre-verified. It must remain HOLD until a
human fills verified refs with real evidence hashes.

Offline readiness command:

```bash
python3 tools/xiaoj_lineworks_release_readiness.py \
  --refs packets/product_av_ordering_ai/lineworks_release_refs_template.json \
  --pretty
```

Expected result for the untouched template is
`HOLD_LINEWORKS_RELEASE_READINESS`. A filled and verified refs file must return
`PASS_LINEWORKS_RELEASE_READINESS` before any P2 runtime connector is enabled.

Offline execution-envelope export:

```bash
python3 tools/xiaoj_lineworks_execution_envelope_export.py \
  --refs packets/product_av_ordering_ai/lineworks_release_refs_template.json \
  --message "LINE WORKS 候選通知 envelope 匯出" \
  --target-ref TARGET_REF_HASHED_OR_MASKED \
  --pretty
```

The exporter writes a redacted JSON artifact under
`runtime/product_av_ordering_ai/lineworks/`. It is a handoff envelope for a
future runtime connector, not a send command. It always reports:

```text
runtime_send_enabled=false
external_api_call=false
formal_lineworks_send=false
credential_values_in_export=false
raw_member_identity_in_export=false
```

Runtime activation packet builder:

```bash
python3 tools/xiaoj_lineworks_runtime_activation_builder.py \
  --operator-ref OPERATOR_REF_VERIFIED_PILOT \
  --execution-envelope-hash 64hex \
  --confirm-human-activation \
  --pretty
```

The activation packet only prepares runtime dry-run evidence. It does not
resolve credentials, send LINE WORKS messages, or enable external calls. A
packet becomes ready only when the operator ref is safe and the execution
envelope hash is 64-hex.

Runtime resolver contract builder:

```bash
python3 tools/xiaoj_lineworks_runtime_resolver_contract_builder.py \
  --refs packets/product_av_ordering_ai/lineworks_release_refs_template.json \
  --pretty
```

The resolver contract records only binding metadata:

```text
connector_ref
binding_ref
value_class
value_hash
verifier
verified
```

It must not contain bot ID, LINE WORKS user ID, access token, private key, or
member plaintext. The production runtime resolver may resolve those values in
memory only after human activation, but the contract and UI must only retain
refs, hashes, and verifier status.

## P2 Runtime Connector Shell

P2 now has a controlled connector shell:

```text
wuchang_cafe_ai_gateway.services.lineworks_connector.execute_lineworks_send_envelope
```

Default behavior is dry-run only:

```text
enable_external_call=false
external_api_call=false
formal_lineworks_send=false
secret_read=false
```

The connector can enter the real send path only when all of these are true:

- the execution envelope is `PASS_LINEWORKS_EXECUTION_ENVELOPE_READY`
- a human activation packet is present
- `activation_packet_hash` is 64-hex
- `operator_ref` is a safe ref or hash
- runtime resolver contract is ready
- `enable_external_call=true`
- a runtime resolver supplies bot ID, target user ID, and access token in memory

The runtime result must not echo bot ID, target user ID, access token, or LINE
WORKS response body. It may return hashes, status code, endpoint template, and
evidence hashes.

The preflight output never echoes bot id, target user id, access token, client
secret, private key, or member plaintext. It still reports:

```text
external_api_call=false
formal_lineworks_send=false
```

Reference pages:

- https://developers.worksmobile.com/en/docs/api
- https://developers.worksmobile.com/en/docs/auth
- https://developers.worksmobile.com/en/docs/auth-jwt
- https://developers.worksmobile.com/en/docs/bot-user-message-send

## Required Human Operations

You must complete these in LINE WORKS Developer Console or admin console:

1. Create or confirm the client app for XiaoJ merchant notification.
2. Create or confirm the Bot and record only the Bot ID as a reference.
3. Enable `bot` and `bot.message` scopes.
4. Choose service account JWT or user OAuth authorization for the first pilot.
5. Add the bot to the target domain and test member account.
6. Record target user IDs as refs, not member plaintext.
7. Produce verified release refs for:

```text
authenticated_staff_ref
lineworks_release_packet_ref
lineworks_app_config_ref
lineworks_bot_ref
lineworks_target_user_ref
message_policy_ref
consent_policy_ref
total_field_release_ref
```

8. Prepare connector refs for P2 runtime:

```text
lineworks_bot_ref
lineworks_target_user_ref
lineworks_access_token_runtime_ref
```

Do not paste access tokens, private keys, client secrets, raw member profile,
or member plaintext into repo files or chat.

## Red-Team Controls

The P1 implementation explicitly blocks these bypass attempts:

- forged `release_status_payload` supplied by a browser or client
- JWT-shaped values in connector refs
- long bare token-like values in connector refs
- lowercase/raw IDs where an uppercase opaque ref is required
- Odoo candidate records containing secret-shaped material in candidate, ref, or release fields

## P1 Acceptance

P1 is complete when:

- The candidate API returns `lineworks_notify_candidate`.
- The candidate API returns an authority packet and local verifier.
- Raw target user refs are not echoed.
- `formal_lineworks_send=false`.
- Fake string release refs produce `HOLD_RELEASE_REFS_UNVERIFIED`.
- Verified release refs can move `lineworks_send` to
  `RELEASE_READY_FOR_HUMAN_ACTIVATION`.

## P2 Formal Send Conditions

P2 may add real LINE WORKS sending only after:

- Credentials are stored outside source code.
- Token retrieval is isolated in a small connector.
- The connector accepts only a verified release packet.
- The runtime connector consumes a redacted execution envelope and resolves
  credential/user refs only inside the approved runtime boundary.
- Message body, target user ref, bot ref, consent ref, and policy ref are sealed.
- Failed sends enter HOLD / QUEUE / DEAD_LETTER with evidence seal.
