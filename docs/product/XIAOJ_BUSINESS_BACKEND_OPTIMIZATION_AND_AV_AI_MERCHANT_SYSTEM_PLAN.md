# XiaoJ Business Backend Optimization and AV AI Merchant System Plan

STATE=P1_BACKEND_OPTIMIZATION_REVIEW_READY

## Purpose

This plan turns the existing XiaoJ productization, Odoo authority node, LINE/LINE WORKS gates, and total-field evaluation work into a business backend improvement roadmap for a high-quality audiovisual AI merchant system.

The system must improve business operation without interrupting the cafe's current manual operation. It must also respect the current local reality: the cafe is active, the association depends on cafe operating cashflow, Sanchong community self-funding is not yet mature, and the founder mission needs to become sustainable beyond single-person burden.

## Target Outcome

The target backend is not just an AI demo. It must become an operator-grade merchant system with:

- a cafe operating cockpit for revenue, orders, courses, referrals, LINE status, and handoff blockers;
- a safe AV AI ordering workflow that produces candidate orders only until Odoo validates menu, price, options, member, voucher, and payment boundaries;
- a LINE Official Account / LINE WORKS control plane that separates association and cafe subjects;
- a financial sustainability layer that tracks debt pressure, course cost allocation, cafe cashflow recovery, and revenue recovery;
- a Sanchong demonstration layer that measures local trust, course-to-member conversion, cafe revenue signals, and community self-funding triggers;
- a no-secret, no-plaintext, no-production-side-effect P1 review mode.

## Current Backend Surfaces

Existing usable surfaces:

- `Business Backend Optimization`: packet-backed P1 backend review cockpit for business continuity, AV AI quality, financial sustainability, Sanchong demonstration, founder mission, release gates, and staff correction queue.
- `Total Product Handoff`: operator ref collection, handoff pack, side-effect boundary, production activation hold.
- `LINE Official Account Config`: candidate settings, webhook candidate, human owner/admin release boundary.
- `LINE WORKS Notification`: candidate, preflight, release refs, runtime activation draft, operator handoff.
- `Cafe AI Eventbook`: event evidence and candidate workflow surface.
- `Cafe Menu Options`: structured menu customization options.
- `Member Registration`: member identity, consent, organization/person review gates.
- `Property / Association / Fund Allocation modules`: broader association and resident management context.

Backend gap:

The current backend is strong on safety gates and productization packets, but it needs a business cockpit that makes revenue continuity, course economics, local demonstration progress, AI AV quality, and operator burden visible in one operating loop.

## End-To-End Flow

1. Customer or staff initiates inquiry through in-store service, LINE, future AV AI ordering, or manual channel.
2. AI layer captures intent as text/audio/video candidate only.
3. Candidate parser creates structured order intent with menu item, options, quantity, context, allergy risk, and confidence.
4. Odoo authority validates menu, price, custom options, availability, member, voucher, and payment preconditions.
5. Operator cockpit shows the candidate with risk flags and fallback path.
6. Human staff confirms or edits before any real POS write.
7. Payment and voucher actions remain manual or separately released until activation refs are complete.
8. LINE/LINE WORKS notifications remain candidate/preflight unless human release refs and runtime resolver refs pass.
9. Daily close reconciles manual orders, POS entries, LINE events, course income, expenses, debt pressure, and community demonstration metrics.
10. Total field receives evaluation packets, not raw secrets, raw member data, raw payment data, or uncontrolled API authority.

## Backend Feature Additions

### 1. Business Continuity Cockpit

Required widgets:

- current manual operation status;
- new automation hold status;
- today's order count, revenue signal, and manual fallback status;
- open blockers by release gate;
- DNS/gateway rollback status;
- LINE/cafe/association subject separation status;
- vendor/API control risk status.

Required refs:

- `manual_order_fallback_ref`
- `manual_payment_fallback_ref`
- `existing_pos_continuity_ref`
- `line_manual_customer_service_ref`
- `dns_gateway_rollback_ref`
- `lost_order_prevention_ref`
- `daily_revenue_reconciliation_ref`

### 2. AV AI Merchant Quality Panel

Required widgets:

- voice capture candidate quality;
- video/product/menu recognition candidate quality;
- intent confidence;
- anti-hallucination status;
- allergy/price/payment/member risk flags;
- Odoo authority validation result;
- staff correction queue;
- customer-facing response preview.

Quality gates:

- no raw audio saved in P1;
- no raw video saved in P1;
- no cloud model authority;
- no direct POS write by AI;
- no price invented by AI;
- no voucher mutation by AI;
- low-confidence candidate goes to staff review.

### 3. Menu, Product, and Custom Option Control

Required widgets:

- menu source of truth status;
- active item availability;
- custom options JSON coverage;
- product photo evidence status;
- generated-image candidate status;
- price/version audit.

Rules:

- Custom Options JSON is preferred for sweetness, ice, temperature, size, toppings, and service notes.
- Generated images may be design candidates, not product evidence.
- Real product photo or staff-approved product photo is required before official product evidence use.

### 4. LINE / Domain / API Control Plane

Required widgets:

- association LINE OA refs;
- cafe LINE OA refs;
- channel candidate ids;
- provider/admin role review;
- vendor access review;
- association-approved subdomain;
- webhook relay;
- callback relay;
- runtime secret rotation readiness.

Rules:

- association and cafe LINE OA subjects must stay separate;
- cafe endpoints must use association-approved subdomains;
- association can provide protective gateway support but cannot silently take over cafe commercial ownership;
- vendor-controlled API cannot write POS, payment, member, or LINE send surfaces.

### 5. Financial Sustainability Panel

Required widgets:

- operator-reported three-year debt increase review;
- course expansion review;
- course cost allocation;
- cafe cashflow recovery;
- debt reduction plan;
- revenue recovery signal;
- unfunded fixed-cost warning.

Required refs:

- `debt_increase_review_ref`
- `association_course_expansion_ref`
- `course_cost_allocation_ref`
- `cafe_cashflow_recovery_ref`
- `debt_reduction_plan_ref`
- `revenue_recovery_ref`

### 6. Sanchong Demonstration and Community Self-Funding Panel

Required widgets:

- Sanchong local readiness status;
- demonstration success metric;
- community trust building;
- course-to-member conversion;
- cafe revenue signal;
- community self-funding trigger.

Strategy:

Sanchong is treated as not yet fully self-funding. The operating strategy is to first create visible, low-risk demonstration results through cafe service and association courses, then use those results to trigger community self-funding.

### 7. Founder Mission Sustainability Panel

Required widgets:

- founder mission ref;
- governance handoff status;
- volunteer role split;
- operator burden reduction;
- public-service continuity;
- single-person risk concentration warning.

Rule:

The founder mission must be institutionalized. The system must not require continued single-person debt absorption, unbounded labor, or unmanaged technical risk.

## Process Improvement Measures

1. Add a daily operating review:
   revenue signal, manual fallback, unresolved candidates, LINE incidents, course income, and release blockers.
2. Add a weekly sustainability review:
   debt pressure, course cost allocation, operator burden, community conversion, and next demonstration milestone.
3. Add a release gate board:
   P1 candidate, human refs pending, ready for human review, ready for activation packet, executed after release.
4. Add a staff correction loop:
   AI candidate mistakes become menu/intent/risk training evidence without raw personal data.
5. Add a local demonstration score:
   small visible wins before any large unfunded scale-up.

## Activation Boundary

P1 review may create packets, reports, dashboards, and candidates only.

P1 must not:

- send LINE/LINE WORKS formally;
- write real POS orders;
- capture payments;
- register members formally;
- redeem vouchers formally;
- read raw secrets;
- move member/resident plaintext into prompts;
- save raw audio/video;
- deploy, restart, or upgrade Odoo.

## Recommended First Backoffice Enhancements

1. Add a backend checklist tab for business continuity refs and daily reconciliation.
2. Add a backend checklist tab for AV AI quality gates and staff correction queue.
3. Add a backend checklist tab for financial sustainability and course cost allocation.
4. Add a backend checklist tab for Sanchong demonstration metrics.
5. Add a backend checklist tab for founder mission handoff and operator burden reduction.

These additions can start as packet-backed fields and readonly JSON/Markdown panels before becoming full Odoo models.

## Odoo P1 Backend Surface

Initial Odoo surface:

```text
Model: wuchang.business.backend.optimization
Menu: WuChang Cafe / Business Backend Optimization
Mode: packet-backed readonly/checklist P1 review
```

The surface builds a `W7TP_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_PACKET_V1` review packet and exposes:

- backend panel list;
- checklist items with required refs, success metrics, and operator status;
- KPI snapshots for safe numeric and summary tracking;
- daily operating signals for safe aggregate revenue, order, incident, course, and burden indicators;
- AV AI candidate quality queue for audio, video, menu text, product image, and multimodal order candidates;
- product/menu quality queue for Odoo product refs, price refs, Custom Options JSON refs, photo evidence refs, availability, and AI candidate permission;
- signal trend review for improving, flat, regressing, and insufficient daily operating signals;
- management decision queue for critical/high/medium actions derived from trends, scorecards, and operating review;
- operator runbook for opening checks, service monitoring, daily close signal entry, weekly sustainability review, and total-field packet review;
- process walkthrough and improvement items for each merchant workflow stage;
- readiness scorecard for AV AI merchant maturity, blockers, and next actions;
- end-to-end flow;
- AV AI technology features;
- quality gates;
- required refs;
- business context;
- first backoffice enhancement list;
- P1 side-effect boundary.
- operating review packet with checklist blockers, KPI coverage, and next actions.
- daily signal packet with missing signal types, needs-action signals, observed day count, and next actions.
- AV candidate quality packet with confidence, Odoo validation state, red flags, product photo evidence state, and staff-review requirements.
- product/menu quality packet with required refs, blocker counts, missing custom options, missing photo evidence, and ready-for-AI-candidate counts.
- signal trend packet with trend items, regressing signal types, insufficient signal types, and next actions.
- management decision queue packet with sorted decision items and priority counts.
- operator runbook packet with daily/weekly operating phases and next actions.
- process walkthrough packet with stage-by-stage improvement backlog.
- readiness scorecard packet with score components, activation blockers, and improvement-first next actions.

It does not activate production behavior.

Operating review output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_OPERATING_REVIEW_PACKET_V1
Button: Build Operating Review
Inputs: checklist item statuses and KPI snapshot summaries
Outputs: blocked checklist items, missing KPI types, needs-action KPI list, next actions
```

Daily signal review output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_DAILY_SIGNAL_PACKET_V1
Button: Build Daily Signal Review
Inputs: daily operating signals with aggregate numeric values, safe summaries, and evidence refs
Outputs: signal type coverage, missing signal types, needs-action daily signals, observed day count, next actions
```

Initial daily signal types:

```text
order_count_signal
revenue_signal
unresolved_candidate_count
line_incident_count
course_income_signal
operator_burden_hours
manual_fallback_status
```

Daily signals are P1-safe management inputs. They may record aggregate numbers and safe summaries, but must not include member plaintext, payment card data, tokens, raw audio, raw video, or direct external API data. They exist to connect the scorecard to actual cafe operating rhythm without turning on production automation.

AV candidate quality review output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_AV_CANDIDATE_QUALITY_PACKET_V1
Button: Build AV Candidate Quality
Model: wuchang.business.backend.av.candidate
Inputs: candidate refs, modality, confidence score, Odoo validation state, red flags, product photo evidence state
Outputs: reviewed candidates, low-confidence count, failed validation count, generated-image hold count, staff-review-required count, next actions
```

Initial AV candidate modalities:

```text
audio_intent
video_product_recognition
menu_text_candidate
product_image_candidate
multimodal_order_candidate
```

Initial AV candidate red flags:

```text
low_confidence
menu_item_not_found
custom_option_unmapped
price_mismatch
allergy_or_safety_risk
payment_or_voucher_request
member_plaintext_risk
generated_image_not_product_evidence
raw_media_storage_risk
```

Candidate confidence below 0.75 requires staff review. Odoo validation failures require menu, price, option, or availability correction before staff approval. A generated image can remain a design candidate, but `generated_image_not_product_evidence` blocks it from product evidence use until a real or staff-approved photo ref is attached. The AV candidate queue must not store transcripts, raw audio, raw video, member plaintext, payment card data, channel tokens, or model prompts.

Product/menu quality review output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_PRODUCT_MENU_QUALITY_PACKET_V1
Button: Build Product Menu Quality
Model: wuchang.business.backend.product.quality
Inputs: product refs, Odoo product refs, menu category refs, price refs, Custom Options JSON refs, photo evidence refs, availability state, AI candidate state
Outputs: reviewed products, ready product count, blocked product count, blocker counts, missing custom option count, missing photo evidence count, next actions
```

Required product/menu refs:

```text
odoo_product_ref
price_ref
custom_options_ref
photo_evidence_ref
```

Initial product/menu blocker types:

```text
missing_odoo_product_ref
missing_price_ref
missing_custom_options_ref
missing_photo_evidence_ref
generated_image_only
inactive_or_unavailable
ai_candidate_not_allowed
```

Product/menu quality is the authority bridge between Odoo and AV AI candidates. AI must not quote a product, price, customization, or product image as official unless the product has Odoo authority refs, price refs, Custom Options JSON coverage, availability state, and real or staff-approved photo evidence. Generated images can remain design candidates only; they cannot satisfy `photo_evidence_ref`.

Signal trend review output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_SIGNAL_TREND_PACKET_V1
Button: Build Signal Trend Review
Inputs: daily operating signals across at least two observed days
Outputs: trend items, regressing signal types, insufficient signal types, needs-action daily signals, next actions
```

Trend rules:

```text
order_count_signal: higher_is_better
revenue_signal: higher_is_better
unresolved_candidate_count: lower_is_better
line_incident_count: lower_is_better
course_income_signal: higher_is_better
operator_burden_hours: lower_is_better
manual_fallback_status: higher_is_better
```

Trend review is evidence for operating discipline, not production approval. Regressing signals or insufficient signal coverage should create improvement work before any activation discussion.

Management decision queue output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_MANAGEMENT_DECISION_QUEUE_PACKET_V1
Button: Build Decision Queue
Inputs: signal trend packet, readiness scorecard packet, operating review packet
Outputs: decision items, critical/high/medium counts, next actions
```

The decision queue converts regressing signals, insufficient signals, activation blockers, blocked checklist items, and needs-action KPIs into a sorted management queue. It does not execute any production behavior; it tells the operator which issue should be handled first and what safe evidence/ref should be attached next.

Operator runbook output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_OPERATOR_RUNBOOK_PACKET_V1
Button: Build Operator Runbook
Inputs: actor/input refs and current P1 business context
Outputs: runbook steps, phase keys, daily step count, weekly step count, next actions
```

Initial operator runbook phase keys:

```text
opening_check
pre_service_ai_gate_check
service_period_monitoring
staff_correction_review
daily_close_signal_entry
signal_trend_review
decision_queue_review
weekly_sustainability_review
total_field_packet_review
```

The operator runbook is designed for the real condition that the cafe is open for business while new automation stays held. It turns "Sanchong is not yet naturally self-funding" into a daily and weekly operating rhythm: protect manual revenue first, collect daily close signals, review debt and course cost pressure, build visible demo wins, and send only safe refs/hashes to total field. It does not send LINE, write POS, capture payments, register members, mutate vouchers, call external APIs, deploy, restart, or upgrade Odoo.

Initial management decision item model:

```text
Model: wuchang.business.backend.management.decision.item
Menu: WuChang Cafe / Management Decision Items
Statuses: todo, in_progress, blocked, ready_for_review, done
Editable safe fields: operator_status, owner_scope, due_date, evidence_ref, operator_note
Readonly generated fields: decision_key, source, priority, title, recommended_action
Default filters: Critical, High, Open
Useful filters: Blocked, Ready For Review, Overdue
```

Process walkthrough output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_PROCESS_WALKTHROUGH_PACKET_V1
Button: Build Process Walkthrough
Inputs: current process improvement item completion state
Outputs: workflow stages, improvement backlog, critical improvement count, next actions
```

Initial process walkthrough stage keys:

```text
customer_inquiry_entry
av_ai_candidate_capture
structured_order_candidate
odoo_authority_validation
staff_confirmation
pos_payment_voucher_gate
line_lineworks_notification
daily_close_reconciliation
sanchong_demo_loop
total_field_packet_review
```

Initial process improvement item keys:

```text
unified_entry_intake_board
av_candidate_confidence_and_red_flag_panel
custom_options_json_mapping_queue
authority_validation_failure_reasons
staff_correction_resolution_sla
release_gate_blocker_board
line_subject_scope_dashboard
daily_close_reconciliation_packet
demo_to_self_funding_trigger_tracker
evidence_hash_and_ref_readiness
```

The process walkthrough is the operator-grade version of "run the flow carefully once." It checks the path from customer inquiry to AV AI candidate, Odoo authority validation, staff correction, POS/payment/voucher release gates, LINE/LINE WORKS notification, daily close, Sanchong demonstration, and total-field packet review. Each stage creates a safe improvement item rather than activating production behavior.

Readiness scorecard output:

```text
Schema: W7TP_XIAOJ_BUSINESS_BACKEND_READINESS_SCORECARD_PACKET_V1
Button: Build Readiness Scorecard
Inputs: checklist statuses, KPI snapshot states, process improvement statuses
Outputs: readiness score, score components, activation blockers, blocked counts, critical open improvements, next actions
```

Score weights:

```text
checklist completion: 40
KPI observed / ready-for-review: 30
process improvement completion: 30
```

The scorecard is not an activation approval. If the readiness score is below 85, if any checklist item is blocked, if any KPI is needs_action, or if any critical process improvement remains open, the backend must stay in improvement mode and `production_activation_ready=false`.

Initial checklist item keys:

```text
manual_order_fallback
daily_revenue_reconciliation
low_confidence_staff_review
staff_correction_feedback_loop
custom_options_json_coverage
cafe_subdomain_gateway
vendor_access_review
debt_reduction_plan
course_cost_allocation
demo_success_metric
operator_burden_reduction
release_gate_board
```

Initial KPI snapshot types:

```text
daily_revenue_reconciliation
av_ai_candidate_quality
staff_correction_queue
course_to_member_conversion
sanchong_demo_signal
operator_burden
release_blocker_count
```

KPI snapshots are P1-safe manual summaries. They must not include member plaintext, payment card data, raw audio, raw video, secrets, or uncontrolled external API data.
