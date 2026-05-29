# W7TP-008 Odoo 預留模組設計 only

狀態：PLANONLY / DESIGN ONLY / NO IMPLEMENTATION
目的：為小J社區服務流程預留 Odoo 模組模型、視圖、權限與資料邊界。
本階段不建立 addon、不寫 Odoo、不連 DB、不啟動服務。

## 1. 模組定位

- 承接 W7TP-005 LINE 居民入口草稿。
- 承接 W7TP-004 Open WebUI staff action draft。
- 承接 W7TP-007 志工外送服務草稿。
- 受 W7TP-016 Admin-blind privacy / 三鑰制度約束。

## 2. 預留模型

### xiaoj.service.request
- request_id
- source
- requester_hash
- service_type
- status
- redacted_summary
- risk_level
- pii_level
- plan_only

### xiaoj.delivery.request
- request_id
- requester_hash
- pickup_area
- dropoff_area
- item_type
- status
- renyi_store_staff_approved
- renyi_store_staff_accompaniment_required
- dynamic_completion_token_ref

### xiaoj.staff.action
- action_id
- actor_hash
- actor_role
- target_ref
- decision
- status_before
- status_after
- plan_only

### xiaoj.privacy.audit
- audit_id
- event_type
- actor_hash
- target_ref
- break_glass_ref
- raw_pii_to_cloud=false

## 3. 視圖預留

- Kanban：服務草稿狀態。
- List：審核佇列。
- Form：單案摘要與 action draft。
- Chatter：只記錄去識別化審核摘要。
- Audit：break-glass / DLQ / 權限回收紀錄。

## 4. 權限邊界

- resident：不可進 Odoo 後台。
- volunteer：不可直接看 Odoo 個資原文。
- staff：只看審核必要摘要。
- renyi_store_staff：可核定陪同外送任務草稿。
- committee：只看公共統計與非個資摘要。
- system_maintainer：只看系統狀態，不看 raw PII。

## 5. Hardwall

- ODOO_WRITE=false at design stage
- DB_CONNECT=false
- ADDON_CREATE=false
- RAW_PII_TO_CLOUD=false
- PLAIN_API_KEY_VISIBLE=false
- SINGLE_ADMIN_DECRYPT_ALLOWED=false
- AI_FINAL_DECISION=false
