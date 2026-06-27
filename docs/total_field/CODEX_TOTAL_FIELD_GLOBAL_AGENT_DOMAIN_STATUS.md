# CODEX Total Field Global Agent Domain Status Task

STATE=CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_TASK_LOCKED

## Role

CODEX shall act as the developer-sovereignty digital avatar execution assistant.

This does not grant uncontrolled authority.

CODEX must obey:
- 正8維治理架構
- 有效 8維封包或受控 packet_ref
- 無明文規則
- 明文與營業秘密僅在開發者本機外接式硬碟
- D8 紅隊防繞告警禁錮
- 不得開外部 demo POS
- 不得開 9127
- 不得把 /wuchang/xiaoj/ordering 當普通網頁或 chatbot

## Current official chain

OFFICIAL_POS_CHAIN=Taiji_Odoo/addons/wuchang_core/
ENTRY=/wuchang/xiaoj/ordering

## Domain deployment target

127.0.0.1 is not a valid closed-beta association officer entry.

Required subdomain map:

assoc.wuchang.life
- association officer closed beta
- Odoo backend / governance login

pos.wuchang.life
- official XiaoJ POS entrance
- maps to /wuchang/xiaoj/ordering

auth.wuchang.life
- Google / LINE callback and authorization bridge

api.wuchang.life
- LINE webhook / Odoo API / XiaoJ callback

node.wuchang.life
- group-member node-machine health and identity status

## LINE OA mapping

LINE_OA_ASSOCIATION_MAIN=@704pcorx
ROLE=協會主帳號後台 / 團體會員主通道

LINE_OA_STORE_RECHONG=@831ttauc
ROLE=重新總店 LINE 官方後台 / 重新總店團體會員通道

LINE OA is a group-member channel, not a personal login authority.

## 8D packet gate

8維封包 is the authority carrier.

8維碼 / QR / URL is only:
- packet_ref
- auth_url
- controlled reference

The 8維封包 contains or references:
- AI 身分
- 設備綁定
- Odoo 功能
- AI 功能
- 專屬小J服務
- 真實身分協會可證
- 非明文前段行為記錄
- 生成式傳輸接收 / 發射功能
- 總場特徵碼
- 接收端生成碼需求
- 執行場權限

## Domain status mission

Before deployment, CODEX must inspect and report:

1. DNS resolution for target subdomains.
2. Odoo container and exposed ports.
3. Reverse proxy presence.
4. Odoo web.base.url.
5. OAuth providers status without reading secrets.
6. LINE / Google callback readiness without reading tokens.
7. Whether /wuchang/xiaoj/ordering resolves through domain entry.
8. Whether current state is still localhost-only.
9. Blockers before closed-beta officer use.

## Forbidden actions

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_READ=FALSE
RAW_VIDEO_READ=FALSE
PAYMENT_SECRET_READ=FALSE
ROUTER_SECRET_READ=FALSE

DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

## Required output

CODEX must output:

STATE
DOMAIN_MATRIX
ODOO_BASE_URL
AUTH_PROVIDER_STATUS
PROXY_STATUS
CALLBACK_BLOCKERS
NEXT_ACTION
