# 8D ADI Order: GST V2.1 簽章回執與自動退場收斂

Run-ID: gst-v21-commander-closeout-20261023T060551Z
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: 2026-10-23T06:12:53.733723+00:00
Owner-ref: CURRENT_EXPLICIT_FOUNDER_REQUEST_20261023
Effect-class: E5

## D1 Intent
完成真人簽章與規格對帳、如實登錄工作證據、釋放 9122，以及重用原生驗簽核心的單次手機入口。

## Verified facts
- [FACT|OBSERVED_DIRECT] taiji01 root and current four dirty paths observed at 2026-10-23T06:05:51Z; existing changes preserved.
- [FACT|OBSERVED_DIRECT] Quick signer omits cryptographic verification before writing formal-effect labels. | source: tools/w7tp_founder_sign.py | hash: 73038d6fd1f6d49bde4ddad7ca4d00668a62341fcfc32302b00572565080f892
- [FACT|OBSERVED_DIRECT] The native capture core calls Fido2Server.authenticate_complete and preserves raw proof append-only; origin/lifetime checks need targeted hardening. | source: tools/gst_mobile_approval_first.py | hash: 1854d8a938f6e396bd7beafd1a7f62439de88e92888dab7f3f7da1a02f5b3678

## Materials
- Allowed: existing user-owned repository source and public verification material | licence: USER_AUTHORIZED_INTERNAL_WORK | checked: 2026-10-23T06:12:53.733723+00:00
- Excluded: private keys, member plaintext, raw proof in model output, unrelated service configuration.

## Build specification
- Reuse gst_mobile_approval_first.py verification; remove independent quick-signer verification implementation.
- Every factual receipt binds the actual raw proof SHA-256 and separates cryptographic verification from Founder identity and formal effect.
- Preserve existing SIGNED_APPROVAL.json; no fresh challenge when a valid saved proof satisfies the fixed contract.
- Exact origin, RP, challenge, lifetime and immutable contract/spec hashes; no historical HEAD lock.
- Single-shot server owns only loopback 9122 and its temporary Tailscale endpoint; clean up in finally.
- No root-key-only or machine-declared ratification.

## Budget fuse
- Limit: 6 integrated_validation_attempt
- Stop condition: preserve evidence on a repeated same-cause failure; independently authorized work continues.

## Acceptance
- [ ] AC-1: Original proof independently verifies and exact specification SHA remains stable. | evidence: evidence/signature-audit.json
- [ ] AC-2: Receipt and correction reflect observed facts, preserve preimages, and do not assert unproven formal effect. | evidence: evidence/reconciliation-readback.json
- [ ] AC-3: 9122 is released, temporary proxy removed, and permanent 8444 baseline preserved. | evidence: evidence/runtime-cleanup.json
- [ ] AC-4: Reused native signing path rejects tampered signature, wrong origin, mismatched contract, expiry, and replay side effects. | evidence: evidence/validation.json
- [ ] AC-5: Actual saved-proof flow writes/readbacks a factual receipt; single-shot cleanup is measured under one second in bounded server validation. | evidence: evidence/single-shot-timing.json
- [ ] AC-6: Existing dual ledgers record this factual event once and both chains are read back. | evidence: evidence/ledger-readback.json

## Non-goals
- No canonical definition change, new role/root, machine private-key signing, Git commit/push, or unrelated task restart.
- A new phone biometric interaction and its three-second human duration are not inferred from a server test.

## D2-D8 projection
- D2 STATE: actual files, actual proof and conflicting receipts are audited in this one run.
- D3 COORDINATE: taiji01; root /home/taiji_admin/Taiji_Hub; current branch/HEAD recorded only as evidence.
- D4 EVIDENCE: SHA-256 bindings, original public-key verification, targeted tests, ledger readback.
- D5 EXECUTION_POLICY: current explicit user authorizes engineering changes; source preimages and metadata history retained.
- D6 GENERATIVE_TRANSMISSION: NOT_CLAIMED for file carriage and Git observation; GST core is unchanged.
- D7 RED_TEAM_RISK_CONFINEMENT: do not execute unverified signer; no proof replacement or 8444 outage.
- D8 ENVELOPE_AUTHORITY: engineering action authorized in this request; formal effect depends on exact native evidence and is not self-issued.
