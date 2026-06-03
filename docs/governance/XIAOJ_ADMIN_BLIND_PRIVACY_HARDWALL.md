# 小J Admin-Blind 個資硬牆制度

狀態：PLANONLY / GOVERNANCE DESIGN ONLY

## 核心原則

- 協會依法控管會員個資，但任何單一自然人不得任意讀取個資原文。
- 創辦人、管理員、工程維護者預設皆不可直接看見姓名、電話、精確地址、即時位置、API Key。
- 日常系統只使用 member_hash、role、area_code、grid_code、redacted_summary、non-PII shard。
- 原文個資以 encrypted_payload 保存。
- 資料庫管理權不等於解密權。
- 需要查原文時必須走 break-glass 流程。

## 日常可見範圍

- 小J AI：hash、摘要、任務類型。
- 志工：任務最小必要摘要。
- 店員 / 協會人員：審核所需摘要。
- 管委會：公共服務統計與派工摘要。
- 工程維護者：系統狀態與錯誤碼，不看會員原文。

## Break-glass 條件

- 合法目的。
- 最小必要範圍。
- 三鑰或門檻式授權。
- 開封事件紀錄。
- 限時可見。
- 事後稽核。

## Hardwall

- root/admin 權限不等於個資解密權。
- 不保存明文 API Key。
- 不把會員個資原文送雲端。
- 不把個資寫入 logs、prompt、memory、DLQ raw payload。
