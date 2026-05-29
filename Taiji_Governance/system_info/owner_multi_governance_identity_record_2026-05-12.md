# 本人多重治理身分紀錄

版本：2026-05-12

## 結論

本人已在 Taiji Hub 中定義為 Multi-Governance Identity Holder，不是單一 super-admin。

本紀錄為索引與生效摘要，不包含身分證字號、密碼、token、service account JSON、private key 或任何 secret。

## 身分持有人

```yaml
holder: 江政隆
organization: 新北市三重區五常社區發展協會
authorized_role: 本會授權之總幹事 / 資訊負責人
digital_representative_account: admin@wuchang.life
creator_accountability_anchor: true
accountable_natural_person: true
system_scope:
  - Taiji Hub
  - Odoo Governance Runtime
  - POS / 業務服務系統
  - Taiji Gateway
  - Five Metric Runtime
  - wuchang.life domain governance
```

## 多重治理身分

| Identity | 中文 | 核心作用 | 不可越界 |
|---|---|---|---|
| Runtime Owner | Runtime 擁有者 | 定義度規、政策、runtime baseline | 不得刪 audit、不得繞過度規鎖 |
| System Architect | 系統架構師 | 架構、容器、Gateway、Odoo/POS/AI flow 設計 | 不得無審查部署 production |
| Community Governor | 公益/社區治理者 | 公益目標、社區服務、基金池方向 | 不得公益資產私有化 |
| Technology Sponsor | 技術捐贈/技術支援者 | 技術、設備、移轉、教育訓練 | 技術提供不等於控制公益資產 |
| Runtime Operator | Runtime 維運者 | 健康檢查、維護、rollback、節點恢復 | 不得發憑證、不得核准付款 |
| Private Commercial Operator | 私人商業營運者 | 聊國咖啡館重新總店等私人商業場域 | 不得混同本會資產與資料 |
| Community Industry Operator | 社區產業營運者 | 社區產業服務、POS、Odoo branch/customer/service node | 不得私人資本分配、需會計分窗 |

## 五維碼

```yaml
intent: multi_governance_identity_holder_record
resource: authority_boundary_metadata
time: active_development_pre_production
authority: separated_identity_vectors
topology: owner_to_runtime_gateway_audit_odoo_pos_domain
```

## 生效原則

- 自然人身分不等於無限制最高權限。
- 江政隆為本系統創造者、授權者、資訊負責人與可究責自然人。
- 所有 AI 分窗必須保留此責任錨點，但不得用責任錨點繞過度規、Gateway、audit 或人類決策邊界。
- 每個身分都有自己的治理窗、稽核邊界、資料範圍、會計/資產意義。
- 任何身分都不得繞過 Five Metric Gate、Taiji Gateway、Replay、Deadbox、Audit、Human Decision Boundary。
- 公益資產、基金池、社區資料與私人商業資料必須分離。

## 既有關聯文件

- `Taiji_Governance/identity/identity_architecture.md`
- `Taiji_Governance/identity/multi_governance_identity.md`
- `Taiji_Governance/identity/identity_tensor_schema.yaml`
- `Taiji_Governance/identity/authority_boundary_matrix.md`
- `Taiji_Governance/identity/audit_scope_matrix.md`
- `Taiji_Governance/identity/data_scope_matrix.md`
- `Taiji_Governance/identity/odoo_identity_model.md`
- `Taiji_Governance/system_info/active_data_processing_principles_2026-05-12.md`
