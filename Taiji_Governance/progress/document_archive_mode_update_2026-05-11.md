# 進度更新：改採文件時間版本封存模式

日期：2026-05-11  
模式：開發期資料治理修正  

## 更新內容

系統開發中不保存任何會員個別進度。

後續進度追蹤改採：

- 整份文件時間版本
- 整份文件封存
- SHA256 baseline
- audit record
- rollback reference

## 完成度影響

| 項目 | 原狀態 | 更新後 |
|---|---|---|
| 會員進度追蹤 | 不建立 | 明確禁止 |
| 文件版本治理 | 部分存在 | 明確採用 |
| 個資風險 | L2 | 降至 L1 |
| Audit / Rollback | 文件層 | 文件層維持 |
| Odoo 會員資料 | 不進入開發期追蹤 | 維持隔離 |

## 風險分級

| 風險 | 等級 | 處置 |
|---|---|---|
| 開發期誤存會員進度 | L3_metric_hazard | block |
| 文件版本未做 SHA256 | L2_drift | warn |
| 文件封存缺 rollback reference | L2_drift | warn |
| 文件僅含無敏架構進度 | L0_exact_match | allow |

## 下一步

建立文件封存索引時，欄位只允許：

- document_id
- document_name
- version
- archived_at
- sha256
- contains_member_progress=false
- contains_personal_data=false
- rollback_reference

