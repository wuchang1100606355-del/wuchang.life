# Member Registration Batch 005H PGPASSWORD Install

timestamp: 20260602_122849
head: 90d0ed6

result: MEMBER_REGISTRATION_005H_PASS

fixed:
- Previous 005G reached PostgreSQL host but failed with no password supplied.
- 005H uses masked internal PGPASSWORD env, not command-line password output.

remote_log:
- evidence/member_registration/member_registration_odoo_install_005H_pgpassword_20260602_122849.txt

executed:
- copied addon into actual Odoo extra-addons mount
- installed Odoo module wuchang_member_registration
- verified module state
- verified wuchang.member.* models

db_write:
- yes, Odoo module install only

not_executed:
- Docker restart
- service restart
- secret output
- broad chmod/chown

rollback_reference:
- 572d0c7 preinstall backup
