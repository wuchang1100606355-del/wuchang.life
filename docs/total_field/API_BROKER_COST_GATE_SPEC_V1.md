# API_BROKER_COST_GATE_SPEC_V1

## 1. 成本防禦機制
W7TP API Broker 必須在轉送封包至雲端前攔截請求。

## 2. 核心關卡
- 去重 (Deduplication): 比對 packet_hash，回傳 Cache 結果。
- 配額 (Quota): 依據 MEMBER_REF 進行 Rate Limiting。
- 阻擋: 未帶 candidate_only: true 標籤者直接拒絕。
