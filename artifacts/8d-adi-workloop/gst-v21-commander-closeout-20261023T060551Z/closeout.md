# taiji01 GST V2.1 簽章、回執與單次退場對帳
Status: DONE

Scope: D5 engineering and factual evidence closeout. Formal canonical effect remains NOT_AUTHORIZED.

- [PASS] AC-1: Original real WebAuthn proof independently and natively verified; specification and codec unchanged. | evidence: evidence/signature-audit.json
- [PASS] AC-2: Original preimages preserved, malformed JSON corrected, exact signed candidate canonical record restored, and truthful receipts read back. | evidence: evidence/manifest-reconciliation.json
- [PASS] AC-3: 9122 has no listener or temporary proxy; zero related signing processes or Python zombies; 8444 HTTPS 200 and configuration preserved. | evidence: evidence/final-runtime-and-git-readback.json
- [PASS] AC-4: 14 isolated regressions pass, including altered assertion, origin, challenge, lifetime, replay, CAS and proxy ownership. | evidence: evidence/integration-test-2.json
- [PASS] AC-5: Actual existing-proof receipt path succeeded and bounded server cleanup was below one second; actual Tailscale transport/cleanup separately measured 31.126 ms. | evidence: evidence/actual-proxy-cleanup-test.json
- [PASS] AC-6: One factual event appears once in each existing ledger, and both complete chains pass readback. | evidence: evidence/dual-ledger-readback.json

Independent functional verification: Separate direct Fido2Server public-key verification of original raw evidence and actual live CLI execution. | evidence: evidence/signature-audit.json

## Observed boundaries
- No new phone biometric ceremony was run; neither biometric method nor a three-second human interaction duration is attested.
- The native tool scope is the fixed GST V2.1 contract. Other contracts are rejected pending an exact governed native binding.
- Formal Founder role binding, canonical promotion and runtime activation are not asserted.
- The old immutable DONE action has an inconsistent RESUME_FROM. Its historical denial and bytes are preserved; native task-context registration remains a local hold.
- The user attachment was read and cross-checked against the live Universal8DFileEngine receipt and source hashes; its later developments remain intact. Receipt claims do not become fresh runtime verification.
- Git local HEAD and remote branch are equal at 3594b4e8292d537ff8d111e44c70c4fc6f177b39; no commit or push was performed.

## NEXT
Existing native Total Field authority adjudication of saved human evidence and precise Founder binding; preserve formal-effect pending until a verifiable native decision exists. No duplicate phone signature is needed for the current captured contract.
