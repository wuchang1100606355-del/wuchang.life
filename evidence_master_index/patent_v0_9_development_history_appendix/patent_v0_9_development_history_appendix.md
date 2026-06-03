# Patent v0.9 Development History Appendix

GeneratedAt: 2026-05-20T09:55:38.890695

## Purpose

This appendix converts the development history into patent-review language:

```text
Development history → technical problem → technical means → artifact/hash → claim support
```

This appendix is for patent attorney review. It is not a final official filing document.

## Core Technical Chain

```text
候選意圖封包化 → 陣型工作區 → 策略閘道 → 跨系統受控連接器 → 稽核回放
```

## Executive Conclusion

The development history supports that the invention should be framed as an AI execution-governance layer, not as generic AI Agent, RAG, intent-driven networking, or metric tensor itself.

## Development Timeline

### P00 — 社區 / Odoo / AI 執行治理需求形成

**Technical problem:** AI 進入 ERP、組織帳號、通訊平台與邊緣節點後，候選意圖可能越權或誤觸工具。

**Technical solution:** 將 AI 候選意圖與外部工具執行分離，建立操作前治理層。

**Artifact references:** Odoo/Google/LINE/Edge governance design; Wuchang community system context

**Claim support:** C01, C08, C10

**Patent use:** 作為技術問題與產業利用背景。

**Risk note:** 不可寫成單純商業規則或管理方法。

### P01 — 五維碼 / 5D 度規基線建立

**Technical problem:** 跨層 AI、runtime、event、memory、authorization 需要共同狀態參照。

**Technical solution:** 建立 [x, y, z, time, scale] 作為狀態封包可投影欄位前綴。

**Artifact references:** Five Metric policy; metric policy baseline; Five-Dimensional Code rule

**Claim support:** C09

**Patent use:** 轉寫為多維狀態封包欄位，不主張抽象度規本身。

**Risk note:** 避免把五維碼本身寫成抽象數學專利。

### P02 — Five Metric Tensor Engine / policy locked

**Technical problem:** AI 或外部命令可能要求改變既有度規規則，造成 metric hazard。

**Technical solution:** 建立 policy locked、threshold、allow / warn / block 分級與 hazard gate。

**Artifact references:** five_metric_engine 8105; policy_locked=true; L0/L1/L2/L3 actions

**Claim support:** C05, C07, C10

**Patent use:** 支撐策略閘道與決定性阻斷。

**Risk note:** 不可主張 metric tensor 一般概念。

### P03 — Guarded-run / preflight gate

**Technical problem:** 工具執行若直接發生，AI 候選意圖可能越過治理層。

**Technical solution:** 在命令執行前先經 preflight / guarded-run 判斷 allow/block。

**Artifact references:** taiji-metric-preflight; taiji-guarded-run; audit jsonl

**Claim support:** C05, C07

**Patent use:** 支撐『工具呼叫前必經策略閘道』。

**Risk note:** 需寫成具體執行前控制，不是一般權限控管。

### P04 — 5D → 7D runtime-control extension

**Technical problem:** 原始狀態欄位不足以同時描述雲端治理與本地執行基底。

**Technical solution:** 保留 5D prefix，加入 heaven / earth runtime-control fields，形成 7D runtime state。

**Artifact references:** 7d_green_checkpoint; runtime_7d_state; 7d_vs_5d_gap

**Claim support:** C09

**Patent use:** 支撐多維狀態封包之欄位擴充與控制維度。

**Risk note:** 不可使用形上學語言；應寫成狀態欄位與控制欄位。

### P05 — 8126 Formal Tensor Runtime

**Technical problem:** 多維狀態封包需要可驗證 runtime 來處理與回報 health。

**Technical solution:** 建立 formal tensor runtime，提供 7D / TEFMP-0.1 狀態服務。

**Artifact references:** 8126 health; taiji-7d-formal-runtime.service; boot verify

**Claim support:** C09, C10

**Patent use:** 支撐封包 runtime 與狀態處理實施例。

**Risk note:** 不要主張 runtime 名稱本身。

### P06 — 8127 Formation Runtime / packet test

**Technical problem:** 候選封包需映射至受控工作區並阻斷不合法封包。

**Technical solution:** 建立 formation runtime，safe_packet allow，cloud_raw_identity / prefix_mutation / raw_plaintext_canonical block。

**Artifact references:** 7d_formation_mesh; 7d-formation-packet-test; 8127 health

**Claim support:** C05, C09, C10

**Patent use:** 支撐陣型工作區映射與封包合法性判斷。

**Risk note:** 陣型應被定義為工作區/工具/資料源/規則集合，不是品牌詞。

### P07 — Odoo / Google / LINE / Edge 跨系統治理

**Technical problem:** AI 候選意圖可能直接突變 Odoo、Google、LINE 或 Edge 節點。

**Technical solution:** Odoo/Google/LINE/Edge 僅能透過受控連接器與策略閘道進行操作。

**Artifact references:** Odoo 18 container; Google identity mapping; LINE grouping; Edge runtime

**Claim support:** C08

**Patent use:** 支撐跨系統受控連接器實施例。

**Risk note:** Odoo/Google/LINE 不應成為唯一限制。

### P08 — Evidence Chain Phase 1

**Technical problem:** 開發歷程與 artifact 若無封存，難以防止 AI 幻覺、爭議或混淆。

**Technical solution:** 建立本機/SD/雲端 evidence packages、master index 與 SHA256。

**Artifact references:** Wuchang_IP_Evidence zip; Wuchang_Cloud_Evidence zip; Master Index

**Claim support:** C10

**Patent use:** 支撐稽核回放與證據鏈背景。

**Risk note:** 證據鏈可支撐可實施性，但不直接等於新穎性。

### P09 — Claim → Artifact → Evidence Package → Hash

**Technical problem:** 請求項若無 artifact 對應，容易變成泛稱或 AI 生成文字。

**Technical solution:** 建立 C01-C11 claim-artifact mapping v0.1/v0.2 clean。

**Artifact references:** claim_artifact_mapping_v0_2_clean.csv/md/summary

**Claim support:** C01-C11

**Patent use:** 支撐代理人確認每一 claim 的 artifact 基礎。

**Risk note:** 候選 artifact 仍需代理人與工程師確認可引用性。

### P10 — Patent v0.3 → v0.5

**Technical problem:** 需將工程架構轉為 TIPO 可讀專利文件。

**Technical solution:** 建立 v0.3 主請求項、v0.4 四文件、v0.5 TIPO markdown draft。

**Artifact references:** patent_claims_v0_3; patent_v0_4_four_docs; patent_v0_5_tipo

**Claim support:** C05, C08, C09, C10

**Patent use:** 支撐初版專利文本形成。

**Risk note:** v0.5 仍為草稿，不是正式送件終稿。

### P11 — Patent v0.6 Review Package

**Technical problem:** 專利代理人需要 DOCX/PDF/圖式可審查格式。

**Technical solution:** 產出 DOCX/PDF/SVG/PNG/ZIP review package 並鎖定 SHA256。

**Artifact references:** patent_v0_6_review_package.zip; v0.6 lock record

**Claim support:** All, especially C05/C08/C09/C10

**Patent use:** 作為代理人審查包。

**Risk note:** 不是最終官方送件包。

### P12 — Patent v0.7 Agent Review Pack

**Technical problem:** 代理人或 AI 審查可能把 claim 寫回 generic RAG / agent / metric tensor。

**Technical solution:** 建立 attorney instruction、redteam summary、non-claim list、evidence summary。

**Artifact references:** patent_v0_7_agent_review_pack.zip; redteam_review_summary; non_claim_items

**Claim support:** C05, C08, C09, C10

**Patent use:** 防止 claim drift。

**Risk note:** 僅為審查導讀，不取代正式 prior art search。

### P13 — Patent v0.8 Handoff + multi-node distribution

**Technical problem:** 交付代理人前需形成總包、多節點封存與可驗證交接狀態。

**Technical solution:** 建立 v0.8 handoff package；MSI source locked；taiji01 rsync verified；penguin Taildrop verified。

**Artifact references:** patent_v0_8_handoff_package.zip; multinode distribution lock record; attorney one-page summary

**Claim support:** C10

**Patent use:** 支撐開發歷程保全與交接完整性。

**Risk note:** 多節點封存證明版本完整，不直接證明專利性。

## Claim Support Concentration

| Claim | Development support | Drafting note |
|---|---|---|
| C05 | policy gate, guarded-run, packet blocking | Main claim core: deterministic gateway before tool call |
| C08 | Odoo/Google/LINE/Edge connector governance | Main claim core: cross-system controlled connectors |
| C09 | 5D→7D state packet, formal runtime, formation workspace | Main claim core: multidimensional state packet and workspace mapping |
| C10 | audit log, evidence chain, multi-node lock | Main claim core: audit replay and evidence chain |

## Non-Claim Boundary

The following should remain background, terminology, or implementation context unless narrowed into concrete structures:

- 五常 philosophy itself.
- 7D as abstract metaphysical language.
- Metric tensor as a generic mathematical concept.
- RAG itself.
- Generic AI agent routing.
- Intent-driven networking itself.
- Odoo / Google / LINE as sole limitations.

## Attorney Use

Patent counsel should use this appendix to identify which claim elements have concrete artifact support and which terms should be rewritten into precise data structures, control flows, or audit records.

## Missing / Not Copied Sources

- None detected in current evidence_master_index source set.
