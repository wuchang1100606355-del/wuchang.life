# 假設、設計、實作與落地契約

## HYPOTHESIS（假設）

用途：解釋未知、提出可行機制、預測結果。
必要欄位：
- `hypothesis_id`
- `question`
- `basis_refs`
- `prediction`
- `falsifier`
- `scope`
- `minimum_test`

假設可以是新的、前瞻的、尚未證實的；其價值由可驗證性決定，不由「看起來保守」決定。
假設不得宣告現況、實作完成、正式效果或權威。

## DESIGN（設計）

設計是「若要達成目標，系統應如何被建構」。
它必須明示：
- `design_id`
- `requirements_refs`
- `facts_used`
- `hypotheses_used`
- `components_and_interfaces`
- `data_and_control_flow`
- `invariants`
- `failure_modes`
- `rollback_design`
- `acceptance_conditions`
- `open_questions`
- `product_level_target`：研究原型／展示級／競賽級／試營運級／產品級／正式營運級等目標水準與判定條件。
- `product_quality_axes`：可靠性、效能、使用性、可維護性、可部署性、可觀測性、隱私／安全、可恢復性、成本、相容性、無障礙等產品品質軸。
- `competitor_set`：真正競品、替代方案與現行做法；每項必須附來源或明示 UNKNOWN（未知）。
- `competitor_benchmark`：逐軸比較功能、效能、成本、硬體需求、治理、隱私、維運、體驗與限制。
- `differentiation_claims`：區分 VERIFIED_ADVANTAGE（已驗證優勢）、DESIGN_ADVANTAGE（設計優勢）、HYPOTHESIZED_ADVANTAGE（假設優勢）、PARITY（相當）、COMPETITOR_LEADS（競品領先）、UNKNOWN（未知）。
- `product_gap_to_target`：距離目標產品水準仍缺什麼、先補哪一項、補完的驗收證據。

設計可以在部分假設尚未驗證時完成，但每個依賴假設必須可追蹤。
若假設後續被反證，只使依賴該假設的設計局部失效，不推翻無關設計。

## IMPLEMENTATION（實作）

實作必須綁定設計版本與精確來源座標：
- 修改／新增路徑
- 版本或工作樹
- 輸入輸出契約
- 測試
- 錯誤處理
- 回復點

`IMPLEMENTATION_CANDIDATE` 只表示程式存在。
`VERIFIED_IMPLEMENTATION` 另要求指定版本的獨立測試與受影響閉環重驗。

## LANDING（落地）

落地是把經驗證實作送入「指定目標座標」，不是建立 commit（提交）或檔案存在的同義詞。

只有以下條件全部成立才可進入落地：
1. 使用者目前意圖仍要求該效果。
2. 目標節點／版本／服務座標新鮮且無衝突。
3. 必要需求、介面、依賴、消費者已閉合。
4. 相稱測試與負面測試通過。
5. 接線位置、啟動條件與資料遷移已明確。
6. 有可執行 rollback（回復）與 preimage（前像）。
7. D7 無未處理的重大／阻斷風險。
8. 需要副作用時，D8／人類授權範圍精確涵蓋該效果。

## LANDING TIME（落地時機）

- `TOO_EARLY`：仍有必要假設未驗證、關鍵需求 UNKNOWN、接線／回復未閉合。
- `READY_TO_IMPLEMENT`：設計閉合，可開始隔離實作，但不可落地。
- `READY_TO_VERIFY`：實作完成，等待指定版本驗證。
- `READY_TO_LAND`：實作與驗證閉合；在 AUTO-LAND（自動落地）預設下不得停留，應立即解析本次自然語言意圖封套並前進。
- `LAND_NOW`：本次意圖涵蓋該效果、目標前像、回復與時窗有效時，立即落地，不等待第二次同意。
- `DEFER_LANDING`：技術已可落地，但現在會干擾運行、證據不足、外部依賴未就緒或時窗不適合。
- `LANDED_REOBSERVE`：已送達，必須重新觀測。
- `ACTIVE_VERIFIED`：正式入口實際使用且效果重驗通過。

落地後若重新觀測失敗，立即回復至上一個已驗證狀態；不得用「部署成功」取代效果驗證。
## AUTO-LAND（自動落地）判定

`AUTO_LAND_DEFAULT=true`。只要本次自然語言明示要求產生系統效果且未指定唯讀：
1. 設計閉合後自動進入實作。
2. 實作完成後自動進入驗證。
3. 驗證與回復硬閘閉合後自動進入 `LAND_NOW`。
4. 落地後自動 `REOBSERVE`；不符合目標即自動 rollback（回復）。
5. 不因尚未 Canonical（正典）或工作樹有無關髒狀態阻擋本次精確、可回復的工程效果。
6. 只有不可逆破壞、越出意圖作用域、必要權限／憑證不可取得、或無法消解的互斥目標，才可 `HOLD`。

正常路徑：
`HYPOTHESIS -> DESIGN -> IMPLEMENTATION -> VERIFY -> LAND_NOW -> REOBSERVE -> ACTIVE_VERIFIED`

禁止正常路徑：
`... -> CANDIDATE -> 等使用者再次授權`
