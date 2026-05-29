# 小J加密實作設計草案

狀態：PLANONLY / CRYPTOGRAPHIC DESIGN ONLY
本文件只描述未來加密封裝設計，不產生真實 key，不讀 secrets，不處理真實個資。

## 1. 設計目標

- 個資原文以 encrypted_payload 保存。
- 系統日常只處理 hash、redacted_summary、area_code、non-PII shard。
- root/admin/database admin 不等於解密權。
- break-glass 必須走三鑰門檻與稽核流程。

## 2. 建議 envelope 結構

- payload_id：加密封包 ID。
- subject_hash：會員或案件 hash。
- data_class：資料類型。
- encrypted_payload：密文，不可進 prompt/log/memory。
- key_policy_id：對應三鑰保管政策。
- threshold_mode：2_of_3 或 3_of_3。
- decrypt_allowed_roles：只允許 break-glass 流程，不允許單一 admin。
- audit_required=true。

## 3. 禁止事項

- 不保存 plaintext master key。
- 不把 key shard 寫入 Git、logs、memory、prompt。
- 不把 encrypted_payload 送雲端模型解讀。
- 不把 raw PII 寫入 DLQ raw payload。
- 不讓單一管理員解密。

## 4. 未來實作建議

- 使用 envelope encryption。
- 使用硬體安全金鑰或 USB shard 保存 key fragment。
- 使用 audited break-glass session。
- 使用限時 capability token 控制開封範圍。
- 開封後自動 revoke。

## 5. Hardwall

- plaintext_master_key_stored=false
- single_admin_decrypt_allowed=false
- cloud_lane_decrypt_allowed=false
- raw_pii_to_cloud=false
- audit_required=true
- plan_only=true
