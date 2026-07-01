# XiaoJ Merchant System Invention Capability Integration

STATE=XIAOJ_MERCHANT_SYSTEM_INVENTION_CAPABILITY_BLUEPRINT_READY

This document turns the W7TP / XiaoJ invention stack into merchant-system
product capabilities. The target product is not only an AI ordering screen. It
is a sovereign merchant operating system in which cloud AI, humanoid avatar,
membership, POS, table-side ordering, social operations, and community/property
workflows are all gated by local authority.

## Product Sentence

Cloud AI serves the customer experience. Local authority decides execution.
The humanoid layer can be subscribed from the cloud, but member authority,
discount authority, order authority, payment authority, social publication
authority, and property/community authority remain local.

```text
customer / staff / table / community input
  -> total-field subfield query
  -> cloud or local AI candidate
  -> protocol-carrying authority packet
  -> local reconstruction
  -> sovereign member / menu / POS / property / social verifier
  -> EXECUTE / HOLD / QUARANTINE / QUEUE / DEAD_LETTER
  -> evidence seal and UI status
```

## Capability Layers

| Layer | Merchant Capability | Invention Capability Added | Authority Boundary |
| --- | --- | --- | --- |
| L0 | Total-field subfield query | Every generation consults total-field level subfield information before authority packet construction | Missing or failed subfield query causes HOLD |
| L1 | AI candidate intake | AI output is candidate-only | AI never directly writes POS, member, payment, property, or social records |
| L2 | Protocol-carrying authority packet | Candidate is converted into a locally verifiable authority packet | Packet carries intent/state/evidence/permission/risk/reconstruction/failure fields |
| L3 | Generative transmission | Full sensitive body is not sent when indexes, deltas, hashes, state codes, route keys, or generation parameters are enough | Cloud receives minimized candidate context |
| L4 | Local reconstruction | Local side reconstructs verifiable menu/member/order/community state | Formal authority comes from local lookup and verifier |
| L5 | No-floating-point discrete authority | Approval uses integer state codes, bit flags, hashes, lookup keys, TTL, nonce, evidence refs | Neural model scores are not execution authority |
| L6 | Data breathing flow | Every candidate moves through visible governance states | No silent fail |
| L7 | Dead-letter governance | Failed, expired, risky, incomplete, or unverifiable candidates are retained for review | Failed candidate cannot execute |
| L8 | Evidence seal | Each candidate, decision, and gate result is sealed | Audit can explain why execution was or was not allowed |
| L9 | UI status | Staff/customer/admin sees candidate, hold, review, dead-letter, execute status | Cloud UI cannot bypass local gate |

## Merchant Modules

### 0. Mandatory Total-Field Subfield Query

Purpose: every generated candidate or local payload must first consult the
current total-field subfield state. This prevents the merchant system from
generating in a narrow silo when the total field has already distributed updated
state, routing, safety, or field-scope information.

Runtime rule:

```text
generation request
  -> query runtime/intent_subfields
  -> summarize latest subfield packet refs and safety flags
  -> hash the query result
  -> embed query hash in authority packet
  -> local verifier blocks execution if query is missing or not OK
```

Disclosure boundary:

- Expose subfield name, latest packet reference, hash, state, run id, mission,
  and safety flags.
- Do not expose full packet body, owner details, complete git state, secrets,
  member plaintext, raw audio, router credentials, or private lookup tables.

### 1. Sovereign AI Membership

Purpose: give the merchant high-quality personalization without giving cloud AI
member authority.

Local authority fields:

- member reference, not member plaintext
- membership level
- consent state
- benefit and coupon eligibility
- preference code
- blacklist or hold state
- TTL and nonce
- evidence reference

Cloud AI may:

- suggest a greeting
- suggest menu recommendations
- suggest preference-aware wording
- generate a coupon candidate
- draft member messages

Cloud AI must not:

- decide identity
- decide membership level
- activate a discount
- update member records
- receive member plaintext
- receive payment data

Execution gate:

```text
member_candidate
  -> member authority packet
  -> local member verifier
  -> personalize / discount / hold / review
```

### 2. Cafe Audio-Video AI Ordering Waiter

Purpose: create the impressive merchant-facing experience while keeping the
invention boundary clean.

Cloud humanoid subscription can provide:

- avatar rendering
- voice conversation
- speech-to-text
- text-to-speech
- menu explanation
- customer-facing tone and service style
- natural-language order candidate

Local authority must verify:

- menu item exists
- option is allowed
- price is recomputed locally
- table or session is valid
- member discount is authorized
- stock or service state is acceptable
- staff confirmation is present when required
- payment remains separately gated

Execution gate:

```text
voice / text / avatar order intent
  -> order candidate packet
  -> menu + option + price + table + member verifier
  -> staff confirm or local execute
  -> POS write only after execution_allowed=true
```

### 3. Odoo / POS / Table-Side Ordering

Purpose: make Odoo/POS the formal transaction embodiment, not an LLM-controlled
database.

Supported surfaces:

- Odoo route: `/wuchang/xiaoj/ordering`
- customer display mode
- staff display mode
- table-side QR ordering
- POS screen extension
- evidence display mode

Authority rules:

- AI can produce draft order lines.
- Formal POS order creation requires local verifier approval.
- Payment capture requires a separate payment gate.
- Refund, discount, loyalty point, inventory, and membership effects require
  their own local authority checks.

### 4. Merchant Social AI Manager

Purpose: use AI for business growth without allowing AI to publish or activate
customer-impacting campaigns directly.

AI may draft:

- social posts
- LINE or community messages
- menu announcements
- coupon campaigns
- event invitations
- reply candidates

Local authority verifies:

- audience segment reference
- offer validity
- channel permission
- consent state
- publication role
- risk flags
- TTL and nonce

Execution states:

```text
DRAFT_CANDIDATE -> LOCAL_APPROVAL_REQUIRED -> SCHEDULED / HOLD / DEAD_LETTER
```

### 5. Property And Community Merchant Extension

Purpose: extend the same authority-packet system into property and community
service workflows.

AI may generate candidates for:

- visitor access
- parcel notice
- facility booking
- repair request
- fee reminder
- resident announcement
- volunteer or manpower dispatch
- community event notice

Local authority verifies:

- resident reference
- unit reference
- role and permission
- time window
- facility state
- service category
- consent state
- evidence reference

No AI-generated community action executes without local authority.

### 6. Router / Edge / Local Authority Node

Purpose: keep the merchant system resilient even when cloud services are slow,
unavailable, or untrusted.

Edge node may provide:

- route key resolution
- capacity hold
- local verifier status
- queue status
- evidence reference
- offline local lookup

Edge node must not publicly expose:

- credentials
- full routing tables
- private lookup tables
- private weights
- member plaintext
- raw audio or raw video

## Implementation Phases

| Phase | Product Name | Build Target | Safety Boundary |
| --- | --- | --- | --- |
| P0 | Shadow candidate rehearsal | local candidate order packets and evidence status | no POS write, no payment |
| P1 | Merchant AI assistant MVP | table-side QR + AI candidate + local verifier + staff confirm | formal writes still gated |
| P2 | Audio-video humanoid waiter | cloud avatar/voice subscription plus local authority packet | cloud remains candidate-only |
| P3 | Odoo/POS execution gate | verified order write and evidence seal | payment separate |
| P4 | Sovereign AI membership | preference, consent, benefit, and discount authority | no member plaintext to cloud |
| P5 | Social and community manager | campaign drafts, community messages, property workflows | local approval before publication/execution |
| P6 | Edge resilience | fallback queue, dead-letter, offline lookup, router/edge status | no cloud authority |

## Minimal First Build

The smallest commercially meaningful system is:

```text
Odoo/POS menu read
  + table/customer/staff ordering UI
  + total-field subfield query before every generation
  + cloud humanoid or voice candidate service
  + local authority packet generator
  + menu/price/table/member verifier
  + staff confirmation gate
  + evidence seal
```

This version is already enough to demonstrate the invention in a merchant
setting because it proves the key distinction:

```text
AI makes a candidate.
Local authority makes the executable decision.
```

## Product Requirements

Must have:

- candidate-only cloud AI
- total-field subfield query before every generation
- local authority verifier
- authority packet
- member-safe personalization
- Odoo/POS formal gate
- staff confirmation path
- evidence seal
- visible UI status
- hold/dead-letter failure states
- formal release gates for member registration, POS order creation, and payment

Should have:

- cloud humanoid avatar subscription
- speech input and output
- table-side QR session
- social campaign draft gate
- property/community workflow gate
- edge fallback queue

Must not have in early commercial build:

- autonomous payment capture by AI
- direct POS write from cloud response
- cloud-side member plaintext
- cloud-side discount authority
- cloud-side social publication authority
- raw audio retention by default
- unsealed silent failures

## Formal Release Gates

The original merchant modules expose a no-side-effect release status path for
the three formal commercial actions:

```text
/wuchang/xiaoj/api/formal-release-status
```

The API checks release references for:

- formal member registration
- formal POS order creation
- formal payment

Each gate returns `HOLD_RELEASE_REQUIREMENTS_INCOMPLETE` until all required
release references are present, and `HOLD_RELEASE_REFS_UNVERIFIED` when the refs
are only strings or unsigned placeholders. Release refs must be verified objects
with a ref, packet hash, allowed verifier, and `verified=true`; raw ref values
are not echoed back to the UI. Total-field subfield danger flags also block the
gate before human activation. When complete and verified, the gate returns
`RELEASE_READY_FOR_HUMAN_ACTIVATION`, not automatic execution. The P1 runtime
still reports:

```text
formal_db_write=false
formal_pos_write=false
payment_capture=false
member_plaintext_read=false
external_api_call=false
```

This creates an auditable bridge from candidate-only operation to formal
activation without letting cloud AI, avatar service, or an unreviewed UI directly
create members, write POS orders, or capture payments.

## Integration With Existing Repo

Existing Odoo-aligned pieces:

- `wuchang_core`
- `wuchang_cafe_ai_gateway`
- `wuchang_cafe_menu_options`
- `wuchang_google_member_login`
- `wuchang_line_login`
- `wuchang_member_registration`
- `wuchang_pos_topology`
- `wuchang_property_local_cloud`
- `/wuchang/xiaoj/ordering`

Existing product contracts:

- `packets/product_av_ordering_ai/cloud_candidate_contract.json`
- `packets/product_av_ordering_ai/no_llm_backbrain_contract.json`
- `packets/product_av_ordering_ai/formal_gate_contract.json`
- `packets/product_av_ordering_ai/function_call_spec.json`
- `packets/product_av_ordering_ai/browser_packaged_pages.json`

New integration map:

- `packets/product_av_ordering_ai/merchant_invention_capability_map.json`

## Commercial Positioning

The system should be sold as a merchant sovereignty layer, not as another AI
chatbot or ordering kiosk.

Best pitch:

```text
讓雲端 AI 負責親切與聰明，讓本地權威負責正確與可執行。
```

Engineering pitch:

```text
Every AI output becomes a candidate packet. Every merchant-impacting action
requires local reconstruction, deterministic verification, and an evidence seal.
```
