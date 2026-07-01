# XiaoJ Sovereign Member / 8D / Gemini LLM Readiness Matrix

STATE=HOLD_P2_PRODUCT_RELEASE_GAPS_PRESENT

## Conclusion

These capabilities are partially implemented, but they are not all fully landed
as production-ready flows.

The safe current statement is:

```text
會員註冊、Google 會員登入、團體 8D 候選註冊、小J 會員瀏覽器、Gemini/LLM 設定原型已存在；
但 Odoo 個資回傳本機、8D 代理身分更換、主權小J正式領用、使用者 Gemini API 專屬 LLM 尚未完整產品化 release。
```

## 1. 會員資訊總廠 / 協會權限

Current status: `PARTIAL_LANDED`

Current evidence:

- `Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py`
- `Taiji_Odoo/addons/wuchang_member_registration/security/wuchang_member_groups.xml`
- `configs/identity/WUCHANG_ROOT_IDENTITY.yaml`

What exists:

- Member registration model.
- Member consent ledger.
- External auth binding model.
- Staff, manager, admin group concepts.
- Owner/admin review gate for organization or responsible-person registrations.

Not yet complete:

- Formal legal-person / association-office delegation UI.
- Verified release packet for changing association-level authority.
- Production procedure for uploading and verifying human-world role proof.

## 2. Odoo 取得個資後如何傳回本機

Current status: `NOT_FULLY_LANDED`

Current evidence:

- `Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py`
- `Taiji_Odoo/addons/wuchang_google_member_login/models/res_partner.py`
- `Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py`

What exists:

- Google OAuth can create or update `res.partner`.
- Google subject is bound through a hash for group 8D flow.
- Runtime 8D packets avoid member plaintext by using refs and hashes.

What does not exist yet:

- A formal local-return/export endpoint for Odoo-held personal data.
- A user-owned encrypted local vault import flow.
- A verified consent/ref packet for returning personal data.
- A verifier proving returned packets contain only the minimum necessary fields.

Target flow:

```text
member_login_or_8d_scan
  -> user requests personal data return
  -> Odoo verifies member identity + consent + authority
  -> Odoo builds encrypted local-return packet
  -> local device/vault receives packet
  -> cloud/LLM receives only member_ref / behavior_ref
```

Production rule:

```text
個資可回到會員本機或會員控制的 vault；
不可回到雲端 LLM；
不可進 prompt；
不可無 consent_ref 匯出。
```

## 3. 如何更換八維碼代理身分

Current status: `PARTIAL_LANDED`

Current evidence:

- `Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py`
- `Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py`
- `scripts/verify/verify_group_member_8d_registration.py`

What exists:

- Group 8D batch generation.
- 8D claim route.
- Google / LINE / manual provider hash binding.
- Dry-run confirmation packet.

What does not exist yet:

- Formal replacement/rotation action.
- QR invalidation list.
- Delegate recovery quorum.
- Old packet revocation evidence chain.

Target flow:

```text
create delegate replacement request
  -> verify owner/admin or recovery quorum
  -> revoke old packet_ref and provider binding
  -> issue new packet_ref + d8_ref
  -> seal replacement evidence
  -> UI shows old=revoked, new=active
```

## 4. 如何領用主權小J

Current status: `PARTIAL_LANDED`

Current evidence:

- `runtime/member_browser/ACTIVE_XIAOJ_MEMBER_BROWSER_RELEASE.json`
- `scripts/verify/verify_xiaoj_member_browser_release.py`
- `scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py`
- `docs/total_field/XIAOJ_MEMBER_BROWSER_1B_CONTROL_SPEC.md`

What exists:

- Member browser packaged release artifact.
- Candidate-only browser packets.
- Member refs, behavior refs, cloud compute refs.
- No plaintext 8D return packet pattern.

What does not exist yet:

- Odoo-facing claim/activate endpoint for one human member.
- Claim wizard binding `member_identity_code` to a XiaoJ instance.
- Device binding and revocation UI.
- Transfer/recovery operation.

Target flow:

```text
member logs in or scans 8D
  -> local device creates XiaoJ claim packet
  -> Odoo verifies member/ref/consent
  -> XiaoJ instance binds member_identity_code + device_ref
  -> member can revoke, rotate, or transfer XiaoJ
```

## 5. 如何使用使用者 Google Gemini API 專屬 LLM

Current status: `P1_NO_PLAINTEXT_CONTRACT_LANDED_RUNTIME_NOT_RELEASE_READY`

Current evidence:

- `Taiji_Odoo/addons/wuchang_core/models/settings.py`
- `Taiji_Odoo/addons/wuchang_core/views/settings_views.xml`
- `Taiji_Odoo/addons/wuchang_core/controllers/main.py`
- `Taiji_Odoo/addons/wuchang_core/models/api_account_separation.py`
- `packets/product_av_ordering_ai/gemini_no_plaintext_candidate_worker_contract.json`
- `tools/xiaoj_gemini_no_plaintext_candidate_packet.py`
- `scripts/verify/verify_xiaoj_gemini_no_plaintext_candidate_worker.py`

What exists:

- `ai_mode`, `gen_model`, `google_api_key`, `ollama_model` settings.
- `/wuchang/config/llm/get`
- `/wuchang/config/llm`
- `/wuchang/llm/health`
- `/wuchang/llm/generate`
- Basic Google/Gemini generation paths.
- API account separation model.
- P1 no-plaintext Gemini candidate-worker packet contract.
- Offline packet builder for redacted task view, candidate-only cloud payload, and local zero-network-RTT decision.

Why this is not release-ready:

- Legacy code stores Google API key in `ir.config_parameter`.
- Config route can accept raw `google_api_key`.
- Public generation endpoint exists and needs a member/authority gate.
- There is no per-user Gemini key ref / vault connector.
- There is no member LLM release packet.
- The new P1 verifier proves the no-plaintext packet pattern, but legacy runtime routes still need migration.
- There is no production Gemini connector consuming only the no-plaintext packet.
- Legacy raw-key runtime has not yet been migrated behind key-ref vault and member release gate.

Target safe configuration:

```text
user supplies Gemini API key to vault only
  -> vault returns GEMINI_KEY_REF
  -> Odoo stores GEMINI_KEY_REF, not raw key
  -> member LLM config binds member_ref + model_ref + quota_ref + consent_ref
  -> generation is candidate-only
  -> local verifier checks no raw API key, no member plaintext, no execution authority
```

Minimum fields for future release:

```text
member_ref
gemini_key_ref
model_ref
quota_ref
consent_ref
usage_scope_ref
revocation_ref
evidence_hash
```

## 6. 總場 LLM 真實/幻境分層治理

Current status: `P1_CONTRACT_LANDED`

Core definition:

```text
LLM hallucination: `CONDITIONALLY_ALLOWED_AS_IMAGINED_CANDIDATE`
```

這不是把 LLM 幻覺當錯誤一律消滅，而是把它關進總場提供的環境：

```text
REAL_VERIFIED
IMAGINED_CANDIDATE
EXECUTABLE_AUTHORIZED
```

Critical qualification:

```text
LLM 本身不是事實權威。
總場提供 truth boundary、evidence anchor、本地重構上下文與 verifier status，
使 LLM 只能在被標記的真實層、候選幻境層或可執行授權層中輸出。
```

所以「讓 LLM 分清真實或幻境」的精確技術意思是：

```text
LLM output is constrained by total-field supplied reality context;
real claims require local evidence refs;
execution claims require the local gate;
otherwise the output remains IMAGINED_CANDIDATE.
```

Allowed:

- LLM 可以在 `IMAGINED_CANDIDATE` 中生成候選文案、候選回覆、候選方案、人形服務語氣與互動想像。
- LLM 可以讓體驗更自然、更有人味，但 UI 與封包必須標示它仍是 candidate。
- 本地可以在 Gemini 尚未回來前先顯示本地 fallback 或候選 pending。

Forbidden:

- LLM 不可把想像內容標成 `REAL_VERIFIED`。
- LLM 不可把候選內容標成 `EXECUTABLE_AUTHORIZED`。
- LLM 不可主張 POS 已下單、付款已完成、會員身分已成立、LINE WORKS 已送達，除非本地證據與 verifier 已確認。

## 7. 低成本模型路由與後續落地順序

Current status: `P1_LLM_COST_SAVING_MODEL_ROUTER_READY`

Current evidence:

- `packets/product_av_ordering_ai/llm_cost_saving_model_router_contract.json`
- `packets/product_av_ordering_ai/xiaoj_low_cost_model_release_sequence_contract.json`
- `Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/llm_cost_saving_model_router.py`
- `tools/xiaoj_llm_cost_saving_model_router.py`
- `scripts/verify/verify_xiaoj_llm_cost_saving_model_router.py`
- `docs/product/XIAOJ_LLM_COST_SAVING_MODEL_ROUTER_GUIDE.md`

Default model roles:

```text
gpt-5.5: total-field planning / patent core review / red-team review / final release judgment
gpt-5.4-mini: Codex implementation / documentation fill / focused verifier repair / Odoo/LINE module modification
gemini-2.5-flash-lite: merchant runtime candidate generation / customer-service draft / menu copy / social draft
gpt-5.4-nano: classification / format conversion / field backfill / report summary only
```

Hard boundary:

```text
cheap model output is always candidate-only;
cloud model is not authority;
local discrete verifier remains the authority;
nano is not allowed to make architecture decisions.
```

Ordered P2 gates:

```text
1. migrate_gemini_raw_key_to_gemini_key_ref_vault_binding
2. add_member_llm_release_gate
3. add_local_personal_data_return_packet
4. add_8d_delegate_rotation_and_revocation
5. add_sovereign_xiaoj_claim_activation
6. only_then_enable_formal_pos_member_payment_release_gates
```

Authority rule:

```text
Gemini / LLM = imagined candidate and language quality
Total Field = reality distinction, local reconstruction, verifier, evidence seal
Human owner/admin = formal release root of trust
```

## Operational Answer

If you ask "can I operate this today?", the answer is:

- Google member login: `YES, if OAuth client_id/client_secret are configured and module is deployed`.
- Group 8D registration: `YES for candidate/dry-run and review flow`.
- Odoo personal data return to local: `NO, needs local-return packet`.
- Replace 8D delegate identity: `NO, needs rotation/revocation flow`.
- Claim sovereign XiaoJ: `PARTIAL, member browser exists but no Odoo claim wizard`.
- LLM hallucination / imagination: `YES, conditionally allowed as IMAGINED_CANDIDATE`.
- User Gemini API dedicated LLM: `P1 no-plaintext candidate contract exists, but runtime is not production release-ready until key-ref vault flow is added`.

## Safety Boundary

```text
raw_member_plaintext_to_cloud=false
raw_api_key_to_repo=false
raw_api_key_to_llm_prompt=false
odoo_personal_data_export_requires_consent_ref=true
8d_identity_replacement_requires_revocation_evidence=true
sovereign_xiaoj_claim_requires_member_identity_ref=true
```
