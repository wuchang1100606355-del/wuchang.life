# Odoo Reserved Models for XiaoJ Volunteer Delivery

狀態：DESIGN ONLY / NOT IMPLEMENTED
本文件只預留 Odoo 模型，不建立 Odoo addon，不寫入資料庫。

## xiaoj.delivery.request

- request_id
- requester_hash
- requester_role
- pickup_area
- dropoff_area
- item_type
- delivery_note_summary
- requested_time_window
- status
- assigned_volunteer_hash
- plan_only
- created_at

## xiaoj.volunteer.profile

- volunteer_hash
- service_area
- available_time
- service_type
- active_status
- review_status

## xiaoj.delivery.event

- request_id
- event_type
- event_summary
- actor_hash
- timestamp

## xiaoj.service.point

- volunteer_hash
- request_id
- point_type
- point_value
- approval_status

## 資料邊界

正式姓名、電話、精確地址、即時位置不得送雲端。
Odoo 若未來承接正式資料，必須位於協會依法物理控管邊界內。
