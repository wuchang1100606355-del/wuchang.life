# C Drive To Organization Cloud Redaction Flow

版本：2026-05-11

## Flow

```text
C:/Users/o0930/Taiji_Data/<scenario>
→ export_review
→ redaction / summarization
→ redacted_cloud_candidates
→ owner review
→ Taiji_Hub_Org_Readonly_Cloud_Staging
→ organization shared readonly cloud
```

## Block Conditions

Stop if the candidate contains:

- 明文個資
- 會員個別進度
- 商家營業機密
- 管委會未公開敏感會議資訊
- secret / token / key / credential
- 可逆推個人的 hash / tensor / vector label

## Required Review Record

```json
{
  "event": "c_to_cloud_redaction_review",
  "source_path": "/mnt/c/Users/o0930/Taiji_Data/<scenario>/<file>",
  "candidate_path": "/mnt/c/Users/o0930/Taiji_Data/redacted_cloud_candidates/<file>",
  "contains_personal_data": false,
  "contains_business_secret": false,
  "contains_member_progress": false,
  "contains_secret": false,
  "owner_reviewed": true,
  "decision": "allow_with_audit",
  "sha256": "sha256:<hash>"
}
```

