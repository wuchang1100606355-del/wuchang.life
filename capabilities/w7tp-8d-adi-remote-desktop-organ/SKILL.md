---
name: w7tp-8d-adi-remote-desktop-organ
description: 將 Remote Desktop Commander（遠端桌面指揮官）的設備、檔案、搜尋、程序與設定能力等價重構為 W7TP／8D ADI 受治理遠端能力器官。自然語言先轉為常態指令，跨節點狀態使用原胞狀態封包；正式作用經 D8 權威閘門後由 native_claw（原生作用執行器）或相容傳輸執行，並回傳 D4 證據。
---

# W7TP 8D ADI Remote Desktop Organ（W7TP 8D ADI 遠端桌面能力器官）

## 定位

Remote Desktop Commander（遠端桌面指揮官）是外部能力來源與相容傳輸，不是權威。目標是保留其可用能力語意，重構成 W7TP 原生能力契約，最終可由各節點 native_claw（原生作用執行器）提供，不要求外部來源 runtime（執行環境）永久存在。

## 固定鏈路

`自然語言／Web／Odoo → Translation LLM（自然語言轉譯大型語言模型） → Persistent Command Set（常態指令集） → Command Cache（指令快取） → 8D ADI → Origin Cell State Packet（原胞狀態封包） → 可選 Cloud Candidate Completion（雲端候選補全） → 本地 8D 重驗證 → D8 Authority Gate（D8 權威閘門） → native_claw／相容傳輸 → D4 Evidence（D4 證據）`

## 8D 聯合場

- D1 Intent（意圖）：命令語意、完成條件與禁止效果。
- D2 State（狀態）：節點／檔案／程序／設定的當前、目標、未知。
- D3 Coordinate（座標）：裝置、服務、路徑、程序、工作階段、搜尋、設定參照。
- D4 Evidence（證據）：前後狀態、輸入輸出摘要、雜湊、錯誤與收據。
- D5 Execution/Policy（執行／政策）：作用類別、工具入口、前像、冪等與回復。
- D6 Generative State Transmission（生成式狀態傳輸）：跨節點可用任務最小狀態原胞／參照作為重構機制；差異分析不是傳輸技術；同節點本地讀取不強制走 D6。
- D7 Risk/Isolation（風險／隔離）：作用範圍、動態命令分類、節點／工具離線語義分離、失敗即關閉。
- D8 Authority（權威）：工具、管理者、網路可達性、外部 policy（政策）都不創造 W7TP 權威。

## 動態命令

`start_process（啟動程序）` 與 `interact_with_process（程序互動）` 不可固定分類。每次必須先判斷實際命令／輸入會造成的效果，再使用既有 Deterministic Effect Gate（確定性作用閘門）決定是否需要精確 D8 授權。

## 原生重構

來源工具名稱只作 compatibility mapping（相容映射）。W7TP 原生指令使用 `rdc.*` COMMAND_ID（指令識別），目標則是 `node.*` 能力。正式服務只用 SERVICE_REF（服務參照）／DOMAIN_REF（網域參照），禁止把 IP:Port 當服務身份。

## 雲端候選補全

雲端只可補候選關係、候選命令映射與非權威推理；不得創造 D8、不得虛構現場狀態、不得把 UNKNOWN（未知）改成 OBSERVED_FACT（已觀測事實）。

## native_claw 邊界

native_claw（原生作用執行器）只接受已分類、已綁任務、目標、冪等鍵與必要權威參照的 Effect Envelope（作用封套）。它不理解自然語言、不自行選工具、不創造權威。

## 完成證據

每個作用回傳：`COMMAND_ID + DEVICE_REF + TARGET_REF + EFFECT_CLASS + START/END + OUTCOME + PREIMAGE_REF + RESULT_HASH + AUTHORITY_REF + RETURN_COORDINATE`。收據是 D4，不是 D8。
