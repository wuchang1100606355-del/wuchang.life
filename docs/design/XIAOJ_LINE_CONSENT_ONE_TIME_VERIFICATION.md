# W7TP-005 LINE 同意與一次性驗證設計

狀態：PLANONLY / DESIGN + MOCK ONLY

## 1. 制度目的

LINE 與社區 WiFi 只能作為入口或場域訊號，不能直接視為個人身分。居民若要查詢個人進度、家戶資料、外送狀態、報修細節，必須經過登入、授權或一次性驗證。

## 2. 適用情境

- 我的進度查詢。
- 外送申請狀態。
- 報修案件狀態。
- 個人化社區服務。
- 需要查看 association_controlled 資料摘要。

## 3. 驗證方式

- one_time_code：一次性驗證碼。
- signed_magic_link：限時簽章連結。
- staff_verified：協會人員現場核定。
- renyi_staff_verified：仁義店照服員資格職員協助核定。

## 4. 驗證硬牆

- WiFi presence is not identity.
- LINE user id hash is not full identity.
- 驗證 token 不含姓名、電話、精確地址。
- token 必須有 expires_at。
- token 只能查該案、該範圍、該時間窗。
- raw PII 不送雲端。
- Odoo 不寫入。

## 5. 失敗處理

- token 過期：重新申請。
- token 重放：進 DLQ。
- scope 不符：拒絕。
- 高風險或疑似冒用：staff_review_lane。
