# W7TP Total Field Governance Engine V2 Manager And GPT Resilience

## 1. 一句話說明

本管理層讓小J在 GPT、雲端 LLM、API、網路或 DDNS 延遲與失靈時保持安全降級，而不是把外部候選結果當成權威或可執行命令。

## 2. 要解決的問題

外部 GPT 與雲端候選橋接會遇到延遲、不可用、候選品質不穩、網路中斷、DDNS 不穩、router capacity HOLD、USB dead-letter 未啟用等問題。治理引擎 v2 管理層把這些狀態收斂成安全決策：HOLD、local fallback、queue、dead-letter required 或 UI status only。

## 3. 為何 GPT / 雲端候選會延遲或失靈

可能原因包含外部 API timeout、網路路徑不穩、DDNS 更新延遲、雲端服務限流、模型排隊、router 溫度過高、USB storage 錯誤、或本地容量守門仍在 HOLD。這些都是可預期的運行條件，不應阻塞主治理迴圈。

## 4. 本系統如何避免被 GPT 卡死

`w7tp_cloud_candidate_resilience_guard.py` 只讀 fixture，不打雲端；它檢查 latency、timeout、availability、candidate-only、cloud authority、fallback、queue 與 dead-letter 狀態。超時或不可用時會打開 circuit breaker，阻止雲端候選成為可執行輸出，並優先回 local fallback，其次 queue candidate，最後要求 dead-letter 或 HOLD。

## 5. 雲端候選橋接與本地權威腦分工

GPT / 雲端 LLM 只能提供 candidate diversity bridge。總場治理引擎、本地 lookup、router capacity guard 與 flow guard 才能決定是否安全處理。外部候選不得直接產生命令、不得觸發 DB write、router write、deploy、restart、payment、order 或 external send。

## 6. local fallback / queue / dead-letter / UI status

當 cloud latency 超過 timeout 或 cloud unavailable 時，系統輸出 `FALLBACK_LOCAL_LOOKUP` 或 `QUEUE_CANDIDATE`。若 queue 也不可用，才進入 `DEAD_LETTER_REQUIRED` 或 HOLD。UI 可呈現目前是 fallback、queue、HOLD 或 status-only，不會阻塞主要流程。

## 7. router capacity guard 如何接入

目前 router capacity guard 為 `HOLD_USB_STORAGE_ERRORS_DETECTED`，因此 `command_allowed=false`、`requires_human_approval=true`、USB mailbox enable、JFFS pointer write、router write、service restart 都維持 HOLD。只有後續 USB 修護與 capacity evidence 通過後，才能進入人工批准流程。

## 8. 固定 IP / DDNS 如何作 endpoint reference

`220.135.21.74`、`Coffeeboss.asuscomm.com`、`192.168.50.1`、`2222` 與 `coffeeboss` 僅作 endpoint reference。它們不是密碼或 token，也不得被放入 secret context。router password 不得寫入檔案、env、log、report 或 git；若未來需要 SSH，必須先通過 human approval gate 並使用互動式密碼輸入。

## 9. Open WebUI / AI Browser / Odoo / POS 如何呈現狀態

Open WebUI、AI Browser、Odoo 與 POS 只能呈現去識別化狀態：cloud gate、router capacity gate、candidate queue、fallback、dead-letter required、packet hash 與 evidence ref。它們不得顯示 raw packet、secret、會員明文、router 密碼或可執行命令。

## 10. 不主張事項

本文件不主張 GPT 永遠不會壞，不主張雲端候選具備權威，不主張可繞過 router capacity guard，不主張可直接啟用 USB mailbox 或 JFFS pointer，也不主張可進行 production release。

## 11. 安全聲明

本輪為 sandbox landing，不 deploy、不 restart、不寫 DB、不修改 router、不連外雲端測試、不讀 env、不讀 secret、不讀會員明文、不讀 raw audio。所有候選結果只可作 safe summary 與 hash evidence。

## 12. runtime evidence reference

本輪 runtime evidence 位置：

```text
runtime/total_field_governance_v2/W7TP_TOTAL_FIELD_GOVERNANCE_V2_20260630_111000/
```
