# Merlin Human Execution Checklist Governance
# 梅林路由器人工承接操作清單治理規格

Status: human manual checklist only
Scope: XiaoJ Intent Field / W7TP / EAMTP-7D / Merlin Router Firmware

## 1. Purpose

This layer converts an approved Merlin Approval Gate record into a human-readable manual execution checklist.

It does not execute router changes.

## 2. Flow

Approved record
→ Human Execution Checklist
→ manual UI checklist
→ operator confirms outside automation

## 3. Safety Boundary

This checklist generator must not:

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

## 4. Manual Execution Rule

A checklist is not an executable command.

It is a structured manual guide for the human operator.

## 5. Canonical Statement

小J可以把已核准的梅林操作單轉成人工承接清單，
但不得自動登入、不得自動套用、不得自動重啟、不得保存路由器憑證。
