# Member Registration Batch 007 Avatar Field

timestamp: 20260602_123409
head: b7148b5

result: MEMBER_REGISTRATION_AVATAR_FIELD_PASS

added:
- wuchang.member.registration.member_avatar
- wuchang.member.registration.member_avatar_source
- wuchang.member.registration.member_avatar_url_hash
- wuchang.member.registration.member_avatar_updated_at
- wuchang.member.identity.code.member_avatar
- wuchang.member.identity.code.member_avatar_source
- wuchang.member.identity.code.member_avatar_url_hash
- wuchang.member.identity.code.member_avatar_updated_at
- wuchang.member.external.auth.provider_picture_url_hash

behavior:
- member can paste/upload thumbnail into same member_avatar field
- LINE/Google profile image can be fetched into same member_avatar field through provider sync method
- raw provider picture URL is not required for daily output
- thumbnail is display data, not legal identity verification data

remote_log:
- evidence/member_registration/member_registration_avatar_patch_20260602_123409.txt

db_write:
- yes, Odoo module upgrade only

backup:
- pre-upgrade PostgreSQL dump created on taiji01

not_executed:
- Docker restart
- service restart
- secret output
- broad chmod/chown
