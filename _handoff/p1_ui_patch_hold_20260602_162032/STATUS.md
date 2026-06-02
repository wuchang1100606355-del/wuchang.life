# P1 UI Patch Hold

status: generated_not_integrated
created_at: 20260602_162032
source_material: _handoff/gemini_ui_materials_20260602_155100.tar.gz
runtime_target: Odoo 18
base_guard: MEMBER_REGISTRATION_FINAL_V2_PASS_20260602

files:
- portal.py
- portal_templates.xml
- backend_menu.xml
- portal.css

next:
- review
- map into Taiji_Odoo/addons/wuchang_member_registration
- update manifest
- run UI_GRADE_GATE_V1
- no deploy before red-team pass
