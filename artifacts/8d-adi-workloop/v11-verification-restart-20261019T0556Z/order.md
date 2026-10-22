# 8D ADI Order: V11驗證程序重啟

Run-ID: v11-verification-restart-20261019T0556Z
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: 2026-10-19T05:55:42.777405+00:00
Owner-ref: UNKNOWN_UNVERIFIED
Effect-class: E2

## D1 Intent
依目前使用者明示，重用既有9122與iPhone公鑰開啟新驗證請求，保留原V11證據；不授予D8或D4

## Verified facts
- [DEFINITION|DECLARED_ONLY] Founder/member intent supplied for this run | source: intent-envelope.json | hash: NONE

## Materials
- Allowed: user-authorized project evidence | licence: NOT_APPLICABLE | checked: 2026-10-19T05:54:34+00:00
- Excluded: raw credentials and protected member plaintext | reason: protected context boundary

## Build specification
- artifact directory = artifacts/8d-adi-workloop/v11-verification-restart-20261019T0556Z | source: intent-envelope.json#run_id

## Budget fuse
- Limit: 2 attempt
- Stop condition: stop at or before limit and preserve evidence

## Acceptance
- [ ] AC-1: historical signature independently reverified and original files preserved | evidence: evidence/validation.json
- [ ] AC-2: successor request pinned to same task/key/effects and fresh time without old-signature reuse | evidence: evidence/validation.json
- [ ] AC-3: existing 9122 verification entry exposes successor and requires human FaceID | evidence: evidence/live-readback.json

## Non-goals
- live, protected, formal, ADI, canonical, pointer, identity, Seat, or database mutation

## D2-D8 projection
- D2 STATE: UNKNOWN_UNVERIFIED current and target state
- D3 COORDINATE: artifacts/8d-adi-workloop/v11-verification-restart-20261019T0556Z at 2026-10-19T05:54:34+00:00; ADI range unresolved
- D4 EVIDENCE: intent-envelope.json; further evidence required
- D5 EXECUTION_POLICY: candidate artifact only; rollback this unpromoted run directory
- D6 GENERATIVE_TRANSMISSION: NOT_CLAIMED; carrier is not W7TP
- D7 RED_TEAM_RISK_CONFINEMENT: three red-team event coordinates not yet run
- D8 ENVELOPE_AUTHORITY: candidate only; Total Field decision NOT_REVIEWED
