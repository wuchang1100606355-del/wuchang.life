# W7TP-016 與 W7TP-004/005/007 隱私整合圖

狀態：PLANONLY / CONTROL MAP ONLY

## Integration

W7TP-005 LINE 居民入口
-> 只收去識別化意圖草稿
-> personal progress query 需登入 / 授權 / 一次性驗證

W7TP-004 Open WebUI 本地工作台
-> staff 只看任務摘要與最小必要欄位
-> high-risk / DLQ 進人工審核
-> 不提供任意瀏覽個資入口

W7TP-007 志工外送服務
-> waiting_volunteer_accept 只顯示區域級資訊
-> accepted 後限時揭露最小必要資訊
-> service_closed 後收回志工端可見權限

W7TP-016 Admin-Blind Privacy
-> encrypted_payload 保存原文
-> 三里長三 USB / 硬體金鑰門檻制
-> break-glass 才可限時、限範圍開封

## Boundary

- LINE / Open WebUI / Cloud lane 不可取得 raw PII。
- W7TP Gateway / Router 僅處理 hash、redacted summary、non-PII shard。
- Odoo 未來若承接正式資料，必須位於協會依法物理控管邊界。
- 三鑰開封結果不得送雲端 lane。
