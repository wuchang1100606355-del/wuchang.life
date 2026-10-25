# Mandatory red-team, HOLD, and authorization

## Non-skippable stages

Every skill records:

1. `RED_TEAM_PRE_DEFINITION`
2. `RED_TEAM_PRE_ACTIVATION`
3. `RED_TEAM_POST_OPERATION`

Mark a stage `NOT_APPLICABLE_WITH_EVIDENCE` only when the manifest effect and requested run prove it does not apply. Founder approval, prior PASS, canary, provider output, installation, or an existing model cannot waive an applicable stage.

## Required perspectives

Test:

- false product promise, unusable output, misleading natural-language PASS, or missing acceptance evidence;
- hidden duplicate skill, alias drift, overly broad multi-purpose skill, or wrong effect class;
- Seat overflow, duplicated occupancy, reservation misuse, member/XiaoJ/profile mismatch, or cached-session survival after transfer;
- prompt injection, retrieved-data instruction injection, context poisoning, missing provenance, stale evidence, or cross-member mixing;
- candidate that emits ALLOW, commit, TFS, TFID, canonical pointer, formal hash, or direct action authority;
- protected-data exposure, credential material, ADI, H64-TD, raw member content, or provider-boundary leakage;
- wrong node, carrier/protocol confusion, replay, TTL failure, dependency substitution, image drift, or resource escape;
- floating-point data promoted into identity or decision authority; undeclared representation, precision, units, coordinate basis, rounding, serialization, tolerance, or non-finite-value policy; or missing deterministic cross-receiver replay evidence;
- ordinary transfer, compression, sync, encryption, prompt generation, or model output mislabeled as W7TP;
- effect equivalence, shared carriers, shared protocols, similar interfaces, or performance outcomes mislabeled as technical identity;
- a weighted or floating identity score, E0-E5 reused as evidence levels, or an incomplete six-axis technology comparison;
- ordinary optimization mislabeled as structural elimination, or carrier semantics collapsed into reconstruction and verification semantics;
- a technology-identity candidate presented as novelty, patentability, infringement, legal status, or global superiority;
- missing verifier, packet-carried verification, rollback, cleanup, evidence, suspension, or retirement behavior;
- live DB, deploy, restart, router, payment, formal submission, identity, Seat, canonical, or pointer effect hidden below E5.

## Finding decision

- Open `HIGH` or `CRITICAL`: HOLD and no activation or state-changing execution.
- `MEDIUM`: mitigate or cite an exact active bounded policy that accepts the residual risk.
- `LOW`: may enter a reversible, isolated, hash-bound remediation bundle.
- Authorization never turns invalid protocol, identity mismatch, protected-data leakage, authority injection, hash drift, or failed product acceptance into PASS.
- Close findings only with evidence and rerun only affected checks plus the applicable red-team stage.

## Natural-language HOLD

Return both stable machine evidence and a Traditional-Chinese response:

```json
{
  "hold_code": "ROLE_SEAT_UNAVAILABLE",
  "human_response": {
    "question": "為什麼這個小J現在不能使用這項技能？",
    "answer": "此角色的固定位置目前沒有一個有效 Seat 綁定到這位會員的小J，因此系統沒有啟動技能。",
    "risk_found": "若略過 Seat，可能讓其他身分取得不屬於他的資訊或工具。",
    "possible_effect": "可能造成跨會員存取或權限擴張。",
    "protected_state": "既有 Seat、會員資料、服務及正典均未改變。",
    "solution": "建立一份只變更指定 Seat 的綁定候選，交由總場與 Founder 確認。",
    "user_action_required": true,
    "authorization_request": "BOUND_REQUEST_REF"
  }
}
```

Give one solution, not a diagnostic menu. Do not require the user to find paths, hashes, line numbers, or terminal output that automation can resolve.

## Authorization request

Bind requests to exact identity, Seat, action, node, target, input/manifest hashes, expected effect, maximum effect, affected state, risks, safeguards, rollback, stop conditions, single use, expiry, and Total Field review. Ask one clear yes/no question only after explaining the effect and risk.

Never request blanket shell access, reusable secrets, all-node authority, unrestricted member data, open-ended deployment rights, or permission to suppress future HOLD decisions.
