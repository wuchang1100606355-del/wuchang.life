# 主權 AI 會員系統

English name: **Sovereign AI Member System**

## Product position

以會員本地主權為核心，將會員身分、意圖、雲端 AI 候選、本地總場裁決、服務流程與證據治理整合於單一產品。會員保留授權權；小J是本地意圖層與執行前治理介面；雲端模型只產生候選；正式操作只能由本地總場依權限、硬風險與證據裁決。

## Product chain

```text
會員主權
-> Google / 8D 身分
-> Odoo 會員流程
-> 小J本地意圖層
-> 雲端候選大腦
-> 本地總場驗證
-> 會員入口 / 服務介面
-> 證據封存
-> 可落地產品
```

## Verified source surfaces

| Product surface | Existing integration | Current source state |
|---|---|---|
| Member entry | `wuchang_member_registration/views/login_templates.xml` | Product name, login, signup, LINE and Google entry links |
| Member registration | `wuchang_member_registration` | Consent, review state, identity code and backend review action |
| Google identity | `wuchang_google_member_login` | OAuth login/callback/welcome source; live use requires configured provider refs |
| 8D identity | group registration routes and packet verifier | Candidate and confirmation flow; formal authority remains local |
| XiaoJ intent | `wuchang_cafe_ai_gateway/services/p1_intent_engine.py` | Local intent candidate flow |
| Cloud candidate | `tools/total_field/w7tp_vertex_candidate_gateway.py` | Candidate-only one-shot gateway |
| No-plaintext boundary | `tools/xiaoj_gemini_no_plaintext_candidate_packet.py` | Ref-only candidate packet and explicit no-plaintext flags |
| Local execution gate | `tools/w7tp_packet_inference_runtime.py` | Local `ALLOW` / `HOLD` / `BLOCK` decision boundary |
| Evidence and operator console | AI Eventbook and Total Product Handoff views | Existing backend actions exposed under one product menu |

The requested `Taiji_Odoo/addons/wuchang_member_ai_portal` path is not present in this checkout. This product integration therefore uses the verified login surface and existing Odoo modules; it does not create a parallel portal, public controller, or duplicate member model.

## Member and operator flow

1. The member opens `/web/login`, `/web/signup`, or the configured Google member entry.
2. Odoo verifies the available identity and consent context. The system does not authorize on the member's behalf.
3. XiaoJ converts the service request into a local intent/candidate packet.
4. Only de-identified refs, intent codes, schema context, and technical context may enter a cloud candidate request.
5. Cloud output is normalized as `CANDIDATE_ONLY`.
6. The local execution gate decides `ALLOW`, `HOLD`, or `BLOCK` and records evidence.
7. The UI presents PASS, HOLD, manual-confirmation, or error state without exposing member plaintext or credentials.

## Operator guide

After the source is installed through the owner-approved Odoo change path, authorized backend users can open **WuChang Cafe -> 主權 AI 會員系統**:

- **會員入口** opens the existing Odoo login surface.
- **會員註冊審查** opens the existing registration list/form action.
- **候選與證據鏈** opens the existing AI Eventbook action.
- **操作員交接與健康狀態** opens the existing Total Product Handoff action.

An operator must not treat a cloud response as approval. HOLD and manual-confirmation states remain local decisions. Any identity, payment, role, production write, or release action requires its existing human/local gate.

## Configuration

- Configure Google member login through the existing module and provider-ref process. Do not place credentials in documentation or candidate packets.
- Keep member data, credential material, cookies, and session secrets local.
- Use only `member_ref`, `intent_code`, schema refs, policy refs, evidence refs, and other de-identified technical context for cloud candidates.
- Preserve existing Odoo access groups for registration review and backend actions.

## Installation and upgrade boundary

This changeset is source-only and introduces no Python model field or schema change. `DB_MIGRATION_REQUIRED=NO` for these files. Installation still requires an owner-approved Odoo module update, which is outside this task because live DB writes, module updates, deploys, and restarts are prohibited by repository policy.

Safe owner sequence:

1. Review the exact commit and changed files.
2. Back up the target Odoo database according to the existing operator procedure.
3. Use the established Odoo module-update path for `wuchang_member_registration` and `wuchang_cafe_ai_gateway` in an approved maintenance window.
4. Verify login, registration, Google configuration, menu visibility, access rules, AI Eventbook, Total Product Handoff, and Odoo health.
5. If any live route, access rule, or health check fails, keep production state at HOLD and preserve the evidence.

## Static validation

```bash
python3 -m py_compile scripts/verify/verify_sovereign_ai_member_product.py
python3 scripts/verify/verify_sovereign_ai_member_product.py
python3 -m pytest -q tests/test_sovereign_ai_member_product.py
```

The verifier parses the changed XML and manifest, verifies source routes/actions, checks candidate-only and local-gate markers, and performs a changed-surface forbidden-copy scan. It does not write a database or call a live service.

## Demo flow

1. Open the branded login page and identify the member-sovereignty, cloud-candidate, and local-authority states.
2. Select login, registration, or the configured Google identity path.
3. In the backend product menu, open the member review queue.
4. Present a de-identified XiaoJ intent packet and its candidate-only cloud result.
5. Show the local `ALLOW` / `HOLD` / `BLOCK` result and any manual-confirmation requirement.
6. Open AI Eventbook and Total Product Handoff to show the accountable evidence and operator state.

## Current landing statement

The source integration, product copy, Odoo menu wiring, documentation, and static smoke checks can be completed without live side effects. Live product availability and `ODOO_HEALTH=PASS` must not be claimed until the owner-approved module update and runtime checks are performed.
