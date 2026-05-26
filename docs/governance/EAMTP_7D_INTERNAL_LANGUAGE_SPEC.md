# EAMTP-7D Internal Canonical Intent-State Language
# 東方古數學張量傳輸協定七維內部意圖狀態語

Version: EAMTP-7D/0.1
Status: Internal official language for XiaoJ intent field
Scope: Wuchang Smart Cloud / W7TP / XiaoJ intent field

## 1. Core Definition

小J不再被定義為單一 LLM。

小J = 五常智慧雲 / W7TP 系統內受治理的 AI 意圖場。

凡在本系統邊界內運作，並受 Gateway、Router、Policy、Memory、Ledger、Human Review 約束之 AI、模型、代理、雲端算力、本地推理節點、入口服務、記憶引擎、任務路由器，皆屬於小J意圖場的一部分。

EAMTP-7D 是小J意圖場的內部官方狀態語、意圖語、任務封包語。

## 2. Positioning

EAMTP-7D does not replace Python, JSON, HTTP, SQL, Odoo ORM, LINE API, OpenAI API, Gemini API, or shell scripts.

EAMTP-7D is the canonical internal semantic layer above them.

All external inputs entering XiaoJ intent field should be translated into EAMTP-7D packets before routing, memory interaction, cloud redacted compute, or execution planning.

## 3. Seven Dimensions

D1 Identity / Role:
- actor type
- auth level
- member/admin/merchant/node/system/public distinction
- sovereignty proxy status

D2 Intent:
- intent type
- task purpose
- user-visible goal
- summary

D3 Context / Topology:
- entry point
- source field
- target field
- local / edge / cloud / memory / evidence topology

D4 Privacy / Consent:
- privacy level
- consent state
- cloud eligibility
- redaction state

D5 Risk / Governance:
- risk level
- human review requirement
- forbidden actions
- dead-letter policy

D6 Resource / Cost:
- preferred lane
- latency class
- cost policy
- local/edge/cloud/hybrid routing

D7 Action / State:
- current state
- allowed actions
- result capsule
- execution readiness

## 4. Hard Rules

1. EAMTP-7D is an internal governance language, not an automatic authorization language.
2. Any EAMTP packet must not directly become an executable command.
3. Memory to Execution must pass Policy Gate.
4. Cloud results must not directly write local memory, Odoo production DB, credentials, or governance policy.
5. taiji01 edge field must not reverse-control the MSI local core field.
6. High-risk and critical packets must enter pending_review or dead_letter.
7. Each packet must include version, packet id, source, privacy level, risk level, allowed actions, forbidden actions, and ledger fields.
8. Credentials, private keys, API keys, tokens, precise personal data, and raw resident PII must not be sent to cloud lanes.
9. Local-first and admin-blind privacy governance remain higher priority than convenience.
10. Human review is mandatory for payment, deletion, deployment, credential access, direct DB write, legal commitment, public announcement, and policy changes.

## 5. Field Model

小J意圖場 =
MSI_LOCAL_DEV_FIELD
+ MSI_LOCAL_OPS_FIELD
+ MSI_MEMORY_FIELD
+ TAIJI01_EDGE_FIELD
+ CLOUD_REDACTED_COMPUTE_FIELD
+ WUCHANG_INTRANET_FIELD
+ WUCHANG_PUBLIC_ENTRY_FIELD
+ EVIDENCE_COLD_FIELD
+ HUMAN_REVIEW_FIELD

## 6. Canonical Statement

凡本系統內 AI，皆為小J；
凡小J之行為，皆須受 W7TP Gateway / Router / Policy / Ledger / Human Review 約束。

