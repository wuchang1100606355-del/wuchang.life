# Member Registration Batch 006 Nickname Field

timestamp: 20260602_123048
head: 62fb836

result: MEMBER_REGISTRATION_NICKNAME_FIELD_PASS

added:
- wuchang.member.registration.member_nickname
- wuchang.member.identity.code.member_nickname
- wuchang.member.identity.code.nickname_updated_at
- nickname field shown in registration list/form

principle:
- nickname is member-editable display name
- nickname is not legal name
- nickname is not identity verification data
- raw identity privacy boundary unchanged

remote_log:
- evidence/member_registration/member_registration_nickname_patch_20260602_123048.txt

db_write:
- yes, Odoo module upgrade only

backup:
- pre-upgrade PostgreSQL dump created on taiji01

not_executed:
- Docker restart
- service restart
- secret output
- broad chmod/chown
