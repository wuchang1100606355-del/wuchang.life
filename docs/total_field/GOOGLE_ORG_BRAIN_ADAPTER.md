# Google Org Brain Adapter

STATE=PASS_GOOGLE_ORG_BRAIN_ADAPTER_PACKET
RUN_ID=GOOGLE_ORG_BRAIN_ADAPTER_20260710_121217
TIME=2026-07-10T12:12:17

PACKET=runtime/total_field/google_org_brain/GOOGLE_ORG_BRAIN_ADAPTER_20260710_121217/GOOGLE_ORG_BRAIN_ADAPTER_PACKET.json
PACKET_SHA256=5b0f16fad05383260f368bdaa4924de6dfda919d937f34d92e9e9ad7e6624fd0
REQUIREMENTS_CANDIDATE=runtime/total_field/google_org_brain/GOOGLE_ORG_BRAIN_ADAPTER_20260710_121217/GOOGLE_ORG_BRAIN_REQUIREMENTS.txt

## Safety
- DEPLOY=NO
- DB_WRITE=NO
- RESTART=NO
- ROUTER_WRITE=NO
- RAW_API_KEY=FORBIDDEN
- SERVICE_ACCOUNT_JSON_INLINE=FORBIDDEN
- MEMBER_PLAINTEXT=NO
- CLOUD_COMPLETION=CANDIDATE_ONLY
- HUMAN_REVIEW_REQUIRED=YES

## Decision
使用 Google 組織訂閱與 Google Cloud / Gemini / Vertex 能力作為「組織商業大腦」。
本機與各節點只接入 adapter，不直接成為雲端權威，不持有 raw secret。

## Readiness Check
```json
{
  "state": "GOOGLE_ORG_BRAIN_READINESS_CHECK",
  "imports": {
    "google": true,
    "google.auth": true,
    "google.cloud": true,
    "google.cloud.aiplatform": false,
    "google.cloud.secretmanager": false
  },
  "env_refs": {
    "GOOGLE_CLOUD_PROJECT": false,
    "GOOGLE_APPLICATION_CREDENTIALS": false,
    "GEMINI_API_KEY": false
  },
  "raw_secret_printed": false,
  "authority": "CANDIDATE_ONLY_NO_TOTAL_FIELD_AUTHORITY"
}Next
人工確認 Google Cloud project、組織訂閱、服務帳戶策略。
人工確認是否在 venv 安裝 requirements candidate。
建立真正 cloud worker：sanitized request -> Google candidate -> CLOUD_CANDIDATE_RETURN.md。
總場驗證候選，不得自動部署。
