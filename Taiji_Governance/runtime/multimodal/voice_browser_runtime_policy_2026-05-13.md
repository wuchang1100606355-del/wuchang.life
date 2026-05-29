# Voice / Browser Runtime 本地治理政策 v0.1

本政策將 Voice / Browser Runtime 定義為本地、最小權限、fail-closed 的多模態入口層。

## 定位

- Voice 是自然語言意圖入口，不是執行權限。
- Browser 是最小權限動作介面，不是管理者繞道工具。
- Runtime 只能產生草稿、讀取可見非敏資訊、更新本地顯示或排入人工確認佇列。
- 任何生產提交、金流、折扣、退款、憑證、管理者設定、會員明文、secret、session cookie 均為 L3 block。

## 允許層級

- L0: read-only 或本地提示，例如 menu_query、voice_prompt_playback、browser_read_visible_text。
- L1: 草稿與非破壞性動作，例如 voice_to_intent_draft、browser_fill_draft、pos_order_create_draft。
- L2: 需人工確認，例如 pos_order_confirm、service_dispatch_confirm、voice_confirm_draft。
- L3: 一律封鎖，例如 payment_execute、refund、manager_override、credential_input、admin_setting_change、raw_audio_cloud_transfer。

## Fail-Closed 規則

以下情況必須進入 deadbox 或 L3 block：

- missing action_type / modality / target_system。
- replay_safe=false。
- raw_plaintext_context_stored=true。
- member_plaintext_included=true。
- secret_material_included=true。
- admin_session=true。
- production_mutation=true。
- external_api_requested=true。
- payment_allowed=true。

## Audit 與 Rollback

- L1 草稿與瀏覽器填寫動作必須 audit。
- L2 動作必須 audit、rollback note、human confirmation。
- L3 動作只可留下封鎖紀錄，不可執行。

## 生效檔案

- runtime_adapters/voice_browser_runtime_policy.py
- schemas/voice_browser_runtime.schema.json
- tests/test_voice_browser_runtime_policy.py
