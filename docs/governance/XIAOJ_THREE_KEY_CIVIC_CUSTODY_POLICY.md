# 三里長三 USB / 硬體金鑰實體保管制

狀態：PLANONLY / GOVERNANCE DESIGN ONLY

## 核心原則

- 小J個資開封權不得由單一管理員、創辦人或工程帳號掌握。
- 解密權分割為三份，由三位里長或指定公正保管人分別保管。
- 普通 USB 不得保存明文 master key。
- USB 只能保存加密 shard，或改用硬體安全金鑰。

## 門檻模式

- 2-of-3：一般合法查核或緊急必要。
- 3-of-3：最高敏感資料、大量匯出、API Key 批次復原。

## 開封要求

- legal_basis
- purpose
- requested_data_scope
- approving_key_holders
- opened_by
- opened_at
- expiry_time
- audit_required

## 禁止事項

- 不保存明文 master key。
- 不讓 root/admin 等同解密權。
- 不把 USB shard 寫入 Git、logs、memory、prompt。
- 不把開封後個資送雲端 lane。
