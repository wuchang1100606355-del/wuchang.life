# taiji01 Metric Identity Gateway Container

This container is the official taiji01 local identity gateway for Windows/WSL frontend LLM access.

Flow:

Windows / WSL frontend -> taiji01:11435 -> identity five-code allowlist from Odoo mapping -> taiji01 Ollama 127.0.0.1:11434.

Sovereign developer-member candidate flow:

Google member login -> existing provider-subject link plus local identity/qualification
verification -> short-lived member sovereign packet ->
`POST /w7tp/member-sovereign/total-field-candidate` -> existing Total Field
candidate core.

The candidate route requires all of the following:

- direct LAN/Tailscale client identity from the existing allowlist;
- no `X-Forwarded-For` identity substitution;
- an existing Google link state of `PROVIDER_LINK_FOUND` or `LINK_CONFIRMED`;
- `system_operator` in the member sovereign packet;
- at least one locally issued role reference;
- the exact `sovereign_ai_candidate_submission` scope;
- a closed `LLM_PUSH` candidate request no larger than 256 KiB.

Google is one verification channel, not the natural-person authority source.  A
privileged packet must be issued locally from already verified Odoo authority
facts after the configured identity/qualification checks converge.  The public
`/issue` interface rejects any caller-supplied `system_operator` or
`sovereign_ai_candidate_submission` claim, so a laptop cannot manufacture its
own developer authority.

Natural-person adjudication is three-state.  Complete positive identity and
authority evidence may allow; missing or incomplete evidence holds without
labeling the operator an impostor; `BLOCK_NOT_NATURAL_PERSON` requires an
opaque server-local red-team contradiction evidence reference.  Absence of
such negative proof never converts an incomplete check into either a rejection
or a privileged allow.

For this privileged candidate path, the existing D4 local qualification source
references must include opaque SHA-256 verifier references for usage pattern,
login-location pattern, trusted device, and connection pattern.  Raw location,
IP address, device fingerprint, and behavior history never enter the packet.
An absent or anomalous factor holds for step-up verification; no single factor
proves impersonation by itself.

The source package deliberately leaves the process-local privileged-member
verifier unbound.  Until the existing Odoo natural-person and authority source
is connected inside the server process, privileged submissions return HOLD.
A caller-supplied packet, current-state object, Google result, or red-team claim
cannot replace that verifier.  Identity BLOCK requires its server-local opaque
`red-team-contradiction` evidence reference.

When the process-local verifier determines that high-assurance re-verification
is necessary, it may return the step-up method
`w7tp_privacy_preserving_no_retention_image`.  This is an opaque W7TP verifier
contract, not ordinary image authentication: the 8D packet, gateway request,
LLM, response, and audit log must never receive or retain an image, frame,
selfie, face template, or biometric template.  Only a non-reversible local
verifier result reference may return to D4.  This package exposes the HOLD
contract and rejects image-shaped payloads; it does not invent or embed an
image-verification engine.

One 8D member packet may carry the complete currently verified scope vector and
its opaque evidence references.  It never carries a wildcard permission.  Each
downstream operation must request an exact subset and pass the current-state,
purpose, target, consent, expiry, hash, and local verifier gates again.  Missing
or conflicting natural-person or authority evidence therefore fails closed.

The route never creates or email-merges a member, never grants a role, and never
accepts a laptop claim of super-admin authority.  Existing administrator or
developer authority may enter only as an opaque local role reference already
issued by the member authority source.  The response contains decision codes
and hashes only; it never returns the candidate value or previous value and
always fixes production commit, seal, execution authority, DB write, deploy,
restart, router write, and external network call to false.

Identity source:

- `/home/taiji_01/Taiji_Hub/Taiji_Odoo/identity_map/five_code_identity_allowlist.json`
- This file is the Odoo direct mapping export / projection point.
- The gateway treats it as read-only.

Container hardening:

- host network only for local Tailscale bind
- read-only filesystem
- no-new-privileges
- all Linux capabilities dropped
- memory databases mounted read-only
- audit log mounted read-write

No secrets, tokens, service account JSON, or member plaintext are included.

This source package does not activate itself.  Build, deployment, restart, DNS,
router, tailnet-policy, Odoo database, and canonical changes remain separate
explicitly authorized operations.
