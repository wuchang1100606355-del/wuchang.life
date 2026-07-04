# W7TP User Experience And Cloud Minimality Policy

Status: product-grade total-field frontend policy / candidate-only  
Scope: `8D加密式主權AI`, XiaoJ controlled browser, 0.5-2B LLM frontend, cloud-candidate total-field norms  
Authority: product and governance policy; not legal, patent, accounting, or production security advice

## Core Requirement

```text
使用者體驗不可低於雲端。
雲端依賴需又精準、又低、又無可回推。
```

This is a product-grade hard rule for `8D加密式主權AI`.
English canonical frontend name: `8D_ENCRYPTED_SOVEREIGN_AI`.

The local user interface may be powered by a 0.5-2B LLM and controlled browser, but the member-facing experience must not feel weaker, slower, rougher, less helpful, or less polished than a normal cloud AI interface.

Cloud can assist, but cloud must never become the authority or a user-reconstruction surface.

This belongs to the ten-year / 十年總場 invention lineage and preserves total-field governance framing.
It is not an ordinary cloud UI policy and not an ordinary cloud proxy pattern; it is a total-field user sovereignty rule.

## UX Rule

The user-facing frontend must preserve:

- cloud-grade response polish,
- elder-friendly clarity,
- smooth confirmation flow,
- low-friction controlled browser actions,
- consistent XiaoJ service tone,
- fast local first response,
- graceful cloud candidate augmentation when needed,
- no visible privacy burden unless confirmation is required.

The product must not excuse poor UX by saying "local model is small."
The 0.5-2B LLM is the local control and intent layer, not the full experience ceiling.

## Cloud Dependency Rule

Cloud dependency must satisfy all three gates:

| Gate | 中文 | Requirement |
| --- | --- | --- |
| `PRECISE` | 精準 | Send only the bounded missing capability, target schema, and redacted task scope needed for the current candidate. |
| `LOW` | 低 | Minimize token volume, frequency, provider exposure, latency, cost, and retained references. Prefer local cache, local grammar, local templates, and small model routing first. |
| `NON_INFERABLE` | 無可回推 | Cloud must not receive enough information to reconstruct the user, member identity, raw browser state, health/care context, payment context, exact household context, or persistent cross-session behavior. |

If any gate fails:

```text
HOLD_REQUIRED
reason = "cloud_dependency_not_precise_low_non_inferable"
```

## Allowed Cloud Candidate Payload

Allowed cloud-bound material:

- bounded task intent ref,
- redacted intent summary,
- output schema ref,
- language / accessibility preference bucket ref,
- non-identifying service category,
- coarse route or scene class,
- cost bucket ref,
- one-time packet hash,
- short TTL nonce,
- candidate-only instruction.

Forbidden cloud-bound material:

- member plaintext,
- member name, phone, address, ID number,
- raw browser page,
- raw clickstream,
- raw chat history,
- cookies, OAuth tokens, API keys,
- raw health or care details,
- exact household location,
- exact payment data,
- stable cross-session user identifier,
- full Odoo record,
- proprietary total-field rule table.

## Non-Inference Rule

`無可回推` means cloud output or cloud provider logs must not be able to infer:

- who the user is,
- where the user lives,
- what exact page they saw,
- what exact form they filled,
- what care or health condition exists,
- what payment or identity data exists,
- which stable member profile generated the request,
- how to rebuild the total-field decision logic.

Required techniques:

- ref-only packaging,
- coarse buckets instead of exact values,
- one-shot nonce and short TTL,
- HMAC or hash refs instead of raw identifiers,
- no cross-session stable cloud identity,
- no raw browser page transfer,
- no member plaintext transfer,
- no provider-side authority,
- local verifier gate after cloud return.

## Product Architecture

```text
0.5-2B local LLM
  -> fast intent / language / confirmation candidate
controlled browser
  -> dry-run visible action candidate
cloud candidate norms
  -> precise low non-inferable augmentation only when needed
8D encrypted packet
  -> total-field verifier
```

This architecture allows the user to feel cloud-grade assistance while the system keeps cloud dependency minimal and non-reconstructive.

## Acceptance Criteria

- UX target is cloud-grade or better for the supported task surface.
- Local first response is available even when cloud is unavailable.
- Cloud call is optional per task and must be justified by bounded capability need.
- Cloud request contains no member plaintext, no raw browser page, no secrets, no stable user identifier.
- Cloud return remains `candidate_only=true`, `must_not_execute=true`, and `requires_total_field_verify=true`.
- Total field can reject the cloud result without breaking the user-facing flow.
- Audit stores refs, hashes, buckets, TTL, and decision state, not raw cloud prompt content.

## Safe Summary

```text
體驗要像雲端，權威仍在總場；
雲端只補精準候選，依賴要低，資料不可回推。
```

## Safety Flags

UX_BELOW_CLOUD_BASELINE=HOLD  
CLOUD_DEPENDENCY_PRECISE=TRUE  
CLOUD_DEPENDENCY_LOW=TRUE  
CLOUD_DEPENDENCY_NON_INFERABLE=TRUE  
CLOUD_AUTHORITY=CANDIDATE_ONLY  
MEMBER_PLAINTEXT_TRANSFER=FALSE  
RAW_BROWSER_PAGE_TRANSFER=FALSE  
STABLE_CLOUD_USER_ID=FALSE  
REQUIRES_TOTAL_FIELD_VERIFY=TRUE  
