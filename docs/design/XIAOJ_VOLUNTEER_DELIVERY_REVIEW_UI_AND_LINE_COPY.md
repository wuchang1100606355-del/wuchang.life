# W7TP-007 Open WebUI 審核卡與 LINE 草稿入口

狀態：PLANONLY / DESIGN ONLY
Odoo：不寫入
目的：讓店員 / 協會人員能審核外送草稿，讓居民用 LINE 低成本提出需求。

## 1. LINE 草稿入口

居民看到的快速選單：

- 我要申請外送協助
- 我要查看進度
- 我要取消申請
- 我要聯絡協會人員

LINE 對話原則：

- 優先按鈕，不要求長文字輸入。
- 只收必要資訊。
- 精確地址、電話、姓名不送雲端。
- 高風險需求直接轉人工。

## 2. LINE 草稿問題

1. 請選擇需求類型：餐點 / 文件 / 日用品 / 其他。
2. 請選擇大約區域：B棟 / C棟 / 社區周邊 / 其他。
3. 請選擇希望時間：今天中午 / 今天晚上 / 明天 / 其他。
4. 是否涉及代付款、藥品、貴重物或緊急事件？若是，轉人工。

## 3. Open WebUI 審核卡欄位

- request_id
- requester_hash
- source
- requester_role
- pickup_area
- dropoff_area
- item_type
- delivery_note_summary
- high_risk_flags
- pii_unlock_stage
- staff_review_required
- volunteer_verified_required
- status
- next_action

## 4. 審核按鈕

- 通過草稿，進入 waiting_volunteer_accept
- 退回補資料
- 轉人工關懷
- 進入 DLQ
- 取消申請

## 5. 志工接單卡

志工未接單前只看：

- 區域級目的地
- 物品摘要
- 預估時間窗
- 是否需要特殊協助

志工接單後才限時揭露最小必要資訊，並記錄 pii_unlock_expiry / auto_revoke_at。

## 6. Hardwall

- 不自動派高風險單
- 不送姓名、電話、精確地址、即時位置到雲端
- 不讓 AI 直接完成派單或結案
- 不寫 Odoo
- 不啟動服務
