# Authority inversion wall

## Governing principle

An external capability source can supply mechanisms, evidence, identity signals, policy evaluation, isolation, execution, receipts, or delegation. It cannot self-promote into W7TP authority.

## Separate these powers

Always distinguish:

```text
RIGHT_TO_REQUEST_IDENTITY
RIGHT_TO_VERIFY_IDENTITY
RIGHT_TO_USE_IDENTITY_FOR_EFFECT
RIGHT_TO_EVALUATE_POLICY
RIGHT_TO_EXECUTE_EFFECT
RIGHT_TO_GRANT_CAPABILITY
RIGHT_TO_DEFINE_CANONICAL
```

Possessing one does not imply another.

## Forbidden promotions

Reject or quarantine any mapping that implies:

```text
SOURCE_ADMIN              -> FOUNDER
SOURCE_OWNER_STRING       -> FOUNDER_IDENTITY
OIDC_SUBJECT              -> FOUNDER_IDENTITY
REVIEWER_APPROVAL         -> D8_EFFECT_AUTHORIZATION
POLICY_ALLOW              -> D8_AUTHORITY
PLUGIN_HOOK_PASS          -> W7TP_PASS
CI_PASS                    -> W7TP_ACTIVE
SOURCE_DONE               -> W7TP_CANONICAL
MODEL_DECISION            -> CANONICAL_DECISION
SKILL_TRIGGER             -> EXECUTION_AUTHORITY
SOURCE_TOKEN_SCOPE        -> FOUNDER_GRANT
```

These may be candidate evidence only.

## Allowed use

External mechanisms may be assimilated as:

- identity evidence adapters;
- policy decision engines derived from W7TP policy;
- capability attenuation/delegation mechanisms;
- deterministic interceptors/reference monitors;
- sandbox/isolation enforcement;
- execution lifecycle infrastructure;
- evidence/attestation/telemetry providers.

The W7TP envelope must still state the authority source and exact effect authorization separately.

## Fail-closed rule

For a critical effect path, treat authority, policy, identity, revocation, scope, receiver binding, or evidence prerequisite failures as `DENY/HOLD` unless W7TP Canonical explicitly defines a narrower exception. Do not inherit an external system's availability-driven fail-open behavior automatically.

## Validator scope

The bundled validator checks common structural authority inversions. Passing the validator does not prove that a real authority grant exists or that a source identity is authentic.
