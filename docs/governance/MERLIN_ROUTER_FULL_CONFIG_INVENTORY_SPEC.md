# Merlin Router Full Configuration Inventory Spec
# 梅林路由器完整設定清單規格

Status: redacted inventory only
Scope: XiaoJ / W7TP / EAMTP-7D / Merlin Physical Router Field

## 1. Purpose

This document defines how XiaoJ may understand the full Merlin router configuration without receiving secrets.

The router configuration must be split into:

1. Raw Backup:
   - local-only
   - encrypted storage
   - not committed to Git
   - not uploaded to cloud
   - not provided to LLM

2. Redacted Inventory:
   - safe structured summary
   - no passwords
   - no API keys
   - no private keys
   - no VPN secrets
   - no WiFi passwords
   - no router admin password
   - may be used by XiaoJ / EAMTP / W7TP

## 2. Forbidden Fields

The following must never be stored in repo or sent to AI:

- router admin password
- WiFi password
- VPN private key
- WireGuard private key
- OpenVPN key/cert secret
- DDNS password/token
- API token
- SSH private key
- password hash
- full raw backup file
- complete MAC address list without hashing
- raw resident personal data

## 3. Allowed Redacted Fields

Allowed:

- router model
- firmware name/version
- LAN subnet
- DHCP range
- DNS mode
- guest network enabled/disabled
- SSID names, if not sensitive
- WAN remote admin enabled/disabled
- SSH enabled/disabled
- SSH LAN-only/WAN-exposed classification
- port forwarding summary
- VPN enabled/disabled
- VPN peer count
- QoS enabled/disabled
- AiMesh node count
- USB service enabled/disabled
- risk classification
- operator notes

## 4. Governance Rule

Router raw config is evidence/custody data.

Router redacted inventory is XiaoJ-readable field data.

小J可以理解去敏設定清單，但不得讀取、保存或輸出路由器密碼、金鑰、token、私鑰或原始備份。
