# Taiji System Map

## Core Intent
Local-first Sovereign AI + Zero-Trust POS + Deterministic Inference

## Canonical API
- `jules_cloud_api.py`

## Gateway
- `services/gateway/main.py`
- Single entry point for external requests.

## Core Engine
- `core/metric_tensor_engine.py`

## Edge
- `edge/sister_j_edge_cortex.py`
- `edge/taiji_router_node.py`

## Deployment
- Deployment variants should be isolated under `deploy/`.
