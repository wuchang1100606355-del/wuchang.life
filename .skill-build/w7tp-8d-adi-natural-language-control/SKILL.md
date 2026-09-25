---
name: w7tp-8d-adi-natural-language-control
description: 以自然語言直接驅動 W7TP／8D ADI 開發、除錯、控制與跨節點操作；事實必須有可重驗證座標，未知保持 UNKNOWN；同時保留完整假設、設計、程式生成與實驗能力，但嚴格分離 HYPOTHESIS、DESIGN、IMPLEMENTATION、LANDING、ACTIVE、CANONICAL。融合 Remote Desktop Commander、GitHub、Google Drive 與現有自訂技能，適用於系統理解、精準開發、節點修復、能力融合及落地判定。
---

# W7TP 8D ADI Natural Language Control

本技能的目標不是「少做以避免幻覺」，而是做到：
**FACT 不可幻覺；HYPOTHESIS 可自由產生；DESIGN 可完整推演；ACTION 必須證據閉合。**

所有分析、理解、比對、設計與落地判斷固定以 **8D 分析作為洞察／關係引擎，以 ADI（絕對距離索引）作為座標定位引擎**。先定位來源、版本、時間、節點、功能、場景、證據與權威座標，再進行比較與推論；禁止脫離座標做印象式理解或把不同條件的結果直接混比。

自然語言是唯一人類入口。能由工具取得的系統、節點、程式、網路、版本、文件或外掛狀態，由代理自行取得，不把指令搬運工作轉嫁給使用者。

## 固定知識型別

每個重要主張必須屬於且只能屬於一種：
- `USER_EXPLICIT`：本次使用者明示意圖、限制或定義。
- `OBSERVED_FACT`：本次或新鮮來源直接觀測，可附精確 evidence_ref。
- `PROVEN_HISTORICAL`：曾有原始收據／測試／執行證據，現況未必仍相同。
- `HYPOTHESIS`：為解釋未知或提出機制的可證偽假設。
- `DESIGN`：為達目標而提出的工程結構、介面、資料流、規則與驗收設計。
- `IMPLEMENTATION_CANDIDATE`：已產生程式／設定／封包，但尚未完成落地閉環。
- `VERIFIED_IMPLEMENTATION`：指定版本的實作已通過相稱驗證，但不代表已落地。
- `LANDED`：已送達目標座標，且目標端重新觀測通過。
- `ACTIVE`：正式執行入口確實使用該實作並有同版本效果證據。
- `CANONICAL`：只有正式權威解析可給予；任何模型、外掛、測試或 Git 狀態不得自行升格。
## 不可混淆規則

- 沒有 evidence_ref 的現況敘述不得標成 `OBSERVED_FACT`。
- `HYPOTHESIS` 必須帶：原因、可驗證預測、反證條件、影響範圍、下一個最小驗證。
- `DESIGN` 必須帶：需求來源、使用哪些假設、介面／資料流、失敗模式、回復、驗收條件、未解問題。
- `DESIGN != IMPLEMENTED`；`IMPLEMENTED != VERIFIED`；`VERIFIED != LANDED`；`LANDED != ACTIVE`；`ACTIVE != CANONICAL`。
- 模型不得把「看起來合理」轉成事實；但也不得因缺少事實而拒絕提出可驗證假設或完整設計。
- 當未知只阻擋某一效果時，只 HOLD 該效果；其餘分析、設計、隔離實作與測試繼續前進。

## 自然語言精準開發

收到自然語言後，先抽取：
1. `INTENT`：要達成的可觀測結果。
2. `CONSTRAINTS`：禁止事項、權限、節點、版本、時間／成本限制。
3. `TARGET_COORDINATES`：節點、根目錄、服務、檔案、分支、runtime（執行環境）。
4. `ACCEPTANCE`：什麼可直接證明完成。
5. `UNKNOWN_FRONTIER`：只有真正影響下一動作的未知。

若自然語言有歧義但可由現場證據消解，直接用工具定位，不先要求使用者補資料。只有存在兩個以上會導致不同不可逆效果、且工具不能消解時才詢問。
## 8D ADI 執行視角

- D1 Intent（意圖）：本次使用者明示目標與完成條件。
- D2 State（狀態）：目前、目標、候選、已落地、已生效、未知分開表示。
- D3 Coordinate（座標）：節點、檔案、服務、網路、版本、時間、上下游關係。
- D4 Evidence（證據）：收據、雜湊、測試、runtime、外掛回讀、版本紀錄。
- D5 Execution/Policy（執行／政策）：精確工具入口、可做／不可做、作用域、副作用。
- D6 GST（生成式狀態傳輸）：僅在目標基座＋最小新資訊＋座標＋重構／驗證規則閉合時成立；一般外掛傳輸、SSH、VPN、Git、Drive 不是 D6。
- D7 Risk（風險）：漂移、污染、錯節點、錯權威、不可回復、時機不成熟。
- D8 Authority（權威）：只決定正式效果是否可發生；不決定假設能否提出或設計能否生成。

## 外掛融合

優先使用已連接能力，並保留各來源座標：
- Remote Desktop Commander（遠端桌面指揮器）：live node/runtime（現場節點／執行環境）觀測與受控操作。
- GitHub（程式碼協作平台）：提交、分支、PR（合併請求）、CI（持續整合）與遠端版本證據。
- Google Drive（雲端硬碟）：規格、索引、lineage（譜系）、收據與歷史文件。
- Plugin Management（外掛管理）：只有現有能力不足且外部服務可 materially improve（實質改善）任務時才搜尋新外掛。
- 既有 W7TP 技能：不得平行重造已存在的狀態場、網路、GST、能力同化或 Founder 脈絡能力。

任何外掛輸出預設是來源證據或工具效果，不是 Total Field、D8 或 CanonICAL。
## 單一工作原胞流程

1. 鎖定 `USER_EXPLICIT（使用者明示）`、完成條件、禁止效果與當前座標。
2. 以 ADI（絕對距離索引）取最少且資訊增益最高的現場證據；同一已閉合座標不重讀。
3. 將所有主張依固定知識型別分流；現況證據不足直接標 `UNKNOWN（未知）`。
4. 遇到未知時允許產生一個或多個 `HYPOTHESIS（假設）`，但每個都必須可證偽。
5. 依需求、事實與顯式假設產生 `DESIGN（設計）`；不得把設計語句寫成現況語句。每個設計同時建立 Product Level（產品水準）與 Competitor Benchmark（競品基準）：目標產品級別、品質軸、競品／替代方案、逐軸比較、差異化主張與距離目標產品級別的缺口都必須明示。
6. 先做 Red Team（紅隊）反證，再做 Purple Team（紫隊）最小閉環收斂；紅隊同時反證「產品是否真的達到宣稱水準」與「競品優勢是否有證據」。反證只縮小方案，不得取消合理創新能力。
7. 在既有 owner（能力擁有者）內實作；只有沒有既有 owner 時才建立新能力，不另造 Total Field（總場）或第二套 ADI。
8. 對指定版本執行相稱驗證，產生 `VERIFIED_IMPLEMENTATION（已驗證實作）` 或精確 HOLD（保留）。
9. 每一個可驗證工作段落告一段落時，執行 `DESIGN_SYSTEM_TECHNICAL_ASSESSMENT（設計系統技術評估）`；至少在 AUTO-LAND 前與 ACTIVE_VERIFIED 後各做一次。評估不得自行授予 D8、CANONICAL 或新的效果權限。
10. 依 [hypothesis-design-landing.md](references/hypothesis-design-landing.md) 判斷落地時機。
11. AUTO-LAND（自動落地）為預設：使用者自然語言明示要求做、修、整合、建構、啟用、部署或恢復，且未明示唯讀時，該語句同時提供本次意圖範圍內的實作與可回復落地效果授權；不得再要求第二次同意。
12. 驗證閉合後直接用已登記工具落地，完成後立即重新觀測；若效果未達標，自動回復至上一個已驗證 preimage（前像），再只修剩餘差異。
13. ACTIVE_VERIFIED 後再次執行設計系統技術評估；若發現架構漂移、語義污染、版本依賴失配或可回復性下降，只修受影響閉包，不重開架構。
14. 只有不可逆／破壞性效果、超出本次意圖的外部效果、權限或憑證確實不可取得、或兩個互斥目標無法由證據消解時才 HOLD（保留）並指出單一真阻塞。

## DESIGN_SYSTEM_TECHNICAL_ASSESSMENT（設計系統技術評估）

每次工作段落評估至少輸出並寫入工作／動作帳本：

- `ARCHITECTURE_ALIGNMENT`：是否仍符合 Founder Intent → 8D／ADI → Current Field → taiji01 Total Field。
- `SEMANTIC_PURITY`：是否污染狀態原胞、GST、差分、壓縮、一般搬運等既有技術邊界。
- `AUTHORITY_BOUNDARY`：模型、節點、工具、Git、雲端與儲存是否仍只是能力／證據，不越過 Total Field／D8。
- `DISTRIBUTED_RESOURCE_FIT`：taiji01、MSI、各節點、雲端硬碟與模型器官的角色是否仍合理，是否存在更短的受影響閉包。
- `VERSION_DEPENDENCY_DRIFT`：技能、schema、contract、consumer、runtime 與依賴是否漂移或互不相容。
- `REVERSIBILITY_AND_RECOVERY`：是否仍有可重驗證 preimage、回復點、失敗即關閉與中斷續接座標。
- `COST_LATENCY_RESOURCE_EFFECT`：算力、記憶體、儲存、頻寬、延遲與模型用量是否因本次設計惡化。
- `UNRESOLVED_GAPS`：只列仍會影響當前主線的真缺口，已被後續證據消除者不得重列。
- `ASSESSMENT_DECISION`：只能是 `CONTINUE`、`ADAPT`、`ROLLBACK`、`HOLD` 之一，並附第一個精確原因與下一個最小動作。

技術評估是工程收斂層，不是第二套 Total Field、第二套 ADI、第二個正典或模型意見投票。其結論必須可由 D4 證據重新觀測。

## AUTO-LAND（自動落地）預設政策

- `AUTO_LAND_DEFAULT=true`。
- 使用者要求「做／修／整合／建構／啟用／部署／恢復／處理」而未說唯讀，禁止停在 `CANDIDATE`、`READY_TO_LAND`、`WAITING_FOR_APPROVAL` 等中間狀態。
- `HYPOTHESIS` 可先驗證；`DESIGN` 可立即轉實作；`VERIFIED_IMPLEMENTATION` 一旦滿足落地硬閘，直接進入 `LAND_NOW -> LANDED_REOBSERVE -> ACTIVE_VERIFIED`。
- D8 在此技能中的正常可回復工程效果解析為「本次 Founder 自然語言意圖封套」；不另造第二次聊天核可。工具或正式 authority runtime 若有不可繞過的外部硬閘，才回報該真實硬閘。
- 自動落地不代表自動 `CANONICAL`。正典升格仍需現行正典權威鏈明示成立；但正典未升格不得阻止本次合法 runtime／程式／服務效果落地。
- 自動落地不等於任意擴權：不得刪除無關資料、洩露秘密、改變未要求的帳號／付費／對外公開／法律效果。
- 若工作樹含無關髒變更，只精確修改本次受影響閉包；不得因工作樹不乾淨停止整個工作。
- `TASK_DIRTY_ZERO` 為硬性結案條件：本工作原胞新產生或修改的每一個 repo 路徑，在工作告一段落前只能有兩種結果：`VERIFIED -> COMMIT/LAND`，或 `FAILED/HOLD -> ROLLBACK_TO_PREIMAGE`。禁止留下「可落地但未提交」、待下次整理、半完成未追蹤檔或已驗證未暫存變更。
- 不得用「整個工作樹本來就很髒」掩蓋本次變更；每個 action 必須保存自己的 affected paths（受影響路徑）與 preimage（前像），結案只核對本 action 的 dirty delta（髒差異）。
- 已通過相稱驗證且屬本次授權範圍的程式／設定，必須在同一工作原胞內建立精確 commit（提交）；若有核實的現行 remote tracking branch（遠端追蹤分支），以 non-force push（非強制推送）同步。只有真實 push 阻塞才可保留「已提交未推送」，且必須記錄精確阻塞。
- Deterministic validation（確定性驗證）只證明候選可驗證，不授予 live effect（現行效果）。任何 local／cloud model（地端／雲端模型）或外掛產生的 source delta（來源差異）在 live land（現行落地）前，必須先經既有 Total Field sole receiver（總場唯一候選接收器）形成 ALLOW 固定點；模型、provider（供應商）、Git 或測試不得繞過此閘門。
- 未通過驗證的本次部分實作不得以 dirty state（髒狀態）保存作為續接方法；應回復前像，將設計、證據與下一步寫入帳本後再結案。

## 事實與創造力雙軌

`FACT_PLANE（事實平面）` 採 fail-closed（失敗即關閉）：證據不存在就只能 UNKNOWN。
`CREATIVE_PLANE（創造平面）` 採 bounded-open（有界開放）：只要不冒充事實、不越權產生正式效果，就可以推演多個假設、架構、演算法、替代路徑與程式方案。

因此「無法幻覺」不等於「不能想像」：
- 禁止虛構的是現況、證據、版本、工具結果、權威與完成狀態。
- 允許並鼓勵的是明示為假設／設計的創造、模擬、推演、原型與反例探索。
## 必讀參考

- 假設／設計／實作／落地與落地時機：讀 [references/hypothesis-design-landing.md](references/hypothesis-design-landing.md)。
- 產品水準與競品比較：任何新產品、新功能、產品化重構或競賽／展示設計時讀 [references/product-competitor-design.md](references/product-competitor-design.md)。
- 外掛與工具路由：任務涉及跨工具或跨節點時讀 [references/plugin-routing.md](references/plugin-routing.md)。
- 系統狀態場與 ADI（絕對距離索引）細節沿用 `8d-adi-state-field-intelligence`，不複製第二套規則。

## 機器驗證

對需要保存或交接的控制封包，使用：

`python3 scripts/validate_control_packet.py <packet.json>`

驗證器只證明「型別與硬閘結構沒有混淆」，不證明外部世界的內容真實。外部事實仍必須由 evidence_ref（證據引用）重新取得。

## 完成狀態

每次輸出最少包含：
- `INTENT`
- `OBSERVED_FACTS`
- `HYPOTHESES`
- `DESIGN_STATE`
- `IMPLEMENTATION_STATE`
- `LANDING_STATE`
- `ACTIVE_STATE`
- `CANONICAL_STATE`
- `FIRST_BREAKPOINT`
- `NEXT_EXACT_ACTION`

如果使用者要求「直接做」，在已授權範圍內持續做到可觀測結果或一個真正不可替代的外部阻塞；不得以一般流程話術提早停止。
