# W7TP Odoo 社區管委會模組讀取報告

TIME=2026-05-26T00:40:16
REGISTRY=runtime/reports/W7TP_ODOO_CANONICAL_ADDON_REGISTRY_20260526_003729.json

## 1. 結論

- registry_records=24
- committee_candidates=8
- 本次只讀取檔案層，不安裝、不重啟、不寫 DB。

## 2. 候選模組

| score | addon | recommendation | installable | bagua | path |
|---:|---|---|---:|---|---|
| 52 | wuchang_core | installable_review_first | True | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A4_merchant_cloud, A5_committee_service, A6_privacy_custody, A7_integration_bridge | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core |
| 33 | wuchang_core | canonical_candidate | True | A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A5_committee_service | Taiji_Odoo/addons/wuchang_core |
| 8 | wuchang_community_core | installable_review_first | True | A1_core_governance | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core |
| 2 | wuchang_property_local_cloud | canonical_candidate | True | A1_core_governance, A2_resident_entry, A4_merchant_cloud | Taiji_Odoo/addons/wuchang_property_local_cloud |
| 2 | wuchang_m1_property | installable_review_first | True | unclassified | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property |
| 2 | wuchang_property_core | installable_review_first | True | A1_core_governance | reviews/odoo18_property_candidate/wuchang_property_core |
| 1 | liaoguo_digital_fantasy_ai | installable_review_first | True | unclassified | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai |
| 1 | wuchang_property_manpower_surface | canonical_candidate | True | A2_resident_entry | Taiji_Odoo/addons/wuchang_property_manpower_surface |

## 3. 候選模組詳細讀取

### wuchang_core

- score=52
- path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core
- installable=True
- depends=base, web, point_of_sale, website, hr, project, maintenance
- models=User, community.bulletin, community.fund.account, community.fund.transaction, community.package, wuchang.ai.agent, wuchang.ai.config, wuchang.ai.hallucination.monitor, wuchang.ai.learning.log, wuchang.ai.logic, wuchang.ai.meeting, wuchang.ai.memory, wuchang.ai.perception.sensor, wuchang.ai.prompt, wuchang.ai.supervisor.log, wuchang.ai.trusted.device, wuchang.api.account.separation, wuchang.audit.log, wuchang.chronos.device, wuchang.coin.ledger, wuchang.collab.space, wuchang.community.coin, wuchang.customer.display.music.check, wuchang.customer.display.music.config, wuchang.customer.display.music.playlist, wuchang.delivery.order, wuchang.delivery.team, wuchang.device.audio, wuchang.device.control.execution.log, wuchang.device.control.plan, wuchang.device.display, wuchang.device.node, wuchang.digital.signage, wuchang.infrastructure.device, wuchang.jf.gateway, wuchang.legal.doc, wuchang.life.covenant, wuchang.menu.addon, wuchang.menu.attribute, wuchang.menu.attribute.value, wuchang.menu.item, wuchang.menu.item.addon, wuchang.menu.item.attribute, wuchang.order, wuchang.platform.admin, wuchang.pos.expense, wuchang.privacy.mask, wuchang.property.building, wuchang.property.committee.member, wuchang.property.community, wuchang.property.complaint, wuchang.property.document, wuchang.property.expert.ai, wuchang.property.financial.report, wuchang.property.unit, wuchang.router.certificate, wuchang.signage.content, wuchang.sister.control, wuchang.social.config, wuchang.system.medic, wuchang.task, wuchang.ui.proxy, wuchang.voice.conversation, wuchang.voice.conversation.stats, wuchang.voice.sample, wuchang.volunteer.announcement, wuchang.volunteer.meeting, wuchang.volunteer.signup, wuchang.volunteer.task, wuchang.voucher.product, wuchang.wit, 聊國咖啡重新總店
- hits=committee; meeting; announcement; A5_committee_service; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/order_site.py:announcement; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/settings.py:announcement; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py:meeting; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_property_expert.py:管委會; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_partner.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/collab_meeting.py:meeting; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:committee

#### files
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/__manifest__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/brother_channel.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/customer_display_music_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/device_app_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/device_enrollment_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/device_query_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/handshake_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/line_webhook_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/menu_import.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/notification_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/order_site.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/router_certificate_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/router_relay.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/sister_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/ticket_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/ui_proxy_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/voice_interface_controller.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/ai_cron.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/ai_memory_init.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/ai_prompt_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/breakfast_pos_menu.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/constitution_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/cron.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/device_control_plan_defaults.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/enable_vertex_ai.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/google_credentials.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/lang_setup.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/meeting_setup.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/menu_setup.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/pos_expense_sequence.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/pos_setup.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/property_structure_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/router_certificate_defaults.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/signup_setup.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/sustainability_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/sync_balance_action.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/system_params.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/taiwan_cafe_music_playlist.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/ui_proxy_cron.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/user_setup.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/vm_agent_config.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/wuchang_association_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/Untitled-2.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_agent_new.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_event_listener.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_guard.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_index_mixin.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_jules_tools.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_logic.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_memory.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_perception_sensor.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_prompt.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_property_expert.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/api_account_separation.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/coin_ledger.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/collab_meeting.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/compliance_fix.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/core_logic.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/customer_display_music.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control_plan.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/finance.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/governance.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/infrastructure.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/jf_gateway.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/knowledge_kb.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/mail_bot.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/order.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/pos_config_ext.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/pos_expense.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_partner.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_users.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/router_certificate.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/settings.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/sister_control.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/system_tools.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/task.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ui_proxy.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/voice_conversation.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/wuchang_task_force.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/scripts/knowledge_sync_agent.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/security/ir.model.access.csv
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/security/security.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/static/manuals/User_Manual_Admin.md
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/static/manuals/User_Manual_Committee.md
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/static/src/xml/delivery_interfaces.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/tests/benchmark_spatiotemporal.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/tests/test_listener_sim.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/tests/trigger_scan.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_agent_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_memory_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_prompt_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ambassador.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/brother_console.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/client_actions.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/delivery_page.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_web_app_templates.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/homepage_template.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/knowledge_templates.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/mobile_voice_app.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/needs_templates.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_website.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_config_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_simulator.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/service_dashboard.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ticket_page.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/voice_chat.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/voice_reference.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/webauthn_login.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_menus.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_task_force_views.xml

### wuchang_core

- score=33
- path=Taiji_Odoo/addons/wuchang_core
- installable=True
- depends=base, point_of_sale, account
- models=wuchang.ai.verification, wuchang.bank.clearance, wuchang.no.delete.mixin, wuchang.renyi.volunteer.account, wuchang.renyi.volunteer.account.line, wuchang.renyi.volunteer.business, wuchang.task.force.dispatch, wuchang.volunteer.management.meeting, wuchang.wish.project
- hits=committee; meeting; A5_committee_service; Taiji_Odoo/addons/wuchang_core/models/wuchang_matrix.py:meeting; Taiji_Odoo/addons/wuchang_core/security/wuchang_security.xml:會議; Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv:meeting

#### files
- Taiji_Odoo/addons/wuchang_core/__init__.py
- Taiji_Odoo/addons/wuchang_core/__manifest__.py
- Taiji_Odoo/addons/wuchang_core/models/__init__.py
- Taiji_Odoo/addons/wuchang_core/models/wuchang_matrix.py
- Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv
- Taiji_Odoo/addons/wuchang_core/security/wuchang_security.xml
- Taiji_Odoo/addons/wuchang_core/views/wuchang_views.xml

### wuchang_community_core

- score=8
- path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core
- installable=True
- depends=base, mail
- models=none
- hits=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/__manifest__.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/community_household.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/mail_bot_liberation.py:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/community_roles_security.xml:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/data/wuchang_ai_avatar_data.xml:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/data/wuchang_company_data.xml:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/views/community_household_views.xml:committee; /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/ir.model.access.csv:committee

#### files
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/__manifest__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/data/wuchang_ai_avatar_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/data/wuchang_company_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/community_household.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/mail_bot_liberation.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/community_roles_security.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/ir.model.access.csv
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/views/ai_avatar_dashboard_views.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/views/community_household_views.xml

### wuchang_property_local_cloud

- score=2
- path=Taiji_Odoo/addons/wuchang_property_local_cloud
- installable=True
- depends=base
- models=display_name, memo, name, one_time_code_hash, wuchang.field.verification.device, wuchang.franchise.relationship, wuchang.google.nonprofit.resource, wuchang.group.customer, wuchang.happiness.ledger, wuchang.local.cloud.appliance, wuchang.member.identity, wuchang.member.sovereign.device, wuchang.permission.proof, wuchang.ticket.opening, wuchang.trusted.governance.node
- hits=Taiji_Odoo/addons/wuchang_property_local_cloud/__manifest__.py:管委會; Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_property.py:committee

#### files
- Taiji_Odoo/addons/wuchang_property_local_cloud/__init__.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/__manifest__.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/__init__.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_company_association_registration.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_company_google_workspace.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_franchise_relationship.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_google_nonprofit_resource.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_pos_policy.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_property.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_ticket_opening.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_ticket_quota_buckets.py
- Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_company_association_registration_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_company_google_workspace_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_franchise_relationship_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_google_nonprofit_resource_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_pos_policy_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_property_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_ticket_opening_views.xml
- Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_ticket_quota_buckets_views.xml

### wuchang_m1_property

- score=2
- path=_imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property
- installable=True
- depends=wuchang_m3_volunteer, project, maintenance, mail
- models=property.request
- hits=_imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/models/property_request.py:報修; _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/views/property_request_views.xml:報修

#### files
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/__init__.py
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/__manifest__.py
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/models/__init__.py
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/models/property_request.py
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/security/ir.model.access.csv
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/views/property_request_views.xml

### wuchang_property_core

- score=2
- path=reviews/odoo18_property_candidate/wuchang_property_core
- installable=True
- depends=base, mail, project, maintenance
- models=wuchang.property.request
- hits=reviews/odoo18_property_candidate/wuchang_property_core/models/property_request.py:報修; reviews/odoo18_property_candidate/wuchang_property_core/views/property_request_views.xml:報修

#### files
- reviews/odoo18_property_candidate/wuchang_property_core/__init__.py
- reviews/odoo18_property_candidate/wuchang_property_core/__manifest__.py
- reviews/odoo18_property_candidate/wuchang_property_core/models/__init__.py
- reviews/odoo18_property_candidate/wuchang_property_core/models/property_request.py
- reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv
- reviews/odoo18_property_candidate/wuchang_property_core/security/property_record_rules.xml
- reviews/odoo18_property_candidate/wuchang_property_core/security/property_security.xml
- reviews/odoo18_property_candidate/wuchang_property_core/views/property_request_views.xml

### liaoguo_digital_fantasy_ai

- score=1
- path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai
- installable=True
- depends=base, mail, crm
- models=liaoguo.ai.optimizer
- hits=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/OPTIMIZATION_MANIFESTO.md:管委會

#### files
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/OPTIMIZATION_MANIFESTO.md
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/__manifest__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/data/ai_optimization_data.xml
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/models/__init__.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/models/liaoguo_ai_optimizer.py
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/security/ir.model.access.csv
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/views/ai_computer_metrics_views.xml

### wuchang_property_manpower_surface

- score=1
- path=Taiji_Odoo/addons/wuchang_property_manpower_surface
- installable=True
- depends=base
- models=name, wuchang.property.manpower.surface.line, wuchang.property.manpower.surface.plan
- hits=Taiji_Odoo/addons/wuchang_property_manpower_surface/models/wuchang_property_manpower_surface.py:管委會

#### files
- Taiji_Odoo/addons/wuchang_property_manpower_surface/__init__.py
- Taiji_Odoo/addons/wuchang_property_manpower_surface/__manifest__.py
- Taiji_Odoo/addons/wuchang_property_manpower_surface/models/__init__.py
- Taiji_Odoo/addons/wuchang_property_manpower_surface/models/wuchang_property_manpower_surface.py
- Taiji_Odoo/addons/wuchang_property_manpower_surface/security/ir.model.access.csv
- Taiji_Odoo/addons/wuchang_property_manpower_surface/views/wuchang_property_manpower_surface_views.xml

## 4. 社區管委會模組應有職責

- 管委會公告 / 決議草稿
- 會議紀錄草稿
- 報修案件統計
- 公設巡檢
- 財務摘要，不含會員 raw PII
- 住戶意見彙整，只處理去識別化摘要
- 颱風 / 緊急事件通報
- Open WebUI 管委會審核卡
- Odoo 模型預留：xiaoj.committee.notice / xiaoj.committee.meeting / xiaoj.committee.repair.summary / xiaoj.committee.inspection

## 5. Hardwall

- READ_ONLY=true
- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- COMMITTEE_RAW_PII_ACCESS=false
- AI_FINAL_DECISION=false

