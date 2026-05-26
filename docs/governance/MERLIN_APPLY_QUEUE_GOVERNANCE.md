# Merlin Apply Queue Governance
# 梅林路由器操作單佇列治理規格

Status: plan-to-ticket / human-review only
Scope: XiaoJ Intent Field / W7TP / EAMTP-7D / Merlin Router Firmware

## 1. Purpose

Merlin Apply Queue converts Merlin Intent Driver plans into human-review tickets.

It does not execute router changes.

## 2. Flow

User intent
→ Merlin Intent Driver
→ EAMTP-7D Policy Gate
→ decision:
  - allow_low_risk: observe / explain only
  - pending_review: create apply ticket
  - dead_letter: reject and preserve
→ Human approval required before any router operation

## 3. Safety Boundary

This queue must not:

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

## 4. Approval Rule

Tickets are not executable commands.

A ticket is only a structured human-review object containing:

- intent
- risk
- decision
- plan hash
- proposed manual steps
- forbidden automatic actions
- approval status

## 5. High-Risk Router Management

The following must always require explicit human approval:

- SSH management exposure changes
- WAN administration changes
- port forwarding changes
- VPN membership access
- firewall segmentation
- QoS affecting emergency traffic
- guest network isolation
- DDNS / DNS routing changes

## 6. Hardwall

The following must never become apply tickets:

- export router password
- read private key
- disable firewall
- expose unrestricted WAN SSH
- expose MSI local core directly to WAN
- flush firewall without review
- erase logs or evidence

## 7. Canonical Statement

小J可以把你的意圖轉成梅林路由器操作單，
但操作單不是命令。
未經你明確承接與核准，不得對梅林韌體、SSH、防火牆、VPN、DNS、QoS、WiFi 進行實際變更。
