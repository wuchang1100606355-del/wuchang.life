# 小J分窗模型下載與建立

本資料夾提供可貼入 Ollama 的小J治理前綴與 Modelfile 範本。

## 前綴檔

```text
prompts/XIAOJ_MODEL_WINDOW_GOVERNED_PREFIX.md
```

可貼入：

- Ollama Modelfile `SYSTEM """..."""`
- OpenWebUI system prompt
- 任何新模型的系統前綴欄位

## 一鍵建立新分窗模型

格式：

```bash
cd /home/taiji_admin/Taiji_Hub
bash scripts/ollama_create_model_window.sh <base_model> <new_model_name> <window_id>
```

範例：

```bash
cd /home/taiji_admin/Taiji_Hub
bash scripts/ollama_create_model_window.sh qwen2.5:3b xiaoj-persona-qwen25-3b AIW-persona-light
```

```bash
cd /home/taiji_admin/Taiji_Hub
bash scripts/ollama_create_model_window.sh llama3.1:8b xiaoj-engineering-llama31-8b AIW-engineering-reasoning
```

```bash
cd /home/taiji_admin/Taiji_Hub
bash scripts/ollama_create_model_window.sh deepseek-r1:8b xiaoj-engineering-deepseek-r1-8b AIW-engineering-reasoning
```

## 可用 window_id

| window_id | 用途 |
|---|---|
| `AIW-persona-light` | 低成本聊天、摘要、低熵草稿 |
| `AIW-engineering-reasoning` | 工程推理、patch、manifest、測試草案 |
| `AIW-gateway-policy` | TensorPacket 與 allow/audit/warn/block |
| `AIW-audit-replay` | audit、rollback、SHA256、replay review |

## 治理規則

新模型可直接用於本地聊天與草稿。

一旦輸出要變成系統動作，必須經過：

```text
模型輸出 -> TensorPacket -> Taiji Gateway -> Five Metric Gate -> Audit -> Human Boundary if required
```

不可用新模型直接：

- 改 Odoo production
- 改 Google Workspace / Admin
- 讀 secret / token / service account JSON
- 執行 payment / refund / manager override
- 改 Docker / systemd / router / VPN

## 檢查

```bash
ollama list
ollama run <new_model_name>
```

