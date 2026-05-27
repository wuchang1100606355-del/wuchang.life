# Merlin Approval Gate Governance
# 梅林路由器操作單核准閘門治理規格

Status: human-approval record only
Scope: XiaoJ Intent Field / W7TP / EAMTP-7D / Merlin Router Firmware

## 1. Purpose

Merlin Approval Gate records human approval for a Merlin Apply Queue ticket.

It does not execute router changes.

## 2. Flow

Merlin Apply Queue ticket
→ Approval Gate
→ exact approval phrase verification
→ ticket hash verification
→ decision:
  - approved_record_only
  - rejected_approval
  - rejected_dead_letter
→ append-only approval ledger

## 3. Safety Boundary

The Approval Gate must not:

- login to router
- use SSH
- call router HTTP admin API
- write nvram
- reboot router
- change firewall
- change WAN exposure
- change WiFi
- change VPN
- store router password
- store API key / token / private key

## 4. Approval Meaning

Approval means:

- the human has accepted the plan for manual review / manual application
- the ticket may be moved to a human execution checklist
- the system may preserve an approval record

Approval does not mean:

- automatic router execution
- direct SSH
- direct HTTP admin call
- firmware change
- firewall modification
- credential access

## 5. Hardwall

Dead-letter tickets cannot be approved.

Tickets involving router password export, private key access, unrestricted WAN SSH, firewall disablement, evidence erasure, or direct MSI core exposure to WAN must remain rejected.

## 6. Canonical Statement

核准閘門只記錄人類承接，不自動執行。
小J可以協助產生核准紀錄與人工操作清單，但不得越過人類核准直接修改梅林路由器。
