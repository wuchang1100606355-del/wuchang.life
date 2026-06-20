# 紅隊告警：雲端算力 dry-run 設定錯誤

state: REDTEAM_ALERT_HARD_HOLD
target: CLOUD_COMPUTE_DRYRUN_MISCONFIG
source: current_total_field_status + local candidate file scan
deploy: false
service_restart: false
secret_read: false
member_plaintext_read: false
db_write: false
cloud_compute_called: false

## 紅隊判定

若檔案以 dry-run / validation 命名，但內容包含下列行為，必須列為 HARD_HOLD：

- 使用 service account key JSON path
- 設定 GOOGLE_APPLICATION_CREDENTIALS
- 產生或使用 access token
- 呼叫 Gemini / Vertex generateContent
- 使用 curl POST 觸發真實雲端模型
- 以 HTTP 200 判斷雲端算力已通

這不是安全 dry-run；這是實際雲端算力與 credential 作業路徑。

## 正確安全邊界

允許：

- gcloud account / project 查詢
- auth/impersonate_service_account 設定查詢
- service account impersonation 對 project describe 的 dry-run
- token 不輸出
- key 不讀取
- API 不啟用
- 不呼叫 generateContent
- 不 deploy / restart / DB write

禁止：

- cat ADC json
- cat service account key json
- print token to screen
- use GOOGLE_APPLICATION_CREDENTIALS with local key json
- call Gemini / Vertex generateContent as validation
- commit key or generated credential files
- label real compute call as dry-run

## Findings

- path: scripts/cloud_service_account_validation_dryrun.sh | risk: SERVICE_ACCOUNT_KEY_JSON_PATH | verdict: HARD_HOLD | matched_terms: gcp-sa-key.json, GOOGLE_APPLICATION_CREDENTIALS
- path: scripts/cloud_service_account_validation_dryrun.sh | risk: TOKEN_GENERATION | verdict: HARD_HOLD | matched_terms: print-access-token, ACCESS_TOKEN=
- path: scripts/cloud_service_account_validation_dryrun.sh | risk: REAL_VERTEX_GEMINI_CALL | verdict: HARD_HOLD | matched_terms: generateContent, aiplatform.googleapis.com, gemini-1.5-pro
- path: scripts/cloud_service_account_validation_dryrun.sh | risk: MISLEADING_DRYRUN_NAME | verdict: HARD_HOLD | matched_terms: PASS_CLOUD_COMPUTE_ACCESS_VERIFIED
- path: scripts/cloud_service_account_validation_dryrun.sh | risk: CURL_REAL_POST | verdict: HARD_HOLD | matched_terms: curl, -X POST


## Next Safe Action

1. Do not execute the misconfigured validation script.
2. Do not commit the misconfigured script.
3. Replace with service-account-ref / impersonation-only dry-run.
4. First safe verification must be project describe through impersonation only.
