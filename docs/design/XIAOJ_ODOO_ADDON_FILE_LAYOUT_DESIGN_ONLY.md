# W7TP-008 Odoo Addon File Layout Design Only

狀態：PLANONLY / DESIGN ONLY / NO IMPLEMENTATION
目的：預留未來 Odoo addon 檔案架構，不建立實際 addon、不寫資料庫、不啟動 Odoo。

## 1. 預留 addon 名稱

- xiaoj_community_service

## 2. 預留檔案架構

```text
xiaoj_community_service/
├── __manifest__.py              # future only / not created now
├── __init__.py                  # future only / not created now
├── models/
│   ├── __init__.py
│   ├── service_request.py
│   ├── delivery_request.py
│   ├── staff_action.py
│   └── privacy_audit.py
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── views/
│   ├── service_request_views.xml
│   ├── delivery_request_views.xml
│   ├── staff_action_views.xml
│   └── privacy_audit_views.xml
├── data/
│   └── sequence.xml
└── README.md
```

## 3. 預留模型對應

- xiaoj.service.request：承接 LINE / Open WebUI 草稿。
- xiaoj.delivery.request：承接志工外送草稿。
- xiaoj.staff.action：承接人工審核 action draft。
- xiaoj.privacy.audit：承接 break-glass / DLQ / 權限回收紀錄。

## 4. 安全預設

- 所有 write action 預設 disabled。
- AI 不可直接呼叫 Odoo write。
- raw PII 不進 prompt、logs、memory、cloud lane。
- encrypted payload 只能透過 W7TP-016 break-glass 設計處理。
- 志工外送必須保留仁義店照服員資格職員核定陪同硬牆。

## 5. 實作門檻

未來若要建立真實 addon，必須先完成：

1. human governance review。
2. test database only。
3. access matrix review。
4. no raw PII cloud lane verification。
5. explicit authorization anchor。

## 6. Hardwall

- ADDON_CREATE=false
- ODOO_WRITE=false
- DB_CONNECT=false
- SERVICE_RESTART=false
- RAW_PII_TO_CLOUD=false
- SECRET_READ=false
