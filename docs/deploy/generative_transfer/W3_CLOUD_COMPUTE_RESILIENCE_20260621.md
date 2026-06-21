# W3 Cloud Compute Resilience Gate

RUN_ID=W3_CLOUD_COMPUTE_RESILIENCE_20260621
STATE=CLOUD_COMPUTE_LABOR_ONLY_GATE

## Purpose
Use cloud compute as governed labor for product improvement, market redteam, competitor analysis, and long-running candidate generation without giving cloud authority, memory benefit, data benefit, or Land authority over W7TP, Odoo, POS, LINE WORKS, Tailscale, secrets, or member plaintext.

## Core Rule
主體算力找雲端，8D 解密找我們。

Cloud compute may be triggered as bounded labor. It receives only redacted packets, performs hard candidate work, and returns candidate packets. Local Total Field, GT8D lookup, local verifier, evidence ledger, and human/staff review remain authority.

## Cloud Labor Rule
- cloud_trigger_allowed=true
- cloud_labor_only=true
- cloud_authority=false
- cloud_memory_benefit=false
- cloud_data_benefit=false
- candidate_only=true
- land_allowed=false

## Allowed Cloud Workloads
- competitor_matrix_expansion
- product_redteam_batch
- merchant_objection_draft
- roi_metric_hypothesis_generation
- schema_fixture_candidate_generation
- long_context_summarization_of_redacted_packets
- stress_scenario_generation

## Forbidden Cloud Workloads
- secret_read
- member_plaintext_read
- raw_odoo_record_dump
- lineworks_send
- odoo_db_write
- pos_action
- tailscale_change
- chrome_live_control
- payment_processing
- final_authority_or_land_decision

## Resilience Pattern
1. Local node creates a redacted 8D_GENERATIVE_TRANSFER_REQUEST.
2. The packet sets `candidate_only=true`, `cloud_authority=false`, `land_allowed=false`.
3. Cloud compute returns an 8D_CANDIDATE_COMPLETION_PACKET.
4. Local verifier checks schema, budget, redaction, claim labels, and forbidden actions.
5. Local reconstruction decides whether the candidate becomes evidence, a dry-run fixture, or HOLD.
6. Runtime action remains blocked unless a later Stage 2 or Stage 3 review authorizes it.

## Capacity Controls
- max_cloud_batch_items: 20
- max_candidate_ttl_seconds: 300
- max_redacted_packet_bytes: 65536
- max_retry_count: 2
- fallback_on_cloud_failure: local_lookup_and_hold
- budget_policy: cost_ceiling_required_before_cloud_trigger

## Product Resilience Benefits
- Absorb long competitor-analysis and redteam cycles without slowing local POS nodes.
- Generate multiple market objection candidates while keeping final wording local.
- Produce stress scenarios for degraded network, duplicate POS identity, notification trust, display trust, and ROI proof.
- Keep local system responsive by offloading non-authoritative analysis only.

## Stopline
If any cloud path requests real credentials, raw member data, service-account token printing, API enablement, deployment, DB/Odoo/POS write, LINE WORKS send, Tailscale mutation, cloud memory benefit, cloud data benefit, or final Land authority, output:

STATE=HOLD_CLOUD_COMPUTE_BOUNDARY
