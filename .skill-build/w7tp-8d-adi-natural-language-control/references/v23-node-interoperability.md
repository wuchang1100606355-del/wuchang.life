# V2.3 三節點技能互通契約

本契約依 2026-09-27 使用者要求更新三處自訂技能；它是技能操作契約，不是第二正典、接收核心或總場。

## 單一現行設計與因果
現行設計只有 Founder V2.3。8D = 8_IN_1_SINGLE_STATE_FIELD：D1 意圖、D2 狀態、D3 座標、D4 證據、D5 執行／政策、D6 生成式狀態傳輸、D7 風險／隔離、D8 封套／權威，是同一動態狀態場的八個同時耦合視角。不得把它們拆成八個階段、八套核心或彼此独立權威。程序可有先後，不能改寫本體。
ADI 為時空狀態索引：綁定狀態、時間、空間／物件、關係、因果、譜系、證據與重構座標。封包決策索引與系統索引網保持各自契約；浮點資料域只在明示數值契約下使用，不取得決策權。不得降級為 embeddings、語意相似度、路徑清單或普通查詢資料庫。
設計、實作、安裝、選定綁定、排隊、執行、驗證與正式權威分開。舊版本／索引僅供歷史導航，不能當第二現行設計。

## 精確座標與索引失效
每一現況主張綁定 node、device_id、runtime_identity、object_path、source_version／sha256、observed_at_utc、causal_parent_refs、evidence_ref、scope、stage。缺項標 UNKNOWN，不由另一節點補值。
技能、來源、schema、runtime identity、選定綁定或因果依賴任一變動，標記受影響下游 CURRENT_READINESS_INVALIDATED；保持原索引為歷史，產生新快照及 previous_ref。只重驗受影響閉包。雜湊相同僅證明位元組，不證明執行或權威。
操作前先讀本節點技能，再透過已授權通道核實對端 hostname、實際 home、UTC 與指定 object；不可只憑裝置顯示名切換節點。工具傳輸與本機 Git 是載體／保存，不是 D6 重構本身。

## 三節點互通
共同技能名稱固定 w7tp-8d-adi-natural-language-control。
- taiji01：device_id 0a8cb96c-0944-459c-9af3-bc2aeb70aacf；技能 /home/taiji_admin/.codex/skills/w7tp-8d-adi-natural-language-control；工程根 /home/taiji_admin/Taiji_Hub。重用既有能力 owner、候選接收器、ADI 與總場；正式跨節點效果回既有 taiji01 Total Field 裁決。
- MSI：device_id 7914d170-9245-4177-bb12-54aae2ab2631；技能 /home/taiji_admin/.codex/skills/w7tp-8d-adi-natural-language-control。提供已授權開發、觀測與候選能力；不可代替 taiji01 正式權威。
- taiji03：device_id e07385cc-8861-4c68-a512-599e20dc58ba；技能 /home/lenovo/.codex/skills/w7tp-8d-adi-natural-language-control；既有接收器 /opt/w7tp/exact-v3/current/w7tp_genbench_v3.py。只提供本節點已核實能力及授權效果，跨節點權威回 taiji01；不得創建第二接收核心。
以上是明示觀測座標，不是永久可達或授權證明。傳遞最小必要狀態引用、schema、版本、依賴與可驗證證據；對端重新觀測。分別回報 REGISTERED、SELECTED、QUEUED、EXECUTED、VERIFIED，未執行不得寫完成。

## 接收器與副作用邊界
2026-09-27 所讀 taiji03 接收器為 W7G3 binary header、固定本地 TOKEN_TABLE 與 novel block payload 機制。來源的 W7TP_8DADI_2.3 標籤不是原胞技術等同或目前執行證明；必須重新綁定來源 hash 與實際 runtime 後才能主張效果。不得因名稱等同 taiji01 原胞最小封包或總場。
先靜態檢視 handler 呼叫鏈再認定唯讀；status 名稱不保證無啟動容器等副作用。技能更新只代表安裝契約更新，不改服務、正式索引／帳本、正典、指標、T-014 或授予新權限。本技能的 references/node-interoperability-index.json 是候選導航索引，不替代原生 ADI。
