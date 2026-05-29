# 小J設計人架構金鑰租用政策

狀態：PLANONLY / GOVERNANCE DESIGN ONLY

## 1. 修正定義

- api_key_type=designer_architect_provided_key
- service_type=leased_compute_or_key_service
- key_owner=設計人 / 架構提供者
- lessee=新北市三重區五常社區發展協會
- association_key_ownership=false
- generic_vendor_key=false

## 2. 架構理由

協會向設計人租用受治理的雲端 API 算力 / key service，原因是 W7TP 會在本地先完成脫敏、分片、意圖路由與用量紀錄，避免協會 raw PII 直接送往外部模型。

## 3. 使用流程

LINE / Open WebUI / Odoo draft
-> W7TP Gateway
-> redaction gate
-> shard / non-PII summary
-> designer_architect_provided_key service
-> cloud API
-> W7TP fusion / review
-> PLANONLY result

## 4. 權利邊界

- 協會租用算力服務，不直接取得 key 明文。
- 設計人提供 key / 算力服務，不因此取得協會 raw PII。
- 外部 API 只接收 non-PII shard / redacted summary。
- key 使用須有 usage ledger 與 cost summary。
- key 可撤回、輪替、停用。

## 5. Hardwall

- plaintext_key_storage=false
- association_plaintext_key_access=false
- raw_pii_to_api=false
- raw_pii_to_cloud=false
- prompt_key=false
- log_key=false
- memory_key=false
- git_key=false
- dlq_raw_key=false
- w7tp_redaction_required=true
- shard_routing_required=true
- usage_ledger_required=true
- plan_only=true
