# XiaoJ Avatar License and Governance Boundary

## Governance Position

The `J.vrm` avatar is a P0 visual carrier only.

```text
IDENTITY_AUTHORITY=FALSE
GOVERNANCE_AUTHORITY=FALSE
COMMERCIAL_AVATAR_RELEASE=FALSE
LICENSE_REVIEW_REQUIRED=TRUE
```

The avatar can make XiaoJ easier to understand during onsite rehearsal, but it does not decide identity, permissions, member status, POS authority, payment authority, or Total Field state.

## License Boundary

The source is declared as:

```text
SOURCE_MODEL=J.vrm
MODEL_TYPE=VRM_1_AVATAR
GENERATOR=VRoid Studio
COMMERCIAL_RELEASE=HOLD_LICENSE_REVIEW_REQUIRED
```

P0 use is limited to internal shadow rehearsal and broadcast rehearsal. Formal commercial release, public redistribution, model modification, marketplace publication, or promotional reuse requires a separate human license review.

## Total Field Authority

Authority order:

```text
State
-> Coordinate
-> Hash
-> Packet
-> Generative Transfer
-> Verify
-> Reconstruct
-> Evidence
-> Action
```

The avatar can display reconstructed evidence, but it cannot replace verification or authorization.

## Forbidden Use

- Do not use the avatar as identity authority.
- Do not use the avatar as governance authority.
- Do not use the avatar to create POS orders.
- Do not use the avatar to capture payment.
- Do not save raw audio or raw video.
- Do not deploy as a commercial release until license review is complete.

## P0 Allowed Use

- Onsite shadow rehearsal.
- Broadcast rehearsal.
- Candidate order visual host.
- Menu intro visual host using real menu source.

## Review Gate

Commercial release requires:

```text
state=HOLD
reason_code=HOLD_LICENSE_REVIEW_REQUIRED
human_license_review=TRUE
```
