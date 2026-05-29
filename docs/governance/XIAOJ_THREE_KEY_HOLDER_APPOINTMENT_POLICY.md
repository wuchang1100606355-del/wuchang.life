# 小J三鑰保管人任免制度

狀態：PLANONLY / GOVERNANCE DESIGN ONLY

## 1. 制度目的

三鑰保管制度用於防止任何單一管理員、創辦人、工程帳號或外部雲端 lane 單獨解密會員個資原文。

## 2. 保管人資格

- 三位里長或協會指定之公正保管人。
- 不得同時兼任系統單一最高管理者。
- 不得單獨持有 master key。
- 必須理解不得複製、外流、上傳、拍照保存 key shard。

## 3. 任命程序

1. 協會會議或正式授權程序提名。
2. 建立 custody_id 與 key_holder_hash。
3. 發放 USB shard 或硬體安全金鑰。
4. 建立 custody record。
5. 封存任命紀錄。
6. 測試 2_of_3 / 3_of_3 模式，但不使用真實個資。

## 4. 撤換程序

1. 保管人離任、遺失金鑰、疑似外洩或利益衝突時啟動撤換。
2. 舊 shard 立即 revoke。
3. 重新產生 custody set。
4. 更新 custody record。
5. 產生 audit record。

## 5. 遺失 / 疑似外洩處理

- 立即標記 key_holder_status=revoked。
- 暫停 break-glass。
- 啟動 replacement custody ceremony。
- 不得用備份明文 master key 恢復。

## 6. Hardwall

- plaintext_master_key_stored=false
- single_admin_decrypt_allowed=false
- cloud_lane_decrypt_allowed=false
- key_shard_to_git_logs_memory=false
- break_glass_audit_required=true
