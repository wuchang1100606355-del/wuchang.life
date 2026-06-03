# 模型名稱分窗介面生效紀錄

版本：2026-05-13  
狀態：ACTIVE  
介面：`site/model_window_interface/index.html`  
Registry：`runtime/identity/model_window_registry.json`

## 核心原則

本系統只有一座可見 AI 身分：小J。

Ollama 或其他廠牌模型名稱只用於選擇內部分窗，不代表獨立人格或無限制權限。

## 分窗規則

| 分窗 | 模型名稱 | 可用任務 | 風險上限 |
|---|---|---|---|
| `AIW-persona-light` | `qwen:0.5b`, `gemma:2b` | 低成本聊天、低熵草稿 | L1 |
| `AIW-engineering-reasoning` | `sister-j-brain`, `llama3.1`, `deepseek-r1`, `Wuchang-Phi4` 等 | 工程推理、patch、manifest、測試草案 | L2 |
| `AIW-gateway-policy` | `metric-language-gateway-ai`, `sister-j-brain` | TensorPacket、allow/audit/warn/block | L3 偵測 |
| `AIW-audit-replay` | `metric-language-gateway-ai`, `sister-j-brain` | audit、rollback、SHA256、replay review | L2 |
| `AIW-deadbox` | 無直接模型 | 隔離、人工審查 | L3 |
| `AIW-human-boundary` | 無直接模型 | 人類確認 | human required |

## 匝道要求

模型可直接用於本地聊天、草稿與低風險測試。

只要模型輸出要轉成系統行為，就必須進入：

```text
Model Output -> TensorPacket -> Taiji Gateway -> Five Metric Gate -> Audit -> Human Boundary if required
```

## 禁止

- 以模型名稱取得最高權限。
- 讓 OpenWebUI / Ollama UI 直接改 Odoo、Google、Docker、systemd、router、VPN。
- 讓模型直接讀取 secret、token、service account JSON、會員明文。
- 讓模型自動付款、退款、折扣、管理員覆寫。

## 驗收

- 分窗 registry 使用 JSON，可被工具讀取。
- 介面為本地靜態 HTML，不呼叫外部 API。
- Clow / Claw / Gateway / Five Metric 只作為狀態與管制說明，不在頁面中直接觸發動作。

