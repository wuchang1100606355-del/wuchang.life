# Odoo Member Scenario Total Field Integration

STATE=ODOO_MEMBER_SCENARIO_TOTAL_FIELD_INTEGRATION_V1
DATE=2026-06-29
TASK_ID=D8_MANDATORY_TASK_20260629_183052_ODOO_MEMBER_SCENARIO_TOTAL_FIELD_INTEGRATION
ROOT=/home/taiji_admin/Taiji_Hub

## 0. Total Field Answer

整合結論：

```text
Odoo 是會員、POS、物業、活動、工單與服務流程的實作載體。
Total Field 是安全、審核、證據與風險准駁權威。
會員本人是同意、撤回、揭露與授權主權權威。
```

因此，會員 Odoo 功能可以依場景設計並接入總場，但不得把 Odoo 狀態、管理員審核、協會治理、AI 建議或 Total Field 安全准駁解讀為會員已同意。

## 1. Non-Override Boundary

所有會員敏感功能必須同時保留三個分離狀態：

- `flow_safety_decision`: Total Field / verifier 對流程安全性的判定。
- `member_consent_state`: 會員本人是否已明確同意、拒絕、撤回或仍需確認。
- `odoo_runtime_state`: Odoo 中註冊、審核、服務、活動或工單的業務狀態。

禁止推論：

```text
flow_safety_decision=PASS -> member_consent_state=granted
odoo_runtime_state=approved -> member_consent_state=granted
admin_approved=true -> member_consent_state=granted
association_approved=true -> member_consent_state=granted
AI_recommends=true -> member_consent_state=granted
```

必要顯示語：

```text
此流程已通過安全檢查，但仍需要會員本人明確確認。
```

## 2. Existing Carrier Inventory

| Carrier | Existing file | Current capability | Integration status |
| --- | --- | --- | --- |
| `wuchang.member.registration` | `Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py` | 註冊來源、審核狀態、會員類型、組織角色、同意版本、審核者、身份碼關聯 | 可作 P1/P2 基礎載體 |
| `wuchang.member.identity.code` | same model file | 產生 member id、7D identity code、masked service code、active status | 可延伸 8D 狀態與總場 ref |
| `wuchang.member.external.auth` | same model file | LINE/Google/Odoo 外部登入 hash 綁定 | 可接會員裝置與入口治理 |
| `wuchang.member.consent.ledger` | same model file | 同意版本、用途、撤回時間、audit hash | 可作會員主權 ledger 的第一層 |
| `wuchang.member.recovery.case` | same model file | 裝置/帳號復原、家人代辦、key custody、封存 | 可接裝置遺失流程 |
| `wuchang.member.group.registration.batch` | same model file | 團體 8D 註冊批次、D8 ref、evidence ref、QR payload | 可接團體會員/商家/組織入口 |
| `wuchang.member.group.registration.packet` | same model file | 團體 claim packet、hash provider ref、D1-D8 envelope | 可接候選會員封包 |
| Odoo backend views | `views/member_registration_views.xml` | 註冊 list/form、submit/approve/reject/dead-letter | P2 需補審核事件與 evidence 必填 |
| Member function refs | `docs/total_field/XIAOJ_MEMBER_BROWSER_1B_CONTROL_SPEC.md` | Odoo ref-only identity/role/function/payment intent 欄位 | 可作 mobile browser 控制面契約 |
| Privacy function universe | `W7TP_FIELD_ATLAS/function_universes/SU_MEMBER_PRIVACY_FUNCTION_UNIVERSE_V1.yaml` | 隱私儀表、8D 狀態、聯絡許可、明文存取紀錄、裝置狀態 | 需落 Odoo model/view |
| Contact approval policy | `W7TP_FIELD_ATLAS/contact_policies/W7TP_MEMBER_CONTACT_APPROVAL_POLICY_V1.yaml` | 中介聯絡、用途限定、可撤回、禁止行銷混用 | 需落 Odoo 許可 ledger |
| Delegation rule | `W7TP_FIELD_ATLAS/delegation/W7TP_MEMBER_DELEGATION_AUTHORITY_RULE_V1.yaml` | 家人/授權人協助、限時、可撤回、敏感行為需審核 | 需落代理授權 model |
| Device loss flow | `W7TP_FIELD_ATLAS/device_loss/W7TP_MEMBER_DEVICE_LOSS_RECOVERY_FLOW_V1.yaml` | 遺失回報、停用舊裝置、復原 ticket、重新綁定、稽核 | 可接 recovery case 延伸 |

## 3. Scenario Function Matrix

| Scene | Member-facing Odoo function item | Total Field packet/gate | Existing carrier | Model/view to add | Member sovereignty checkpoint | Forbidden automation |
| --- | --- | --- | --- | --- | --- | --- |
| 個人會員註冊 | 申請會員、查看審核狀態、查看 masked 身分碼 | registration candidate -> verifier -> review seal | `wuchang.member.registration`, `wuchang.member.identity.code` | 會員自助狀態頁、8D status panel | 註冊同意需會員本人確認；審核通過不等於後續資料揭露同意 | 不自動取得 Odoo 後台權限、不讀 raw PII |
| 會員主權/隱私中心 | 查看同意、撤回同意、查看明文存取歷史、查看裝置綁定 | privacy dashboard packet + evidence refs | `wuchang.member.consent.ledger`, `wuchang.member.recovery.case` | `wuchang.member.sovereignty.state`, `wuchang.member.privacy.event` | 同意、拒絕、撤回分開紀錄 | 不把安全可處理解讀成會員已同意 |
| LINE/Google/Odoo/PWA 入口 | 綁定登入、解除綁定、顯示 provider hash 狀態 | external-auth binding packet | `wuchang.member.external.auth` | 裝置/登入 session 狀態 view | 綁定需會員本人確認；provider hash 不顯示 raw subject | 不同步 Google 私人資料到 Odoo |
| 團體會員/商家/組織 | 建立團體註冊批次、掃碼加入、負責人審核 | group 8D registration packet + D8 envelope | group batch/packet models | `wuchang.organization`, `wuchang.organization.membership` | 組織負責人審核不能替代個別會員敏感同意 | 不讓商家成員自審負責人身份 |
| 家庭/長者/代理協助 | 限時代理、代辦報修/活動、裝置遺失協助 | delegation packet + sensitive review gate | recovery case 部分可用 | `wuchang.member.delegation`, `wuchang.family.organization` | 代理範圍、期限、撤回路徑必填；敏感行為仍需最終授權 | 不建立永久代理、不用代理讀 raw plaintext |
| 裝置遺失/帳號復原 | 回報遺失、暫停舊裝置、復原 ticket、重新綁定 | recovery packet + key custody review | `wuchang.member.recovery.case` | `wuchang.member.device.binding`, recovery timeline view | 高風險復原要會員/合法代理驗證與稽核 | 不在復原時揭露明文、不保留舊裝置有效 |
| 商家/POS 聯絡通知 | 取餐、配送、售後、活動通知的中介聯絡 | contact approval packet + purpose code | consent ledger 可作基礎 | `wuchang.member.contact.permission` | 每個用途獨立同意、到期、可撤回 | 不匯出聯絡清單、不把服務通知包裝成行銷 |
| 活動 RSVP / 費用 / 付款候選 | 報名草稿、付款意向 ref、管理費 masked read | browser candidate packet + payment HOLD gate | ref-only browser spec | `wuchang.member.action.draft` | 報名送出與付款捕獲前必須會員本人確認 | 不自動報名、不自動扣款、不直接寫 POS/Odoo |
| 物業/管委會/住戶 | 戶別身份、報修、通知、管委會職務聲明 | property role packet + evidence gate | property modules and member role fields | `wuchang.property.member.role`, committee claim review | 職務/戶別證據審核不等於揭露個資同意 | 不跨社區查詢、不讓物業人員讀無關會員明文 |
| 審核工作台 | 待審清單、理由、證據 ref、准駁 seal、dead letter | preflight + review event + postflight seal | registration review fields | `wuchang.member.review.event` | 審核者不可代會員授權；自審必須 BLOCK | 不允許 self-review、不允許無 evidence approval |
| Google/LINE WORKS/外部工具 | 任務鏡像、文件 evidence ref、通知狀態 | integration adapter packet | external auth + docs only | integration status view | 外部工具只存 ref/status，不存 raw private data | 不把 Odoo 明文同步到 Google/LINE |

## 4. Odoo Model Backlog

P1 should remain product-shell and ref-only:

- `wuchang.member.dashboard.snapshot`: non-sensitive dashboard payload for mobile/browser UI.
- `wuchang.member.action.draft`: activity RSVP, payment intent, service request, contact request drafts.
- UI status panel: 7D/8D status, verifier decision, evidence ref, consent required marker.

P2 should add the review ledger:

- `wuchang.member.review.event`
- Required fields: `subject_model`, `subject_ref`, `decision`, `reviewer_id`, `reviewed_at`, `reason`, `evidence_ref`, `flow_safety_decision`, `member_consent_state`.
- Rule: append-only; no unlink in normal groups.

P3 should add organization membership:

- `wuchang.organization`
- `wuchang.organization.membership`
- `wuchang.organization.responsible.person.claim`
- Rule: responsible-person approval requires owner/admin or approved responsible-person policy; no self-approval.

P4 should add family and delegation:

- `wuchang.family.organization`
- `wuchang.member.delegation`
- Required fields: `member_ref`, `delegate_identity_ref`, `relationship_or_authority_basis`, `allowed_actions`, `expiry_time`, `revocation_path`, `evidence_ref`.

P5 should add contact and integration adapters:

- `wuchang.member.contact.permission`
- `wuchang.member.integration.status`
- Rule: contact purpose code required; marketing requires separate opt-in; external tools store refs only.

P6 should add hardening and evidence tests:

- route hardening report for public member routes.
- mobile screenshot acceptance for 360, 390, 414, 768 px.
- golden prompts for registration, contact, payment, proxy consent, plaintext, delegation, recovery, and role claim.

## 5. View And Permission Requirements

Minimum Odoo menu groups:

- Member self-service: read own masked status, own consents, own action drafts.
- Member support staff: create support draft, read masked refs, cannot approve own or view raw plaintext by default.
- Member manager: manage registration workflow, cannot approve own record, cannot override member consent.
- Member admin/owner reviewer: approve high-risk role claims, seal evidence, still cannot stand in for member consent.
- Audit reviewer: read append-only event records and evidence refs, no secret/raw plaintext field access.

Every sensitive form should show:

- flow safety decision.
- member consent state.
- evidence ref.
- verifier ref.
- revocation availability.
- forbidden automation note when payment, contact, raw data, production write, or delegation is involved.

## 6. Acceptance Gate

The integration may move from design to implementation only when these checks are true:

- no production Odoo DB write during design and dry-run;
- no module upgrade or service restart without separate Total Field release packet;
- every member-sensitive flow separates `flow_safety_decision` from `member_consent_state`;
- all external IDs, phone, LINE id, Google subject, address, payment data, and raw contact fields are hash/ref/masked by default;
- every approval has `evidence_ref` or remains HOLD;
- every member confirmation path supports denial and revocation;
- self-review and proxy consent requests return HOLD or BLOCK;
- payment and RSVP paths create candidate refs only until explicit member confirmation and formal Odoo workflow approval.

## 7. Landing Order

```text
P1: mobile/browser member dashboard, ref-only, no Odoo write
P2: review event + evidence ref + no-self-review hardening
P3: organization/member relation and responsible-person claims
P4: family/delegation/recovery expansion
P5: contact approval and integration adapter status
P6: route hardening, golden prompts, mobile screenshots, evidence seal
```

## 8. Final Sentence

```text
總場守安全，Odoo 承載流程，會員守主權。
```

## 9. Total Field Landing Review

Landing review:

```text
runtime/total_field/queries/ASK_TOTAL_FIELD_ODOO_MEMBER_SCENARIO_LANDING_20260629_183414/TOTAL_FIELD_RESPONSE.md
```

Decision:

```text
ACCEPT_FOR_DESIGN_LANDING
```

Formal Odoo release state:

```text
HOLD_UNTIL_SEPARATE_RELEASE_PACKET
```

Meaning:

- this document is accepted as the canonical Total Field design reference for Odoo member scenario implementation;
- this acceptance does not approve Odoo production DB writes, Odoo module upgrades, service restarts, payment capture, automatic RSVP submission, or member plaintext reads;
- formal implementation must start from a separate Total Field release packet.
