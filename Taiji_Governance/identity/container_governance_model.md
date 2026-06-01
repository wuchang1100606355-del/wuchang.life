# Container Governance Model

The same physical computer may host multiple identities, but each identity must be separated by container, network, volume, database scope, Odoo boundary, domain route, audit scope, and authority vector.

| Category | Containers |
| --- | --- |
| Core Governance | `taiji_gateway`, `taiji_metric_gate`, `taiji_audit`, `taiji_deadbox`, `replay_index`, `governance_event_bus` |
| Public-Interest | `community_governance`, `community_fund_pool`, `community_document_ai`, `property_ai_service` |
| Community Industry | `cafe_pos_reopen`, `line_order_gateway`, `online_order_gateway`, `customer_display`, `community_ai_subscription` |
| Private Commercial Support | `liaoguo_main_store_support`, `technology_sponsor_records`, `hardware_lending_records`, `technical_transfer_records` |
| Development / Research | `runtime_dev`, `gpu_brain_lab`, `model_routing_lab`, `multimodal_tensor_lab` |

Current observed containers are partial and do not yet satisfy this separation model.
