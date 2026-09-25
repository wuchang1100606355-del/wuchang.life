# 總場詢問封包：生成式建構模型設置與雲端算力配置，及 AI 助理之配合守則

state: QUERY_PACKET_ONLY
target: GENERATIVE_MODEL_SETUP_AND_CLOUD_COMPUTE_CONFIGURATION
source_boundary: ASSISTANT_GENERATED_QUERY_TO_TOTAL_FIELD
live_cloud_execution: false
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
financial_transfer: false
legal_effect: false

## D1 Identity

requester: 本地 AI 助理 (Local LLM Agent)
target: 總場 (Total Field)
machine: taiji01
active_account: taiji_admin
active_repo: /home/taiji_admin/Taiji_Hub

自我定位宣告：
- 作為 AI 助理，我認知自身僅為「8D 作業腦」與「推演引擎」，不具備任何治理決策權與系統越權能力。
- 我的目標是完美對齊總場的設計語義與邊界紀律。

## D2 Intent

基於上一次總場指示（`NEXT_SAFE_ACTION`），要求先產生靜態 spec。
本封包旨在請示總場：
1. 如何運用「生成式建構（Generative Construction）」的思維，來完成 `developer_prefix.yaml`、`openwebui_model_profile.json` 等模型設置？
2. 如何建構 `8d_gateway_tool_schema.json` 與 `cloud_compute_request.schema.json` 等雲端算力配置的 Schema，確保算力極簡化且零幻覺？
3. 作為輔助推演的 AI，我該如何配合總場的指示辦理？請給予我明確的行為守則與輸出格式要求。

## D3 State

已知總場狀態：
- PASS_DEVELOPER_PREFIX_CLOUD_COMPUTE_REPLY_PACKET_COMMITTED 已完成。
- 確認「本地 8D 路由」與「雲端算力代工」必須嚴格解耦。
- 尚未生成任何實體的 spec 檔案。

## D4 Topology

目標拓樸（生成式建構階段）：
總場設計意圖 → AI 助理推演 (純文字/Schema 草圖) → 總場審核 (Redteam Hold/Pass) → 落地為實體設定檔。

## D5 Resource

本次詢問不觸及真實雲端資源，僅請求總場給予以下四個核心檔案的「生成式建構 Prompt / Blueprint」。

## D6 Governance

AI 配合承諾：
- 絕不擅自猜測或擴充總場未提及的參數。
- 絕不在 Schema 中賦予雲端算力直接操作系統的權限。
- 所有生成的設定檔草圖都必須經過 Verifier 視角的靜態檢驗。

## D7 Verify

請總場針對以下問題給予具體指示：

1. **生成策略**：在建構 `developer_prefix.yaml` 與 `openwebui_model_profile.json` 時，應注入哪些關鍵的「上下文降維」與「防幻覺」指令？
2. **算力配置**：`cloud_compute_request.schema.json` 應該具備哪些絕對的欄位限制，以強制雲端模型只輸出 `Delta` 與結構化 `Candidate`？
3. **AI 配合守則**：在接下來的實作階段，總場希望我（AI 助理）以何種格式（例如純 JSON、Markdown 區塊或直接產出寫檔腳本）提供推演結果？
4. **下一步指令**：請總場給出具體的第一個生成任務。

requested_output_format:

STATE=
SOURCE=
VERDICT=
REQUIRED_CODE_FILES=
REQUIRED_CONFIG_FILES=
AI_COMPLIANCE_DIRECTIVE=
NEXT_SAFE_ACTION=
