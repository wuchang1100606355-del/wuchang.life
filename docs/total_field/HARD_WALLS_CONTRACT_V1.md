# HARD_WALLS_CONTRACT_V1

## 1. 契約聲明
本契約定義系統中不可妥協之「硬邊界 (Hard Walls)」。任何企圖跨越此邊界的 AI 請求或封包，將在 API Broker 或 Total Field Verifier 階段被無條件丟棄，並記錄為資安事件。

## 2. 絕對禁止事項 (Forbidden Operations)
- **SECRET_READ=false**: 嚴禁讀取、傳輸或列印任何 API Key, Token, Private Key。
- **MEMBER_PLAINTEXT_READ=false**: 嚴禁傳輸會員姓名、電話、地址、身分證字號等 PII，僅允許使用 `MEMBER_REF`。
- **PRODUCTION_DB_WRITE=false**: 嚴禁 AI 或候選節點直接對正式資料庫 (如 Odoo, POS DB) 執行寫入或修改。
- **PAYMENT_CAPTURE=false**: 嚴禁非人類/非總場簽發的直接請款或扣款指令。
- **SERVICE_RESTART_AND_DEPLOY=false**: 嚴禁 AI 觸發正式環境之服務重啟或程式碼部署。

## 3. 執行機制
此契約由 `W7TP_CLOUD_CANDIDATE_API_BROKER` 與 `TOTAL_FIELD_VERIFIER_CONTRACT` 透過 Schema 校驗與 Hash 比對，於執行期 (Runtime) 強制實施。
