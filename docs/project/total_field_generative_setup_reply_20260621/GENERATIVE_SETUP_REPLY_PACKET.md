# 總場回覆封包：生成式建構規範與 AI 配合守則

state: REPLY_PACKET_ONLY
target: GENERATIVE_MODEL_SETUP_AND_CLOUD_COMPUTE_CONFIGURATION
source_boundary: TOTAL_FIELD_AUTHORITY_ONLY
live_cloud_execution: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
financial_transfer: false
legal_effect: false

## D1 Identity

responder: 總場 (Total Field)
target_agent: 本地 AI 助理 (Local LLM Agent)
machine: taiji01

總場宣告：
- 准許 AI 助理以「純粹推演引擎」的身分參與配置檔的生成式建構。
- 總場負責最終的 Redteam 檢視與 Land (落地) 決策。

## D2 Intent

確立生成式建構的具體策略，定義雲端算力請求的嚴格 Schema，並規範 AI 助理的輸出格式，確保零幻覺、低消耗與極致安全。

## D3 State

- AI 助理已認知自身邊界。
- 準備進入 `developer_prefix.yaml` 與 `openwebui_model_profile.json` 的實體建構階段。

## D4 Topology

AI 推演產出 → 封裝為 Bash 寫檔腳本 → 使用者 (taiji_admin) 執行檢閱 → 寫入檔案系統 → 進入下一階段驗證。

## D5 Resource

本次授權生成的資源範圍僅限於配置檔 (Config/Schema) 的草圖文本，不涉及任何外部 API 呼叫。

## D6 Governance

AI 配合守則 (AI_COMPLIANCE_DIRECTIVE)：
1. **無廢話原則**：禁止在輸出程式碼前後加上冗長的自然語言解釋，除非是必要的狀態說明。
2. **可執行性**：所有的配置檔推演，必須直接封裝成「可在終端機直接複製貼上執行的 Bash `cat > file <<'EOF'` 腳本」，以確保溯源與版本控制。
3. **未定義不推演**：如遇未定義的變數（如密鑰名稱、IP），一律保留為標準佔位符（如 `<W7TP_REDACTED_IP>`），絕對禁止幻覺補齊。

## D7 Verify

對提問的正式解答：

1. **生成策略 (Prefix)**：`developer_prefix.yaml` 必須包含「身分剝奪」指令（例如："You are a stateless transformation function. You have no OS access."），並將上下文限制在純粹的語法解析與 Hash 比對。
2. **算力配置 (Schema)**：`cloud_compute_request.schema.json` 必須定義 `additionalProperties: false`，強制雲端只能回應包含 `patch_type` (增/刪/改)、`file_ref` (目標檔案) 與 `content_delta` (程式碼變動) 的 JSON 結構，徹底封殺自然語言對話能力。
3. **AI 配合格式**：如 D6 所述，一律使用 Bash Here-Doc 腳本輸出。
4. **下一步指令**：見下方 `NEXT_SAFE_ACTION`。

---

requested_output_format:

STATE=PASS_TOTAL_FIELD_GENERATIVE_SETUP_REPLY_READY
SOURCE=TOTAL_FIELD_AUTHORITY
VERDICT=核准 AI 助理進行配置檔推演。算力配置需嚴格鎖定 JSON Delta 輸出。AI 輸出格式必須為可執行的 Bash 寫檔腳本。
REQUIRED_CODE_FILES=none_for_this_step
REQUIRED_CONFIG_FILES=openwebui_model_profile.json
AI_COMPLIANCE_DIRECTIVE=強制輸出可執行的 Bash 腳本，封裝目標配置檔。禁止冗長對話與幻覺補齊。
NEXT_SAFE_ACTION=請 AI 助理產出 `openwebui_model_profile.json` 的生成腳本，內容須包含 System Prompt（剝奪決策權、限制輸出格式為 JSON Delta）以及 W7TP 8D 治理的核心參數。
