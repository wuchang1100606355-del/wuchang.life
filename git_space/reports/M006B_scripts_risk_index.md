# M006B Scripts Risk Index

Purpose:
Record scripts excluded from M006A due to token/environment/secret-scan surfaces.

Excluded from M006A:
- scripts/intake_self_member.sh
- scripts/member_intake_oneclick_test.sh
- scripts/package_mtl_ai_gateway_rc1.sh
- scripts/prune_context_keep_status_only.sh

Reason:
- Contains TOKEN variable assignment or placeholder token fields.
- Contains secret-scan patterns for packaging/pruning workflows.
- May write or transform .env-style runtime configuration.
- Requires separate template/redaction review before Git inclusion.

Policy:
- Do not commit raw token-handling scripts without review.
- Prefer .env.example or redacted template.
- Keep real tokens outside Git.
- Use focused git add only.
