# Member Vault D Drive Boundary

版本：2026-05-11

## Boundary

會員資訊庫位於：

```text
D:/Taiji_Member_Vault/
/mnt/d/Taiji_Member_Vault/
```

此區為：

- 本機高權限個資守門區
- 不自動同步雲端
- 不進無敏唯讀全設備區
- 不由 AI 任意讀取
- 需本人審查與 audit

## Relationship To Other Storage

| Storage | Relationship |
|---|---|
| Cloud readonly staging | must not receive member plaintext |
| Linux runtime workspace | may only receive schema/redacted/import-review artifacts |
| C scenario data | may prepare operational staging, but member master stays guarded |
| D member vault | authoritative protected member information boundary |

## Safe Flow

```text
D member vault
→ owner-reviewed extract
→ redaction / minimization
→ C export_review or Linux import_review
→ Odoo import staging
→ human confirmation
→ audit
```

## Blocked Flow

```text
D member vault
→ cloud staging
```

```text
D member vault
→ external AI plaintext
```

```text
D member vault
→ direct natural-language production mutation
```

