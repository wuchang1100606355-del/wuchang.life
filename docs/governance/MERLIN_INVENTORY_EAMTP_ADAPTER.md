# Merlin Inventory to EAMTP Adapter
# 梅林去敏設定清單轉 EAMTP 網路場封包

Status: local redacted inventory adapter
Scope: XiaoJ / W7TP / EAMTP-7D / Merlin Physical Router Field

## Purpose

Convert configs/merlin/router_inventory_redacted.local.json into a XiaoJ-readable EAMTP-7D packet and network field summary.

## Safety Boundary

This adapter must not:

- login to router
- use SSH
- call router admin API
- read raw ASUS/Merlin backup
- print secrets
- upload data
- modify router settings
- commit local inventory

## Flow

redacted local inventory
→ validator
→ EAMTP-7D packet
→ Policy Gate
→ network field summary report

## Canonical Statement

小J可讀取去敏後的梅林設定清單，理解實體網路邊界場；
但不得讀取原始設定備份、密碼、金鑰、token、WiFi 密碼、VPN 私鑰或完整 MAC 清單。
