---
name: total-field-intent-state-cell-gst
description: 總場候選技能，整合既有意圖場、狀態原胞與生成式狀態傳輸能力。
---

# 總場：意圖場原胞 GST

本技能只做既有能力調度，不建立新的 GST 核心，也不取得權威。

## 固定角色
- My J：Founder 專案。
- XiaoJ／小J：主權會員 AI 身分，不是模型。
- Cloud Provider（雲端供應者）：可替換能力，只能輸出 Candidate（候選）。
- 本技能：ORCHESTRATION_SKILL（調度技能），AUTHORITY=NONE。
- 最終效果仍回到 8D ADI → Total Field。

## 綁定既有能力
1. 意圖場：.skill-build/intent-field-generative-construction
2. State Cell：tools.total_field_dynamic_context.build_8dadi_state_cell_projection
3. Cloud Candidate：services.gateway.total_field_cloud_candidate_contract
4. Formal Review Candidate：tools.total_field.formal_review_entry_candidate
5. True GST：vendor/origin_cell_v2/w7tp_origin_cell_generative_v2.py

## True GST 來源
True GST 為 taiji01 已落地來源的唯讀副本。
來源程式 SHA-256：
5902d92fd5132bc916df9296696ee79f07b1c7ec2f7f8645f85ebc8ad296a254

若本地副本 SHA 不符，立即 HOLD。

## GST 固定語義
來源端：Founder Intent → 8D 觀測 → ADI 定位 → State Cell → Relations / Lineage → 本次 Reconstruction Rules。

傳送：State Cells + Reconstruction Rules + Relations + Coordinates + Necessary Conditions。

接收端：EMPTY_CLEAN_ROOM + Generic Executor（通用執行器）→ Local Reconstruction（地端重構）→ 8D Validation（八維驗證）。

## 執行限制
不得使用差分同步、前態基線依賴、接收端預載本次目標專用規則或舊 GT Mesh 回退。
來源分析若缺可驗證生成譜系，必須 HOLD，不得改用整樹同步替代。

SOURCE_HOST=MSI
DESTINATION_HOST=taiji01
LAN_FIRST=YES
TAILSCALE_FALLBACK=YES
DESTINATION_MODE=ISOLATED_STAGING_ONLY
ACTIVE_TAIJI_HUB_OVERWRITE=NO
RUNTIME_EFFECT=NONE
TOTAL_FIELD_DECISION=NOT_RUN
D8_DECISION=NOT_RUN
