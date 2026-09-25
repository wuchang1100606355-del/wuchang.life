# Evidence Record Package Index

CHECK_DATE=2026-06-27
LEGAL_REVIEW_NEEDED=TRUE
PUBLIC_FILING_POLICY=Use only public-safe summaries, sealed hashes, commit references, and non-sensitive architecture descriptions in TIPO documents.

## Core Evidence Map

### PUBLIC_FILING_SAFE

These items can support the public patent draft after counsel review and redaction:

| Evidence Item | Repo Path / Commit | Filing Use |
| --- | --- | --- |
| True 8D TIPO main draft | docs/patent_delivery/V4_TRUE8D_TIPO_MAIN.md; commit f2b259c | Main specification basis |
| True 8D claims draft | docs/patent_delivery/V4_TRUE8D_CLAIMS.md; commit f2b259c | Claim drafting basis |
| True 8D abstract draft | docs/patent_delivery/V4_TRUE8D_ABSTRACT.md; commit f2b259c | Abstract basis |
| Productized sovereign AI evidence item | docs/patent_delivery/PROPERTY_SOVEREIGN_AI_PRODUCTIZED_VIRTUALIZATION_EVIDENCE_ITEM.md; commit f2b259c | Public-safe technical context after review |
| Generative transmission v2 spec | docs/total_field/W7TP_GENERATIVE_TRANSMISSION_V2_SPEC.md; commit 346842b | Packet/ref/hash/manifest/reconstruction/verifier technical basis |
| Total Field verifier contract | docs/total_field/TOTAL_FIELD_VERIFIER_CONTRACT_V1.md; commit 346842b | Verifier-gated output basis |
| Hard walls contract | docs/total_field/HARD_WALLS_CONTRACT_V1.md; commit 346842b | Safety boundary basis, public summary only |
| Canonical 8D verifier spec | docs/total_field/CANONICAL_8D_VERIFIER_SPEC.md; commit 346842b | 8D validation and state-machine basis |
| Intent-state packet ledger spec | docs/total_field/INTENT_STATE_PACKET_LEDGER_SPEC_V1.md; commit 346842b | D8 envelope/packet ledger basis |
| GT 5GiB equivalent benchmark evidence | docs/evidence/generative_transfer_5gb/W3_GT_5GB_SPEED_20260622T133921Z.md; commit fe913df | Performance/equivalent-transfer evidence, public summary only |
| Patent delivery manifest | runtime/patent_delivery/ACTIVE_TW_W7TP_GT_V06.json | Delivery package state and QA gate reference |

### INTERNAL_EVIDENCE_ONLY

These items support diligence, reduction-to-practice, review traceability, or investor/patent-counsel preparation, but should not be filed as-is:

| Evidence Item | Repo Path / Commit | Reason |
| --- | --- | --- |
| D8 product patent disclosure draft | docs/product/D8_PATENT_INVENTION_DISCLOSURE_DRAFT.md; commit ba72bfe | Counsel triage; contains trade-secret boundary notes |
| D8 investor and patent brief | docs/product/D8_INVESTOR_AND_PATENT_BRIEF.md; commit ba72bfe | High-level invention disclosure; not final filing text |
| Product AV ordering architecture | docs/evidence/product_av_ordering_ai/W7TP_AUDIO_VIDEO_ORDERING_AI_ARCHITECTURE.md; commit fe913df | Product implementation context; redact domain details |
| Product AV security boundary | docs/evidence/product_av_ordering_ai/SECURITY_BOUNDARY.md; commit fe913df | Safety-boundary evidence; internal details need review |
| POS MVP evidence package | docs/evidence/pos_mvp/ and docs/evidence/pos_mvp_p2/; commit fe913df | Implementation evidence; inspect for customer or live-operation details before use |
| SDK 8D packet schema evidence | docs/evidence/sdk/8d/; commit fe913df | Schema verification reference; public-safe excerpt only |
| Operations governance runbooks | docs/operations/; commits cb36f60, 0397dac, 95b70c6 | Demonstrates safety governance; not filing-ready text |
| Product launch and risk docs | docs/product/; commits 89d033a, ba72bfe | Market/product context; avoid marketing claims in patent text |

### TRADE_SECRET_DO_NOT_FILE

- WHY_IT_RUNS lookup details.
- Full lookup tables, internal dictionaries, codebooks, private scoring weights and private rule graphs.
- Live credentials, endpoint tokens, private keys, session cookies or signed URLs.
- Private governance chain internals not necessary to enable the invention.
- Unpublished revenue, pricing, governance or partner-sensitive details.
- Full redteam prompt bodies, incident text or exploit examples beyond abstracted categories.

### NEEDS_REDACTION

- Any example containing member plaintext, phone, address, national ID, raw audio or customer-specific records.
- Any path, endpoint, database name, host name or operational config that would expose live infrastructure.
- Any evidence that includes internal account names, signatures, receipt identifiers or payment traces.
- Any benchmark package that contains raw payloads; use packet size, hash, run ID and verifier result only.
- Any screenshots or diagrams with account names, browser session data, credentials or non-public entity data.

### LEGAL_REVIEW_NEEDED

- Claim breadth over "method and system" for software/AI governance implementations.
- Novelty and inventive-step charting against AI agent orchestration, policy-as-code, human-in-the-loop, memory-augmented agents, edge/cloud inference, and patent-publication prior art.
- Whether to file one broad parent case first or split into child/divisional cases.
- Whether any disclosure has already started a grace-period clock.
- Inventorship, ownership, assignment and applicant identity.
- Whether any implementation details should remain trade secret instead of entering the public patent file.

## Commit Hash Evidence List

- f2b259c Add True 8D patent delivery package
- fe913df Add D8 evidence and governance reports
- 346842b Add clean Total Field contracts and specs
- f217ead Add remaining Total Field governance documents
- cb36f60 Add clean operations runbooks
- 0397dac Clarify Odoo DB write approval default in operations checklist
- 95b70c6 Add remaining operations governance runbooks
- 89d033a Add clean D8 product docs
- ba72bfe Add reviewed product launch and safety docs
- 1f933f8 Update repository agent governance rules

## Safety Evidence Assertions

DB_EXECUTE=FALSE
DB_WRITE=FALSE
SECRET_READ=FALSE
SECRET_VALUE_PRINTED=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

These assertions apply to this evidence-indexing task. They do not certify every historical artifact; any artifact moved from internal evidence to public filing text must receive a separate redaction review.

## Filing Package Status

PUBLIC_DRAFTS_READY_FOR_COUNSEL=TRUE
EVIDENCE_INDEX_READY=TRUE
LIVE_FILING_READY=FALSE

Missing live-filing inputs:

- Applicant and inventor data in official filing forms.
- Counsel decision on priority, grace period, inventor list, applicant ownership, representative drawing and final claim scope.
- Final drawing/figure list.
- Final redaction pass for any evidence attached to public filing.
