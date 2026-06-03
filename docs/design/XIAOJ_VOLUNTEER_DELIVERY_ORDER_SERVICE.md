# 小J志工外送服務接單系統設計

狀態：PLANONLY / DESIGN ONLY
Odoo：預留正式後台，不在本階段寫入
資料治理：協會依法物理控管會員個資；雲端 lane 只可接收去識別化摘要 / hash / non-PII shard。

## 1. 系統定位

小J志工外送服務接單系統用於把居民、商家或協會服務需求整理成外送服務草稿，由協會人員或店員審核，再由志工接單與回報狀態。

## 2. 入口

- LINE：居民 / 商家提出需求
- Open WebUI：協會人員 / 店員 / 志工派單工作台
- W7TP Gateway：去敏、分類、plan-only、DLQ
- Odoo：未來正式後台預留

## 3. 基本流程

```text
LINE / Open WebUI
-> 小J整理需求
-> W7TP Gateway 建立 delivery_request_draft
-> Open WebUI 人工審核
-> 志工接單
-> 狀態更新
-> 完成 / 取消 / DLQ
-> 未來 Odoo 正式紀錄
```

## 4. 狀態機

```text
draft_created
-> waiting_staff_review
-> waiting_volunteer_accept
-> accepted
-> pickup_in_progress
-> delivery_in_progress
-> completed
```

例外狀態：

```text
cancelled
rejected
dead_letter_review
```

## 5. 高風險 DLQ

以下請求不得自動派單：

- 金流 / 代付款
- 貴重物品
- 藥品 / 醫療風險
- 緊急救命事件
- 精確地址原文外送雲端
- 電話 / 身分資料外送雲端
- AI 自動決定高風險派單

## 6. 個資邊界

會員姓名、電話、精確地址、即時位置、健康或緊急事件資訊只留協會物理控管邊界。

雲端 lane 僅可接收：

- redacted_summary
- hash
- non-PII shard
- 區域級資訊，不含精確位置

## 7. Odoo 預留

本階段僅預留以下模型，不實作、不寫入：

- xiaoj.delivery.request
- xiaoj.volunteer.profile
- xiaoj.delivery.event
- xiaoj.service.point
