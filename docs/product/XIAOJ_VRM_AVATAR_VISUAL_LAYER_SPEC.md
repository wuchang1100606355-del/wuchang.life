# XiaoJ VRM Avatar Visual Layer Spec

## State

P0 target: `XIAOJ_AVATAR_P0_READY`

Current avatar reference:

```text
AVATAR_REF=assets/xiaoj/avatar/J.vrm
MODEL_TYPE=VRM_1_AVATAR
GENERATOR=VRoid Studio
AVATAR_ROLE=VISUAL_CARRIER_ONLY
IDENTITY_AUTHORITY=FALSE
GOVERNANCE_AUTHORITY=FALSE
COMMERCIAL_RELEASE=FALSE
LICENSE_REVIEW_REQUIRED=TRUE
```

The avatar is a visual carrier for XiaoJ P0 shadow rehearsal only. It may host menu introduction, candidate order rehearsal, and broadcast rehearsal, but it must not become an identity authority, governance authority, POS writer, payment actor, or commercial release asset.

## Coordinate

Allowed P0 surfaces:

| Surface | Allowed | Boundary |
| --- | --- | --- |
| Onsite shadow rehearsal | Yes | Human-supervised practice only |
| Broadcast rehearsal | Yes | Internal rehearsal only |
| Candidate order visual host | Yes | Candidate display only, no POS write |
| Menu intro visual host | Yes | Real menu wording only |
| Commercial release | No | HOLD until license review |
| Identity authority | No | XiaoJ avatar cannot identify a person |
| Governance authority | No | Total Field verifier remains authority |

## Packet

The avatar state packet is non-executable and evidence-bound:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "XiaoJ Avatar State Packet P0",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "packet_type",
    "avatar_ref",
    "avatar_role",
    "visual_state",
    "spoken_text_ref",
    "candidate_order_ref",
    "human_supervision",
    "must_not_execute",
    "pos_write_allowed",
    "payment_allowed",
    "license_review_required"
  ],
  "properties": {
    "packet_type": { "const": "XIAOJ_AVATAR_STATE_PACKET_P0" },
    "avatar_ref": { "const": "assets/xiaoj/avatar/J.vrm" },
    "avatar_role": { "const": "VISUAL_CARRIER_ONLY" },
    "visual_state": {
      "type": "string",
      "enum": ["idle", "listening", "confirming", "rehearsing", "hold"]
    },
    "spoken_text_ref": { "type": "string" },
    "candidate_order_ref": { "type": "string" },
    "human_supervision": { "const": true },
    "must_not_execute": { "const": true },
    "pos_write_allowed": { "const": false },
    "payment_allowed": { "const": false },
    "license_review_required": { "const": true }
  }
}
```

## Verify

P0 viewer plan:

1. Load `assets/xiaoj/avatar/J.vrm` only after file presence is confirmed.
2. Bind avatar expressions to local candidate states only.
3. Display candidate order text as uncommitted rehearsal text.
4. Require human confirmation before any downstream operation.
5. Keep POS write, payment capture, Odoo DB write, deployment, and commercial release disabled.

## Evidence

P0 is ready only when:

```text
AVATAR_FILE_REGISTERED=TRUE
AVATAR_VIEWER_SPEC_CREATED=TRUE
AVATAR_STATE_PACKET_DEFINED=TRUE
LICENSE_BOUNDARY_DOCUMENTED=TRUE
```

If `assets/xiaoj/avatar/J.vrm` is missing, the correct state is:

```text
STATE=HOLD_XIAOJ_VRM_AVATAR_NOT_READY
REASON=AVATAR_FILE_MISSING
```
