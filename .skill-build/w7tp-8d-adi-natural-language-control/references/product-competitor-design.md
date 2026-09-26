# 8D ADI 產品水準與競品比較契約

本契約固定以 8D 聯合狀態場作為理解／比較引擎，以現行 ADI 索引／座標契約作為定位基礎；ADI 精確子語義由 governing contract（治理契約）決定，不在本文件硬編成單一索引定義。
禁止脫離 ADI 座標，用印象、單一總分、行銷文字或模型先驗直接宣稱產品優勢。

## 基礎方法

任何產品、功能、競品、替代方案或現況基線，先建立 ADI coordinate set（ADI 座標集合）：
- entity（實體）：產品／功能／節點／服務／文件／版本。
- source（來源）：第一手文件、runtime（執行環境）、外掛、Git、Drive、測試或公開來源。
- version（版本）：commit（提交）、release（發行版）、文件版本或現行產品版本。
- time（時間）：觀測時間與有效期限。
- function（功能）：實際比較的使用者效果或工程能力。
- environment（環境）：硬體、網路、資料量、部署形態、使用者場景。
- evidence（證據）：可重新取得的 evidence_ref（證據引用）。
- authority（權威）：只標示來源權威層級，不因來源可信就升格 W7TP D8。

缺少必要座標時只標 UNKNOWN（未知），不得把不同版本、不同場景或不同硬體的結果直接並列成同一現況。
## 8D 比較投影

每一比較項必須投影至：
- D1 Intent（意圖）：使用者真正要達成的效果與產品價值。
- D2 State（狀態）：目前能力、目標能力、成熟度與可用狀態。
- D3 Coordinate（座標）：產品／版本／節點／功能／場景／時間與上下游關係。
- D4 Evidence（證據）：測試、公開規格、runtime、收據、成本或使用者旅程證據。
- D5 Execution/Policy（執行／政策）：部署、維運、治理、限制、授權與實際可執行邊界。
- D6 GST（生成式狀態傳輸）：判斷是否具備可驗證的同／異／同異關係、生成／重構條件、必要座標與等價驗證；共同基座、最小新資訊或差異量只在特定契約需要時使用，不是永久必要定義；一般傳輸能力不得冒充 D6。
- D7 Risk（風險）：安全、隱私、鎖定、可靠性、成本、供應鏈、不可回復與未知。
- D8 Authority（權威）：誰能讓正式效果發生；競品自身管理權不得映射成 W7TP D8。

比較結果不是單一分數，而是 8D 狀態差異與 ADI 座標距離／缺口集合。
不得把多軸差異壓成「總分勝負」後掩蓋關鍵弱點。

## Product Level（產品水準）

不得只寫「產品級」。必須指定目標級別與可觀測達標條件：
- RESEARCH_PROTOTYPE（研究原型）
- DEMO_READY（展示級）
- COMPETITION_READY（競賽級）
- PILOT_READY（試營運級）
- PRODUCT_READY（產品級）
- PRODUCTION_READY（正式營運級）
- ENTERPRISE_READY（企業級）
## Product Quality Axes（產品品質軸）

至少評估：
- 功能完整性與主要使用者旅程
- 效能：延遲、吞吐、資源與擴充
- 可靠性、容錯與恢復
- 安裝、部署、升級與 rollback（回復）
- 可維護性、可觀測性與稽核
- 隱私、安全、資料主權與權威治理
- 使用體驗、無障礙與操作負擔
- 硬體需求、能源與總持有成本
- 相容性、整合能力與供應商鎖定
- 真實環境證據與可重現性

每一品質軸必須有 ADI 座標與 D1-D8 對應，並標示：
OBSERVED_PASS / OBSERVED_GAP / DESIGN_TARGET / UNKNOWN。
不得把 DESIGN_TARGET（設計目標）寫成已達標。

## Competitor Benchmark（競品基準）

競品集合包含：
1. 直接競品：解決同一主要使用者問題。
2. 替代方案：使用者目前可採取的其他做法。
3. 現況基線：不使用本產品時的流程、成本與限制。

每個競品主張都要有 ADI 座標與來源狀態：
- OBSERVED_COMPETITOR_FACT（已觀測競品事實）
- PROVEN_HISTORICAL（已證明歷史）
- COMPETITOR_HYPOTHESIS（競品假設）
- UNKNOWN（未知）
## 差異化與落地

每一差異化主張只能標：
- VERIFIED_ADVANTAGE（已驗證優勢）
- DESIGN_ADVANTAGE（設計優勢）
- HYPOTHESIZED_ADVANTAGE（假設優勢）
- PARITY（相當）
- COMPETITOR_LEADS（競品領先）
- UNKNOWN（未知）

設計目標可以明確要求超越競品，但在同場景、同版本、同條件的可比證據出現前，只能是 DESIGN_ADVANTAGE 或 HYPOTHESIZED_ADVANTAGE。

產品缺口固定表示為：
TARGET_PRODUCT_LEVEL
→ ADI_COORDINATE_GAPS
→ D1_D8_DIFFERENCE_SET
→ MINIMUM_REQUIRED_DELTA
→ IMPLEMENTATION
→ VERIFY
→ AUTO-LAND（自動落地）
→ REOBSERVE（重新觀測）

若某競品資料缺失，不阻止其他已閉合部分繼續設計與實作；只把受影響比較結論標 UNKNOWN。
