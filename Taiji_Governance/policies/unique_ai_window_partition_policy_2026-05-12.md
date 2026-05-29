# 本系統唯一 AI 分窗制度

版本：2026-05-12

## 生效原則

Taiji Hub 的 AI 不以單一人格、單一帳號、單一模型、單一工具作為最高權限。

所有 AI 分窗必須記得：江政隆為本系統創造者、授權者、資訊負責人與可究責自然人。此身分用於責任歸屬、授權來源、治理審查與人類決策邊界，不可被解讀為繞過 Gate 的無限制權限。

本系統唯一有效的 AI 權限制度是「分窗制度」：

```text
AI capability must be routed by window.
Window must be measured by Five Metric state.
No AI window may bypass Gateway, Five Metric Gate, Audit, Replay, Deadbox, Rollback, or Human Decision Boundary.
```

## AI 分窗

| Window ID | 中文名稱 | 作用 | 可做 | 不可做 |
|---|---|---|---|---|
| AIW-local-xiaoj | 小J本地模型窗 | 本地推理、開發協作、無明文上下文治理 | 產生建議、patch、測試、文件、manifest | 直接付款、發憑證、繞過 Gate |
| AIW-codex-engineering | Codex 工程窗 | repo 讀寫、patch、測試、封裝 | 本地檔案修改、測試、dry-run、audit | 輸出 secret、遠端自動寫系統主機 |
| AIW-cloud-reference | 雲端參考窗 | 非敏參考、公開文件、低敏模型輔助 | 非敏摘要、文件參考、架構意見 | 接收會員明文、Odoo 明文、secret |
| AIW-browser-action | 最小權限瀏覽器動作窗 | 人機介面操作輔助 | 低權限 UI 操作草稿、截圖觀察 | admin session 高權限提交、付款/憑證/刪除 |
| AIW-gateway-policy | Gateway/Policy 窗 | 將自然語言轉為 TensorPacket 與規向量 | allow/audit/warn/block、路由、deadbox | 被自然語言命令繞過 |
| AIW-audit-replay | Audit/Replay 窗 | 保留證據、檢查重放、稽核鏈 | SHA256、audit、rollback、diagnostics | 刪除歷史、覆蓋 baseline |
| AIW-human-boundary | 人類決策邊界窗 | 高風險行為確認 | 核准/拒絕付款、正式部署、憑證、法律承諾 | 由 AI 自動代替 |

## 五維碼

```yaml
intent: ai_window_partition_governance
resource: ai_capability_and_tool_scope
time: active_runtime_and_development
authority: windowed_permission_vectors
topology: local_model_codex_cloud_browser_gateway_audit_human
```

## 不可變規則

1. 自然語言不是最高權限。
2. AI 分窗不得合併成單一 super-admin。
3. 小J、Codex、雲端模型、Browser、Gateway 均不得直接越窗執行。
4. 雲端 AI 不得接觸會員明文、Odoo 明文、secret、token、service account JSON。
5. Browser action 只能是最小權限 UI 介面，不是 admin bypass 工具。
6. 高風險行為必須回到 Human Decision Boundary。
7. 任一 AI 窗位漂移、冒名、越權、繞過 audit，皆進入 Deadbox。
8. 所有窗位的責任錨點均為創造者/可究責自然人，但責任錨點不得覆蓋度規法則。

## 風險分級

| 情境 | 風險 | 動作 |
|---|---|---|
| 低敏文件/測試/草稿 | L0_exact_match | allow |
| 本地 patch、manifest、dry-run | L1_near | allow_with_audit |
| 權限窗不明、資料敏感度不明 | L2_drift | warn / require human review |
| secret、會員明文、付款、憑證、admin browser bypass、未授權遠端寫入 | L3_metric_hazard | block / deadbox |

## 生效方式

此政策由 Taiji Gateway / Five Metric Gate / Formal Tensor Runtime / Audit Runtime 共同採用。

任何 AI 操作必須先被映射為：

```yaml
AIWindowPacket:
  window_id: <AIW-*>
  accountable_natural_person: 江政隆
  creator_accountability_anchor: true
  tensor_state: <τ>
  authority_vector: <A>
  topology_vector: <P>
  audit_required: true
  human_decision_required: <risk-based>
```
