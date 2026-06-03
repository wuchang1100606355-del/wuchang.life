# W7TP-007 v3.1 Progressive PII Unlocking

狀態：PLANONLY / DESIGN ONLY
本檔只補設計與 schema，不寫入 Odoo，不啟動服務。

## Progressive PII Unlocking

- waiting_volunteer_accept：只顯示區域級資料，不顯示姓名、電話、精確門牌、即時位置。
- accepted：限時揭露最小必要資料，必須記錄 unlock_reason、pii_unlock_scope、pii_unlock_expiry、auto_revoke_at。
- delivery_completed：志工回報送達，但不等於服務正式關閉。
- requester_confirmed：需求者或替代交握確認。
- staff_audited：協會人員審核完成。
- service_closed：收回志工端前端可見權限並封存紀錄。

## Volunteer Qualification

- volunteer_verified = true
- staff_approved = true
- suspension_status = clear
- service_scope 符合派送區域
- training_status 符合服務類型

## Completion Token

可使用 dynamic QR、paper one-time code、voice confirmation code、staff manual close。Token 不得包含姓名、電話、精確地址、即時位置。

## High Risk DLQ

金流、藥品、貴重物、緊急救命事件、單獨進屋服務、精確個資外送雲端、志工資格不明、token 過期或重放，一律 staff review / DLQ。
