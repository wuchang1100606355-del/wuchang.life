# Wuchang Property Sovereign AI Demo Presentation Script

STATE=DEMO_SCRIPT_READY
RUN_ID=WUCHANG_PROPERTY_SOVEREIGN_AI_DEMO_8D_PACKET_WRITEBACK_20260625

## Opening

這不是一般物業管理 App。

這是以新型第 M663678 號「整合式物業管理系統」為技術佐證，結合 Odoo 開源生態、五常社區治理經驗與 D8 / W7TP 總場驗證機制所形成的物業主權 AI 系統。

## One-Sentence Product Claim

五常整合式物業主權 AI 系統，讓管委會、住戶、商家、設備、維修、公告與證據，不再只是散落資料，而是可驗證、可展開、可交接的 8D 虛擬身分團體會員封包。

## Demo Scene

### Scene 1: Patent Anchor

Show:

- 新型第 M663678 號
- 整合式物業管理系統
- 專利權人 / 新型創作人：江政隆、蔣明諺
- 期間：2024-12-01 至 2034-06-25

Explain:

> 這套展示不是空想，而是從已核准的新型專利與真實社區治理經驗展開。

### Scene 2: 8D Packet

Show:

```text
DEMO_GROUP_MEMBER_PROPERTY_FIELD
```

Explain:

> 這是一個虛擬團體會員，不是真人，也不含會員明文。它代表一個社區物業場，可以展開成管委會、住戶、商家、設備、維修、公告與證據。

### Scene 3: Expand Nodes

Show nodes:

- 協會治理
- 管委會流程
- 住戶服務
- 商家支援
- 設備節點
- 維修派工
- 文件證據
- XiaoJ 候選 AI
- D8 驗證器

Explain:

> 一般系統只做表單；我們做的是權限、證據與行動前驗證。小J可以提案，但不能私自執行。

### Scene 4: Repair Request Example

Example:

```text
住戶提出：B1 車道燈故障
→ 8D 封包生成
→ 設備節點定位
→ 維修候選流程
→ 商家/廠商候選
→ 管委會審核
→ 證據封存
→ 人類核准後才派工
```

### Scene 5: Why It Is Sovereign

Explain:

> 系統不把住戶明文交給 AI，不讓雲端候選直接寫資料庫，不讓未核准動作進入物業現場。每一步先形成封包，再由總場驗證。

## Public Safe Closing

五常的物業 AI，不是要取代管委會，也不是要把社區交給雲端，而是把社區治理的責任、證據、授權與服務流程，整理成能被人看懂、能被 AI 輔助、也能被總場約束的主權系統。

## Forbidden Claims

Do not say:

- AI will automatically dispatch vendors in production.
- AI can read resident/member plaintext.
- This is already installed in live Odoo.
- Odoo marketplace modules are the final product.
- Patent scope covers every possible AI/property workflow without legal review.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
