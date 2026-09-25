# Merlin Intent Driver Governance
# 梅林路由器意圖駕馭治理規格

Status: plan-only governance layer
Scope: XiaoJ Intent Field / W7TP / EAMTP-7D / Merlin Router Firmware

## 1. Purpose

The Merlin router must be used as the physical network boundary field of XiaoJ.

XiaoJ may drive the router through governed intent, but must not directly perform unsafe router changes.

## 2. Layer Definition

Merlin router firmware:
- physical network boundary
- LAN/WAN/VPN/guest network/firewall/DNS/QoS/device visibility

W7TP Router:
- intent governance
- EAMTP-7D translation
- policy gate
- dead-letter
- pending review

Merlin Intent Driver:
- converts user intent into router governance plan
- classifies risk
- creates EAMTP-7D packet
- records plan
- never changes router in plan-only mode

## 3. Safety Rules

1. Router admin credentials must not be stored in the repo.
2. Router password, API key, token, private key must never be requested by LLM.
3. WAN SSH is high-risk and should be reduced to LAN/VPN only after human approval.
4. WiFi presence is not identity proof.
5. Router control must pass EAMTP-7D Policy Gate.
6. High-risk router operations enter pending_review.
7. Hardwall violations enter dead_letter.
8. Plan-only mode must not SSH into router.
9. No firmware change, reboot, nvram commit, firewall flush, or port exposure without explicit human approval.

## 4. Canonical Intent Classes

Low risk:
- observe_status
- generate_inventory_plan
- explain_network_field

Medium risk:
- qos_xiaoj_priority_plan
- dns_service_naming_plan
- guest_network_design_plan

High risk:
- ssh_hardening_plan
- vpn_member_access_plan
- firewall_segmentation_plan
- https_edge_routing_plan
- emergency_lockdown_plan

Hardwall:
- export_router_password
- read_private_key
- disable_firewall
- expose_core_service_to_wan
- open_unrestricted_wan_ssh
- flush_firewall_without_review

## 5. Canonical Statement

小J可以駕馭梅林路由器，但必須先以 EAMTP-7D 形成意圖封包，
經 Router Guard 判定後，產生可審核計畫。
未經人類承接，不得直接改動梅林路由器設定。
