# M004B Odoo Risk Module Index

Purpose:
Record Odoo implementation files excluded from M004A Safe Core due to credential/OAuth/session/private-key surface.

Excluded groups:
- Taiji_Odoo/addons/wuchang_core/data/
- Taiji_Odoo/addons/pm3_runtime_sync.bak./
- *.backup
- Taiji_Odoo/addons/wuchang_core/controllers/main.py
- Taiji_Odoo/addons/wuchang_core/controllers/device_enrollment_controller.py
- Taiji_Odoo/addons/wuchang_core/models/router_certificate.py
- Taiji_Odoo/addons/wuchang_core/views/router_certificate_views.xml
- Taiji_Odoo/addons/wuchang_core/views/settings_views.xml
- Taiji_Odoo/addons/pm3_runtime_sync/controllers/google_auth.py
- Taiji_Odoo/addons/pm3_runtime_sync/controllers/line_auth.py
- Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py
- Taiji_Odoo/addons/wuchang_line_login/controllers/main.py

Reason:
- Contains OAuth token exchange logic, credential parameter names, password fields, session identifiers, router private key fields, or backup/noisy files.
- Most entries appear to be code variables or secure password fields rather than actual secrets, but they require separate review before Git inclusion.

Policy:
- Do not commit raw risk files until reviewed.
- Prefer template/redacted versions.
- Keep actual secrets in environment variables, Odoo ir.config_parameter, or external secret store.
- No service account JSON, raw token, private key, cookie, or DB dump in Git.
