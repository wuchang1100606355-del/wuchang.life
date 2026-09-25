# W7TP Dual Module Property Merchant Governance Demo Spec

STATE=W7TP_DUAL_MODULE_PROPERTY_MERCHANT_GOVERNANCE_DEMO_SPEC_READY
AUTHORITY=TOTAL_FIELD
MODE=CANDIDATE_ONLY_NO_LIVE_WRITE

## Purpose

This candidate spec connects the property organization container and merchant organization container as a Total Field governance demo. It is not a live Odoo deployment, not a production UI, and not an authority source.

## Dual Module Boundary

The dual module candidate contains:

- property organization container refs.
- merchant organization container refs.
- committee authorization status.
- merchant public projection status.
- service request refs.
- Total Field decision refs.

Property and merchant modules may exchange candidate service context by ref. They cannot share resident details, member plaintext, raw images, private contact data, raw credentials, or hidden review notes.

## 8 State Field Completion

Every dual-module governance packet must expose these keys with `summary`, `refs`, and `status`:

| Key | Field | Required content |
| --- | --- | --- |
| `intent_field` | 意圖場 | property-to-merchant service request or governance intent |
| `state_field` | 狀態場 | candidate, hold, warning, block, or pass-safe-contact state |
| `coordinate_field` | 座標場 | property container ref, merchant container ref, service area ref, or role ref |
| `evidence_field` | 證據場 | public source refs, consent refs, event refs, hash refs, or seal refs |
| `execution_field` | 執行場 | no live write, no release, no restart, no router write |
| `generative_transport_field` | 生成式傳輸場 | `mode=state_packet_ref_reconstruction_equivalent_state` |
| `risk_field` | 風險禁錮場 | no secret, no member plaintext, no resident plaintext, no raw image, no DB write, no release, no restart, no router write |
| `envelope_field` | 封套驗證場 | `final_authority=total_field_verifier`, `human_review_required=true`, `candidate_only=true` |

The generative transport field must set:

```text
mode=state_packet_ref_reconstruction_equivalent_state
not=file_copy/cloud_sync/plaintext_transport
```

## Cloud Boundary

Cloud support may draft candidate wording, candidate notices, and candidate summaries. Cloud support cannot activate a merchant, approve a committee, release access control, read resident details, or change Total Field decisions.

## Default Decision

Dual-module projections default to `HOLD` until public source review, organization identity review, consent or application ref, privacy review, human review, and activation packet sealing pass.

## Safety

```text
NO_SECRET=TRUE
NO_MEMBER_PLAINTEXT=TRUE
NO_RESIDENT_PLAINTEXT=TRUE
NO_RAW_IMAGE=TRUE
NO_RAW_KEY_TOKEN_PASSWORD=TRUE
NO_DB_WRITE=TRUE
NO_DEPLOY=TRUE
NO_RESTART=TRUE
NO_ROUTER_WRITE=TRUE
CANDIDATE_ONLY=TRUE
FINAL_AUTHORITY=total_field_verifier
```
