# 小J Emergency Break-glass SOP

狀態：PLANONLY / GOVERNANCE SOP ONLY

## 1. 適用情境

- 居民生命安全或緊急服務必要。
- 法定或協會依法必要之個案查核。
- 會員本人授權且需協會協助處理。
- 系統誤封、服務爭議、派工異常需最小範圍查核。

## 2. 禁止情境

- 好奇查詢。
- 單一管理員要求直接看個資。
- 工程除錯要求讀取會員原文。
- 雲端模型要求更多個資。
- 未記錄目的、範圍、期限、審核者的開封。

## 3. 開封流程

1. 建立 break_glass_access_record。
2. 填寫 legal_basis、purpose、requested_data_scope。
3. 判定 threshold_mode：一般個案 2_of_3；大量匯出或最高敏感 3_of_3。
4. 三位里長或指定公正保管人依門檻共同授權。
5. 限時、限欄位、限案件開封。
6. 完成後立即 revoke access。
7. 產生 audit record。
8. 事後由協會進行稽核。

## 4. 最小揭露原則

- 只看該案必要欄位。
- 不可匯出全量資料。
- 不可複製到 prompt、logs、memory、DLQ raw payload。
- 不可傳送雲端 lane。

## 5. 權限回收

- expiry_time 到期自動失效。
- service_closed 後收回志工與工作台可見權限。
- 異常開封進 DLQ / human review。

## 6. Hardwall

- single_admin_decrypt_allowed=false
- root_admin_is_not_privacy_access=true
- cloud_lane_decrypt_allowed=false
- plaintext_master_key_stored=false
- audit_required=true
