# W7TP／8D ADI Developer Intent Canonical（開發者意圖正典）V1

狀態：PASS_DEVELOPER_INTENT_CANONICAL_BUILT

本文件只在 Developer Intent（開發者意圖）範圍內作為機器可讀正典；它不修改 W7TP 全域 active canonical pointer（現行正典指標），不建立 D8 權威，不啟用 runtime。

## 1. 唯一來源規則

只繼承 T-001 Founder Intent Lineage 中 ACTIVE 條目。SUPERSEDED 與 REVOKED 不得重新進入現行開發意圖；CONFLICT 與 UNRESOLVED 必須保留為 gate（閘門）。

## 2. 8D ADI 合同

- 模式：8_IN_1_SINGLE_STATE_FIELD
- D1 Intent（意圖）
- D2 State（狀態）
- D3 Coordinate（座標）
- D4 Evidence（證據）
- D5 Execution/Policy（執行／政策）
- D6 Generative State Transmission（生成式狀態傳輸）
- D7 Risk/Quarantine（風險／隔離）
- D8 Envelope/Authority（封套／權威）

禁止把上述八維重新定義成八步依序流水線。

## 3. GST／Origin Cell

D6 依 FI-006／FI-007：求同存異、改異為同的規則化關係、記錄生成／重構規則、傳輸規則治理模組、目的端重構與等價驗證。禁止降級成 delta、patch、compression、file move、sync 或普通 chunk。

## 4. 權威邊界

- 模型／雲端／工具／Receiver 只能提供 capability（能力）。
- Git／PR／SHA／測試／服務健康只屬 D4。
- 正式效果仍只由 taiji01 Total Field 依有效權威閉合。
- 自然人／會員主權不可被組織、模型或 Total Field 取代。

## 5. V2.1／V2.3

Founder-defined mainline（創辦人定義主線）＝ V2.3；觀測到的 machine active pointer（機器現行指標）＝ V2.1。此差異維持 BLOCKED_BY_T007_AUTHORITY_LINEAGE_GAP，T-007 閉合前不得改 pointer。

## 6. 支線供需規則

Git clean merge = true 不足以授權合併。必須先證明支線供給符合真實意圖在當下 8D ADI 座標的需求，而且沒有權威、語義、譜系、重複能力或風險衝突。

機器可讀檔：configs/total_field/w7tp_developer_intent_canonical_v1.json
