# Merlin Redacted Inventory Validator
# 梅林去敏設定清單檢查器

Status: local validation tool
Scope: configs/merlin/router_inventory_redacted.local.json

## Purpose

Validate that the local Merlin router inventory is safe for XiaoJ/W7TP use.

The validator checks:
- JSON validity
- required top-level fields
- forbidden key names
- forbidden secret-like values
- unsafe raw backup hints
- cloud eligibility boundary

It must not:
- login to router
- read raw ASUS/Merlin backup
- print secret values
- upload data
- modify router settings
- commit local inventory
