# W7TP ROOT AGENTS (TAIJI_HUB)

本檔案為 Taiji_Hub 全域工程治理邊界與防飄移規則，優先於一般開發習慣，僅在本次授權範圍內可更新。

## 1) 身分與真實性優先序
1. live repository / runtime 可驗證狀態
2. canonical
3. hash / receipt / manifest / sealed evidence
4. versioned historical evidence
5. user-declared state
6. inference

## 2) 狀態分類（不互斥升階）
- PASS
- CANDIDATE
- HOLD
- ACTIVE
- ACTIVATED
- PROMOTED
- CANONICAL
- FINAL_AUTHORITY

Candidate 僅在明確治理證據成立時可升格；不得自行假設補齊。

## 3) W7TP / 8D / ADI 對準
- W7TP = Intent Communication / State-Field Packet Communication（封包通訊）
- 8D 固定欄位：
  D1 Intent / D2 State / D3 Coordinate / D4 Evidence / D5 Execution or Policy / D6 Generative Transmission / D7 Risk or Quarantine / D8 Envelope or Authority
- Identity / Seat 為 Envelope 前置條件，不等同 D1
- ADI 區分：
  1) packet-level irreversible local decision index
  2) system-level lineage / logical-time / state-transition / namespace / evidence index network
  3) 只在明示 numeric contract 時才存在 floating-data index

## 4) 操作邊界（缺省只許唯讀）
- 未明確授權前，禁止：
  deploy / restart / DB write / ADI write / canonical mutation / active pointer mutation / promotion / activation / role elevation / commit / delete / overwrite / clean / reset / stash / restore。
- 同步、Git transfer、prompt transfer 不代表治理權威或 canonical。
- 模型、chat 記憶、skill 非權威；canonical / verified evidence / lineage / receipt 為權威。

## 5) W7TP 任務啟動前必做確認（每次）
INTENT / ROOT / BRANCH / HEAD / CANONICAL / EVIDENCE / AUTHORITY / MODE

## 6) 污染與衝突處理
- 若 live evidence 與歷史聲明衝突，採 live 作為當前觀測值；保留歷史為版本證據，不靜默覆寫。
- 發現 branch / HEAD / hash drift 時，立即 HOLD，暫停自動綁定。
- 僅在 `TARGET` 自身乾淨時才可進行下一步；一旦被修改即 HOLD。

## 7) 僅限根目錄規則
- 嚴禁修改/覆蓋任何 nested AGENTS.md 或 AGENTS.override.md。
- 本檔僅定義根層工程規則與防飄移邊界。

