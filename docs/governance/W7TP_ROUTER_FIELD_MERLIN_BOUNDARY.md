# W7TP Router Field and Merlin Firmware Boundary
# W7TP 路由場與梅林路由器韌體邊界

Status: canonical governance note
Scope: Wuchang Smart Cloud / XiaoJ Intent Field / W7TP / EAMTP-7D

## 1. Correction

In this system, the word "Router" must not be interpreted as only an application router.

The Wuchang/XiaoJ system has two distinct router layers:

1. Physical Network Router Field
2. W7TP Intent Router Field

The physical router field may include Merlin router firmware.

The W7TP intent router field is the logical governance layer that receives EAMTP-7D packets and decides:

- allow_low_risk
- pending_review
- dead_letter

## 2. Merlin Router Firmware Role

Merlin router firmware belongs to the physical network boundary field.

It may support:

- LAN/WAN boundary
- VPN boundary
- guest network segmentation
- internal/external network separation
- firewall rules
- DNS routing
- device access boundary
- traffic observation
- edge network policy

It must not be treated as the EAMTP intent policy engine itself.

## 3. W7TP Router / Gateway Role

W7TP Router / Gateway belongs to the intent governance field.

It governs:

- intent packets
- EAMTP-7D translation
- privacy state
- consent state
- risk level
- cloud redaction eligibility
- memory-to-execution flow
- dead-letter routing
- human review queue
- local/edge/cloud lane selection

## 4. Dead-Letter Position

Dead-letter must exist at the W7TP Router / Gateway governance layer before packets enter:

- memory field
- execution field
- Odoo / Postgres
- cloud compute lanes
- LLM lanes
- local shell or service action

Merlin may block or segment network traffic, but EAMTP dead-letter is an intent-layer mechanism.

## 5. Boundary Rule

Merlin router firmware can enforce network-level separation.

W7TP Router / Gateway enforces intent-level governance.

They may cooperate, but they must not collapse into one uncontrolled execution surface.

## 6. Canonical Field Model

Physical network layer:

Merlin router firmware
→ LAN / WAN / VPN / guest network / firewall / DNS

Intent governance layer:

Entry adapter
→ EAMTP-7D Translator
→ W7TP Router / Policy Gate
→ allow_low_risk / pending_review / dead_letter

## 7. Hard Rules

1. Merlin firmware must not directly execute EAMTP actions.
2. W7TP Router must not assume network presence equals identity.
3. WiFi presence is not sufficient authorization for member-specific services.
4. taiji01 edge field must not reverse-control MSI local core field.
5. Cloud compute lanes must receive only redacted EAMTP packets.
6. Dead-letter packets must not be executed, sent to cloud, or written into production memory.
7. High-risk router decisions require human review.
8. Physical router rules and intent router rules must both be auditable.

## 8. Canonical Statement

梅林路由器韌體是五常智慧雲的實體網路邊界場。

W7TP Router / Gateway 是小J意圖場的意圖治理路由器。

二者共同形成內外網分流、VPN 邊界、雲端脫敏算力與本機營運場的安全分層，但死信箱判定仍應位於 W7TP 意圖治理層。
