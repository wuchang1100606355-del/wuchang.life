# Member Sovereignty Non-Override Policy

STATE=MEMBER_SOVEREIGNTY_NON_OVERRIDE_POLICY_V1
DATE=2026-06-29
ROOT=/home/taiji_admin/Taiji_Hub

## 0. Total Field Answer

The user's statement is accepted as a Total Field boundary rule.

```text
Member sovereignty cannot be replaced by Total Field, the association, AI,
administrators, or candidate brains.
```

Total Field authority is safety and governance authority. It is not member consent authority.

## 1. Positive Authority Scope

The system may:

- verify whether a flow is structurally safe;
- block privilege escalation;
- block plaintext leakage;
- block automatic payment or deduction;
- block unauthorized disclosure;
- require explicit confirmation by the member;
- seal evidence, risk decisions, and review records.

## 2. Forbidden Substitution

The system must not:

- authorize on behalf of a member;
- refuse authorization on behalf of a member;
- infer consent from silence, membership status, device presence, role, or Total Field acceptance;
- use Total Field authority to override member sovereignty;
- treat `safe_to_process=true` as `member_consented=true`;
- treat verifier `ACCEPTED` as member consent;
- treat administrator approval as member consent;
- treat association governance as member consent;
- treat AI confidence as member consent.

## 3. Required Separation

Every member-sensitive flow must separate these states:

```text
flow_is_safe
member_identity_verified
member_consent_required
member_consent_granted
member_consent_denied
member_consent_revoked
```

Allowed implication:

```text
member_consent_granted -> flow may proceed only if verifier also accepts
```

Forbidden implication:

```text
verifier_accepts -> member_consent_granted
flow_is_safe -> member_consent_granted
admin_approves -> member_consent_granted
association_approves -> member_consent_granted
AI_recommends -> member_consent_granted
```

## 4. Verifier Rule

If a packet requests or implies proxy consent, the verifier must return BLOCK or HOLD:

- `proxy_member_authorization`
- `proxy_member_refusal`
- `assumed_member_consent`
- `safe_processing_as_consent`
- `total_field_overrides_member_sovereignty`
- `admin_overrides_member_sovereignty`
- `association_overrides_member_sovereignty`
- `candidate_brain_overrides_member_sovereignty`

Default decision:

```text
BLOCK_MEMBER_SOVEREIGNTY_OVERRIDE
```

Exception:

```text
HOLD_MEMBER_CONFIRMATION_REQUIRED
```

only when the flow is merely preparing a member-facing confirmation request and does not assert consent.

## 5. Product Language Rule

The UI and PR layer must say:

```text
此流程已通過安全檢查，但仍需要會員本人明確確認。
```

It must not say:

```text
總場已同意，所以會員已同意。
協會已同意，所以會員已同意。
管理員已同意，所以會員已同意。
AI 判斷可行，所以會員已同意。
安全可處理，所以會員已同意。
```

## 6. Audit Rule

Audit records must record consent separately from safety:

- `flow_safety_decision`
- `member_consent_state`
- `member_confirmation_ref`
- `member_confirmation_timestamp`
- `revocation_available`
- `evidence_ref`
- `verifier_ref`

If explicit member confirmation is absent, the record must remain:

```text
member_consent_state=required
```

or:

```text
member_consent_state=unknown
```

never:

```text
member_consent_state=granted
```

## 7. Hardwall Flags

```text
member_sovereignty_non_override=true
total_field_is_not_member_consent=true
association_is_not_member_consent=true
admin_is_not_member_consent=true
ai_is_not_member_consent=true
candidate_brain_is_not_member_consent=true
safe_to_process_is_not_consent=true
explicit_member_confirmation_required=true
consent_revocation_supported=true
```
