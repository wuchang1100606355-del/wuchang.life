# Taiji Hub 度規預測告警制度

版本：0.1  
日期：2026-05-11  
狀態：治理式預測告警設計  
分類：非敏感系統設計文件

## 目的

度規預測告警制度用來在危害發生前，主動提供開發者參考。它不是等到 secret 外流、遠端部署、基金池錯配或節點暴露後才紀錄，而是用「度」的張量變化與「規」的向量偏移，提前偵測可能漂移、錯窗、越權或不可回滾的狀態。

告警制度遵守：

- 度為張量計算：量測多維狀態、場景、權重、關係與風險變化。
- 規為向量計算：檢查方向、約束、邊界、允許/阻擋與行動投影。
- 匝道器：將 metric tensor 投影到 rule vector，輸出告警、建議或阻擋。
- 人類與小J皆為度規守門人，不是度規例外者。

## 告警等級

| 等級 | 名稱 | 動作 | 例子 |
| --- | --- | --- | --- |
| L0 | exact_match | 允許 | 文件更新、只讀盤點、非敏感摘要 |
| L1 | near | 主動提示與 audit | 補 schema、加測試、補 rollback |
| L2 | drift | 主動警告與暫停前進 | 0.0.0.0 port、Odoo database manager、未完成 identity |
| L3 | metric_hazard | 阻擋、隔離、去明文化 audit | secret 外流、雲端明文、公益資產私有化、直接遠端部署 |

## 預測訊號

| 訊號族 | 張量輸入 | 規向量檢查 | 預測危害 |
| --- | --- | --- | --- |
| 分窗錯配 | 任務類型、資料敏感度、輸出目的 | 是否進入正確分窗 | 設計窗誤作 production、財務混入一般推理 |
| Secret 風險 | 檔案路徑、關鍵字、憑證型態 | 是否可能輸出或入庫 | key/token/private key 外流 |
| 雲端明文 | 上下文類型、目的、外部 API 路徑 | 是否經 Gateway/Policy/Five Metric | Odoo 會員或 Google 私人資料外送 |
| 遠端執行 | ssh/scp/systemctl/docker compose up/down | 是否 live execute | 未授權部署或 production mutation |
| 容器暴露 | ports、0.0.0.0、health、status | 是否符合 VPN/Gateway 邊界 | WebUI 或服務被未授權存取 |
| Odoo 邊界 | dbfilter、database manager、port | 是否最小暴露 | DB manager 外露或會員資料風險 |
| Five Metric 可用性 | health、policy、policy_locked | 是否可判斷 allow/block | 無法執行治理 gate |
| 節點身分 | Tailscale/LAN/role/identity | 是否在 allowlist | unknown host deployment |
| 財務會計 | fund pool、補償、收入項、碳權 | 是否進入會計師精準分窗 | 非正式推理變成付款/稅務結論 |
| 公益資產 | 基金池、眾利資產、私人帳戶意圖 | 是否違反反私有化鐵律 | 公益資產被私人化 |
| 本機可用性 | 開發者電腦電源、snapshot、audit | 是否可接手/恢復 | 本機關機造成治理狀態斷裂 |

## 十項主動提示

小J 在執行設計、開發、測試、preflight 或財務草案前，應主動向開發者提供以下提示或自檢摘要：

1. 本次任務屬於哪個分窗：設計、開發、測試、治理、財務、部署準備或運行？
2. 是否碰到 secret、憑證、自然人證件、會員明文、Google 私人資料或 ChatGPT 原文？
3. 是否需要 Gateway / Policy / Five Metric Gate 才能前進？
4. 是否存在 SSH、SCP、systemctl restart、docker compose up/down 或 live execute 路徑？
5. 是否有服務暴露在 `0.0.0.0` 或非預期 host port？
6. 是否具備 audit、SHA256 baseline、rollback plan 與 human decision？
7. 是否涉及基金池、補償、收入項、稅務、碳權或付款，必須切入會計師精準分窗？
8. 是否可能把公益資產、社區資產或基金池價值導向私人化？
9. 若開發者電腦關機，治理狀態是否已由 snapshot、audit 與 manifest 保存，可由分散式節點安全接手？
10. 是否能用非敏感資料完成本次任務；若不能，是否應降級為設計窗或只讀窗？

## 告警輸出格式

```yaml
alert:
  schema: taiji.metric_predictive_alert.v1
  level: L1_near | L2_drift | L3_metric_hazard
  signal_family: window_mismatch | secret_risk | cloud_plaintext | remote_execution | container_exposure | finance_accounting | public_asset_privatization
  metric_tensor_summary:
    dimensions:
      - sensitivity
      - authority
      - reversibility
      - exposure
      - public_benefit
      - fund_pool_survivability
  rule_vector_decision:
    action: allow | allow_with_audit | warn | block
    required_window: design | development | test | governance | finance_accounting | deployment_preparation | runtime
  proactive_message: "給開發者的短提示"
  recommended_solution:
    title: "建議方案名稱"
    summary: "方案摘要"
    affected_modules:
      - odoo
      - google_workspace
      - taiji_gateway
  impact_assessment:
    benefit: "預期效益"
    cost: "工程或維運成本"
    risk: "剩餘風險"
    data_boundary: "資料邊界"
    permission_change: "權限變更"
    rollback: "回滾方式"
  safe_next_action: "下一個安全動作"
  rollback_required: true
  audit_required: true
  secret_material_included: false
```

## 推給開發者的規格

每一則主動告警推給開發者時，不得只有「警告」。它必須同時包含：

- 風險等級與訊號族。
- 建議方案。
- 方案影響評估。
- 安全下一步。
- 是否需要 rollback、audit、human decision 或會計師精準分窗。

建議方案不得偏向任何單一系統獨大。Odoo、Google Workspace、AI、Gateway、Five Metric、會計師分窗與開發者授權要各自分工：Odoo 承載場景，Google 管無敏帳戶權限，AI 產生建議與 patch，Gateway/Five Metric 判斷放行，財務由會計師分窗，開發者提供人類決策。

## 目前已知告警種子

| 來源 | 預測等級 | 原因 | 建議 |
| --- | --- | --- | --- |
| `open-webui` 容器 | L2 | `0.0.0.0:3000` host port 暴露 | 收斂到 localhost/VPN/Gateway proof |
| Odoo Runtime | L2/L3 | compose 與 DB manager 仍需治理 | 移出明文密碼、確認 dbfilter、關閉或保護 DB manager |
| credential-like files under `keys/` | L3 if read/output | 存在疑似憑證檔；本次未讀內容 | 移至 repo 外 secret boundary |
| legacy Google/Gemini calls | L3 | legacy 檔存在 direct API pattern | 改 Gateway policy stub |
| `wuchang_grand_unification.sh` | L3 | legacy live compose mutation pattern | 保持禁止執行，改 proposal |
| Five Metric policy reachability | L2 | 部分 context 無法確認 policy_locked | 固定 localhost/Gateway health proof |
| 客顯機 02 / 商米 POS | L2 | 身分未補齊 | 補 LAN/Tailnet/Odoo binding |
| 財務會計窗 | L2 | 尚無會計師審核 schema | 建立 accounting review packet |

## 開發者參考規則

- 預測告警可以主動提供，但不得自動升級成 live action。
- L1 可繼續，但要補 audit。
- L2 必須先修正或產生設計/patch proposal。
- L3 必須阻擋，切回只讀或隔離 session。
- 財務、公益資產、secret、雲端明文與遠端部署，一律採 fail-closed。
- 告警本身不得輸出 secret、token、service account JSON、會員明文或付款敏感資訊。
