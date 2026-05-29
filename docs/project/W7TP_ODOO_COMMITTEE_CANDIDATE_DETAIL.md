# W7TP Odoo 社區管委會候選模組詳細讀取

TIME=2026-05-26T00:42:19
SOURCE_REGISTRY=runtime/reports/W7TP_ODOO_CANONICAL_ADDON_REGISTRY_20260526_003729.json

## 1. 結論

- committee_candidates=8
- 本次只讀，不安裝、不重啟、不寫 DB。

## 2. 候選排名

| rank | score | strength | addon | installable | path_class | recommendation | models | path |
|---:|---:|---|---|---:|---|---|---:|---|
| 1 | 141 | direct_committee_module | wuchang_core | True | unknown | installable_review_first | 72 | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core |
| 2 | 89 | strong_candidate | wuchang_core | True | canonical_candidate | canonical_candidate | 9 | Taiji_Odoo/addons/wuchang_core |
| 3 | 24 | related_candidate | wuchang_community_core | True | unknown | installable_review_first | 0 | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core |
| 4 | 6 | related_candidate | wuchang_property_local_cloud | True | canonical_candidate | canonical_candidate | 15 | Taiji_Odoo/addons/wuchang_property_local_cloud |
| 5 | 6 | related_candidate | wuchang_m1_property | True | unknown | installable_review_first | 1 | _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property |
| 6 | 6 | related_candidate | wuchang_property_core | True | unknown | installable_review_first | 1 | reviews/odoo18_property_candidate/wuchang_property_core |
| 7 | 3 | related_candidate | liaoguo_digital_fantasy_ai | True | unknown | installable_review_first | 1 | /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai |
| 8 | 3 | related_candidate | wuchang_property_manpower_surface | True | canonical_candidate | canonical_candidate | 3 | Taiji_Odoo/addons/wuchang_property_manpower_surface |

## 3. 詳細資料

### 1. wuchang_core

- score=141
- strength=direct_committee_module
- path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core
- installable=True
- depends=base, web, point_of_sale, website, hr, project, maintenance
- bagua_hint=A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A4_merchant_cloud, A5_committee_service, A6_privacy_custody, A7_integration_bridge

#### models
- User fields=0
- community.bulletin fields=31
- community.fund.account fields=15
- community.fund.transaction fields=15
- community.package fields=31
- wuchang.ai.agent fields=7
- wuchang.ai.config fields=13
- wuchang.ai.hallucination.monitor fields=37
- wuchang.ai.learning.log fields=37
- wuchang.ai.logic fields=0
- wuchang.ai.meeting fields=9
- wuchang.ai.memory fields=10
- wuchang.ai.perception.sensor fields=0
- wuchang.ai.prompt fields=4
- wuchang.ai.supervisor.log fields=19
- wuchang.ai.trusted.device fields=37
- wuchang.api.account.separation fields=12
- wuchang.audit.log fields=16
- wuchang.chronos.device fields=10
- wuchang.coin.ledger fields=5
- wuchang.collab.space fields=9
- wuchang.community.coin fields=23
- wuchang.customer.display.music.check fields=38
- wuchang.customer.display.music.config fields=38
- wuchang.customer.display.music.playlist fields=38
- wuchang.delivery.order fields=23
- wuchang.delivery.team fields=23
- wuchang.device.audio fields=16
- wuchang.device.control.execution.log fields=32
- wuchang.device.control.plan fields=32
- wuchang.device.display fields=16
- wuchang.device.node fields=16
- wuchang.digital.signage fields=18
- wuchang.infrastructure.device fields=7
- wuchang.jf.gateway fields=2
- wuchang.legal.doc fields=13
- wuchang.life.covenant fields=10
- wuchang.menu.addon fields=16
- wuchang.menu.attribute fields=16
- wuchang.menu.attribute.value fields=16
- wuchang.menu.item fields=16
- wuchang.menu.item.addon fields=16
- wuchang.menu.item.attribute fields=16
- wuchang.order fields=20
- wuchang.platform.admin fields=0
- wuchang.pos.expense fields=23
- wuchang.privacy.mask fields=0
- wuchang.property.building fields=31
- wuchang.property.committee.member fields=31
- wuchang.property.community fields=31
- wuchang.property.complaint fields=31
- wuchang.property.document fields=11
- wuchang.property.expert.ai fields=3
- wuchang.property.financial.report fields=31
- wuchang.property.unit fields=31
- wuchang.router.certificate fields=22
- wuchang.signage.content fields=18
- wuchang.sister.control fields=7
- wuchang.social.config fields=23
- wuchang.system.medic fields=16
- wuchang.task fields=14
- wuchang.ui.proxy fields=15
- wuchang.voice.conversation fields=21
- wuchang.voice.conversation.stats fields=21
- wuchang.voice.sample fields=19
- wuchang.volunteer.announcement fields=19
- wuchang.volunteer.meeting fields=19
- wuchang.volunteer.signup fields=4
- wuchang.volunteer.task fields=4
- wuchang.voucher.product fields=23
- wuchang.wit fields=0
- 聊國咖啡重新總店 fields=0

#### access
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_wuchang_chronos_device', 'model': 'model_wuchang_chronos_device', 'group': '', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_wuchang_life_covenant', 'model': 'model_wuchang_life_covenant', 'group': '', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

#### views
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'target_models': ['community.fund.account', 'res.partner', 'transparency.log', 'wish.tree.card', 'wish.tree.fruit', 'wuchang.coin.transaction'], 'action_models': ['community.fund.account', 'transparency.log', 'wish.tree.card', 'wish.tree.fruit', 'wuchang.coin.transaction'], 'menu_ids': ['menu_fund_pool', 'menu_transparency_log', 'menu_coin_transaction', 'menu_wish_fruits', 'menu_wish_cards']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml', 'target_models': ['wuchang.router.certificate'], 'action_models': ['wuchang.router.certificate'], 'menu_ids': ['menu_router_certificate']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml', 'target_models': ['wuchang.infrastructure.device'], 'action_models': ['wuchang.infrastructure.device'], 'menu_ids': ['menu_wuchang_infrastructure', 'menu_wuchang_infrastructure_device']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_menus.xml', 'target_models': [], 'action_models': [], 'menu_ids': ['menu_wuchang_root', 'menu_wuchang_chronos', 'menu_wuchang_covenant']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_memory_views.xml', 'target_models': ['wuchang.ai.memory'], 'action_models': ['wuchang.ai.memory'], 'menu_ids': ['menu_wuchang_ai_memory']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml', 'target_models': ['wuchang.sister.control'], 'action_models': ['wuchang.sister.control'], 'menu_ids': ['menu_wuchang_sister_root', 'menu_wuchang_sister_control']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/client_actions.xml', 'target_models': [], 'action_models': [], 'menu_ids': ['menu_community_super_app']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'target_models': ['wuchang.device.control.execution.log', 'wuchang.device.control.plan'], 'action_models': ['wuchang.device.control.execution.log', 'wuchang.device.control.plan'], 'menu_ids': ['menu_device_control_plan']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'target_models': ['account.move', 'pos.order'], 'action_models': ['account.move', 'pos.order'], 'menu_ids': ['menu_wuchang_reports_root', 'menu_pos_sales_report', 'menu_expense_report', 'menu_business_evaluation']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'target_models': ['wuchang.audit.log', 'wuchang.system.medic'], 'action_models': ['wuchang.audit.log', 'wuchang.system.medic'], 'menu_ids': ['menu_wuchang_system_tools', 'menu_wuchang_system_medic', 'menu_wuchang_audit_log']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'target_models': ['wuchang.customer.display.music.check', 'wuchang.customer.display.music.config', 'wuchang.customer.display.music.playlist'], 'action_models': ['wuchang.customer.display.music.check', 'wuchang.customer.display.music.config', 'wuchang.customer.display.music.playlist'], 'menu_ids': ['menu_customer_display_music', 'menu_customer_display_music_playlist', 'menu_customer_display_music_config', 'menu_customer_display_music_check']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'target_models': ['pos.config', 'wuchang.pos.expense'], 'action_models': ['wuchang.pos.expense'], 'menu_ids': ['menu_wuchang_pos_root', 'menu_pos_expense']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'target_models': ['community.bulletin', 'community.package', 'wuchang.property.community', 'wuchang.property.complaint', 'wuchang.property.unit'], 'action_models': ['community.bulletin', 'community.package', 'wuchang.property.community', 'wuchang.property.complaint'], 'menu_ids': ['menu_property_root', 'menu_property_community', 'menu_property_complaint', 'menu_bulletin', 'menu_package']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'target_models': ['wuchang.device.audio', 'wuchang.device.display', 'wuchang.device.node'], 'action_models': ['wuchang.device.audio', 'wuchang.device.display', 'wuchang.device.node'], 'menu_ids': ['menu_wuchang_iot_root', 'menu_wuchang_device_node', 'menu_wuchang_device_display', 'menu_wuchang_device_audio']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml', 'target_models': ['wuchang.ui.proxy'], 'action_models': ['wuchang.ui.proxy'], 'menu_ids': ['menu_ui_proxy']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_agent_views.xml', 'target_models': ['wuchang.ai.agent'], 'action_models': ['wuchang.ai.agent'], 'menu_ids': ['menu_wuchang_ai_agent']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_views.xml', 'target_models': ['wuchang.order'], 'action_models': ['wuchang.order'], 'menu_ids': ['menu_wuchang_order']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_config_views.xml', 'target_models': ['pos.config', 'wuchang.digital.signage'], 'action_models': ['wuchang.digital.signage'], 'menu_ids': []}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_prompt_views.xml', 'target_models': ['wuchang.ai.prompt'], 'action_models': ['wuchang.ai.prompt'], 'menu_ids': ['menu_wuchang_ai_prompt']}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml', 'target_models': ['res.config.settings'], 'action_models': ['res.config.settings'], 'menu_ids': ['menu_wuchang_settings']}

#### keyword hits
- meta:committee
- meta:meeting
- meta:announcement
- meta:committee_service
- bagua:A5_committee_service
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/order_site.py:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/settings.py:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_property_expert.py:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_partner.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/collab_meeting.py:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/meeting_setup.xml:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_website.xml:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/knowledge_templates.xml:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml:announcement

### 2. wuchang_core

- score=89
- strength=strong_candidate
- path=Taiji_Odoo/addons/wuchang_core
- installable=True
- depends=base, point_of_sale, account
- bagua_hint=A1_core_governance, A2_resident_entry, A3_volunteer_delivery, A5_committee_service

#### models
- wuchang.ai.verification fields=85
- wuchang.bank.clearance fields=85
- wuchang.no.delete.mixin fields=85
- wuchang.renyi.volunteer.account fields=85
- wuchang.renyi.volunteer.account.line fields=85
- wuchang.renyi.volunteer.business fields=85
- wuchang.task.force.dispatch fields=85
- wuchang.volunteer.management.meeting fields=85
- wuchang.wish.project fields=85

#### access
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_renyi_volunteer_business_user', 'model': 'model_wuchang_renyi_volunteer_business', 'group': 'base.group_user', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_renyi_volunteer_business_backend', 'model': 'model_wuchang_renyi_volunteer_business', 'group': 'wuchang_core.group_wuchang_volunteer_backend', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_task_force_dispatch_user', 'model': 'model_wuchang_task_force_dispatch', 'group': 'base.group_user', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_task_force_dispatch_backend', 'model': 'model_wuchang_task_force_dispatch', 'group': 'wuchang_core.group_wuchang_volunteer_backend', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_renyi_volunteer_account_user', 'model': 'model_wuchang_renyi_volunteer_account', 'group': 'base.group_user', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_renyi_volunteer_account_backend', 'model': 'model_wuchang_renyi_volunteer_account', 'group': 'wuchang_core.group_wuchang_volunteer_backend', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_renyi_volunteer_account_line_user', 'model': 'model_wuchang_renyi_volunteer_account_line', 'group': 'base.group_user', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_renyi_volunteer_account_line_backend', 'model': 'model_wuchang_renyi_volunteer_account_line', 'group': 'wuchang_core.group_wuchang_volunteer_backend', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_volunteer_management_meeting_user', 'model': 'model_wuchang_volunteer_management_meeting', 'group': 'base.group_user', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': 'Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_volunteer_management_meeting_backend', 'model': 'model_wuchang_volunteer_management_meeting', 'group': 'wuchang_core.group_wuchang_volunteer_backend', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}

#### views
- {'file': 'Taiji_Odoo/addons/wuchang_core/views/wuchang_views.xml', 'target_models': ['wuchang.wish.project'], 'action_models': [], 'menu_ids': []}

#### keyword hits
- meta:committee
- meta:meeting
- meta:committee_service
- bagua:A5_committee_service
- Taiji_Odoo/addons/wuchang_core/models/wuchang_matrix.py:meeting
- Taiji_Odoo/addons/wuchang_core/security/wuchang_security.xml:會議
- Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv:meeting

### 3. wuchang_community_core

- score=24
- strength=related_candidate
- path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core
- installable=True
- depends=base, mail
- bagua_hint=A1_core_governance

#### models
- none

#### access
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/ir.model.access.csv', 'id': 'access_res_partner_wuchang_resident', 'model': 'base.model_res_partner', 'group': 'group_wuchang_resident', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/ir.model.access.csv', 'id': 'access_res_partner_wuchang_committee', 'model': 'base.model_res_partner', 'group': 'group_wuchang_committee', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

#### views
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/views/community_household_views.xml', 'target_models': ['res.partner'], 'action_models': [], 'menu_ids': []}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/views/ai_avatar_dashboard_views.xml', 'target_models': [], 'action_models': [], 'menu_ids': ['menu_wuchang_community_root', 'menu_wuchang_ai_avatar', 'menu_wuchang_ai_chat']}

#### keyword hits
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/__manifest__.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/community_household.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/models/mail_bot_liberation.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/community_roles_security.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/data/wuchang_ai_avatar_data.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/data/wuchang_company_data.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/views/community_household_views.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_community_core/security/ir.model.access.csv:committee

### 4. wuchang_property_local_cloud

- score=6
- strength=related_candidate
- path=Taiji_Odoo/addons/wuchang_property_local_cloud
- installable=True
- depends=base
- bagua_hint=A1_core_governance, A2_resident_entry, A4_merchant_cloud

#### models
- display_name fields=48
- memo fields=48
- name fields=15
- one_time_code_hash fields=48
- wuchang.field.verification.device fields=48
- wuchang.franchise.relationship fields=15
- wuchang.google.nonprofit.resource fields=13
- wuchang.group.customer fields=48
- wuchang.happiness.ledger fields=48
- wuchang.local.cloud.appliance fields=48
- wuchang.member.identity fields=48
- wuchang.member.sovereign.device fields=48
- wuchang.permission.proof fields=48
- wuchang.ticket.opening fields=13
- wuchang.trusted.governance.node fields=48

#### access
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_group_customer', 'model': 'model_wuchang_group_customer', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_member_identity', 'model': 'model_wuchang_member_identity', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_member_sov_device', 'model': 'model_wuchang_member_sovereign_device', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_field_device', 'model': 'model_wuchang_field_verification_device', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_governance_node', 'model': 'model_wuchang_trusted_governance_node', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_local_cloud', 'model': 'model_wuchang_local_cloud_appliance', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_permission_proof', 'model': 'model_wuchang_permission_proof', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_happiness_ledger', 'model': 'model_wuchang_happiness_ledger', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_ticket_opening', 'model': 'model_wuchang_ticket_opening', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_franchise_relationship', 'model': 'model_wuchang_franchise_relationship', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/security/ir.model.access.csv', 'id': 'access_wuchang_google_nonprofit_resource', 'model': 'model_wuchang_google_nonprofit_resource', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

#### views
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_ticket_opening_views.xml', 'target_models': ['wuchang.ticket.opening'], 'action_models': ['wuchang.ticket.opening'], 'menu_ids': ['menu_wuchang_ticket_root', 'menu_wuchang_ticket_opening_all', 'menu_wuchang_ticket_opening_group_member', 'menu_wuchang_ticket_opening_merchant_self']}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_pos_policy_views.xml', 'target_models': ['wuchang.field.verification.device', 'wuchang.group.customer'], 'action_models': ['wuchang.group.customer'], 'menu_ids': ['menu_wuchang_pos_policy_merchants']}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_franchise_relationship_views.xml', 'target_models': ['wuchang.franchise.relationship'], 'action_models': ['wuchang.franchise.relationship'], 'menu_ids': ['menu_wuchang_franchise_relationship']}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_company_association_registration_views.xml', 'target_models': ['res.company'], 'action_models': [], 'menu_ids': []}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_google_nonprofit_resource_views.xml', 'target_models': ['wuchang.google.nonprofit.resource'], 'action_models': ['wuchang.google.nonprofit.resource'], 'menu_ids': ['menu_wuchang_google_nonprofit_resource']}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_property_views.xml', 'target_models': ['wuchang.field.verification.device', 'wuchang.group.customer', 'wuchang.happiness.ledger', 'wuchang.local.cloud.appliance', 'wuchang.member.identity', 'wuchang.member.sovereign.device', 'wuchang.permission.proof', 'wuchang.trusted.governance.node'], 'action_models': ['wuchang.field.verification.device', 'wuchang.group.customer', 'wuchang.happiness.ledger', 'wuchang.local.cloud.appliance', 'wuchang.member.identity', 'wuchang.member.sovereign.device', 'wuchang.permission.proof', 'wuchang.trusted.governance.node'], 'menu_ids': ['menu_wuchang_property_root', 'menu_wuchang_group_customer', 'menu_wuchang_member_identity', 'menu_wuchang_member_sov_device', 'menu_wuchang_field_device', 'menu_wuchang_governance_node', 'menu_wuchang_local_cloud', 'menu_wuchang_permission_proof', 'menu_wuchang_happiness_ledger']}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_ticket_quota_buckets_views.xml', 'target_models': ['wuchang.group.customer', 'wuchang.ticket.opening'], 'action_models': ['wuchang.group.customer'], 'menu_ids': ['menu_wuchang_ticket_quota_totals']}
- {'file': 'Taiji_Odoo/addons/wuchang_property_local_cloud/views/wuchang_company_google_workspace_views.xml', 'target_models': ['res.company'], 'action_models': [], 'menu_ids': []}

#### keyword hits
- Taiji_Odoo/addons/wuchang_property_local_cloud/__manifest__.py:管委會
- Taiji_Odoo/addons/wuchang_property_local_cloud/models/wuchang_property.py:committee

### 5. wuchang_m1_property

- score=6
- strength=related_candidate
- path=_imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property
- installable=True
- depends=wuchang_m3_volunteer, project, maintenance, mail
- bagua_hint=unclassified

#### models
- property.request fields=6

#### access
- {'file': '_imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/security/ir.model.access.csv', 'id': 'access_property_request_user', 'model': 'model_property_request', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': '_imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/security/ir.model.access.csv', 'id': 'access_property_request_manager', 'model': 'model_property_request', 'group': 'base.group_system', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

#### views
- {'file': '_imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/views/property_request_views.xml', 'target_models': ['property.request'], 'action_models': ['property.request'], 'menu_ids': ['menu_property_root', 'menu_property_requests']}

#### keyword hits
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/models/property_request.py:報修
- _imports/wuchang-ai-main/wuchang-ai-main/wuchang_m1_property/views/property_request_views.xml:報修

### 6. wuchang_property_core

- score=6
- strength=related_candidate
- path=reviews/odoo18_property_candidate/wuchang_property_core
- installable=True
- depends=base, mail, project, maintenance
- bagua_hint=A1_core_governance

#### models
- wuchang.property.request fields=10

#### access
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv', 'id': 'access_property_request_resident', 'model': 'model_wuchang_property_request', 'group': 'wuchang_property_core.group_property_resident', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv', 'id': 'access_property_request_frontdesk', 'model': 'model_wuchang_property_request', 'group': 'wuchang_property_core.group_property_frontdesk', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv', 'id': 'access_property_request_staff', 'model': 'model_wuchang_property_request', 'group': 'wuchang_property_core.group_property_staff', 'read': '1', 'write': '1', 'create': '1', 'unlink': '0'}
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv', 'id': 'access_property_request_technician', 'model': 'model_wuchang_property_request', 'group': 'wuchang_property_core.group_property_technician', 'read': '1', 'write': '1', 'create': '0', 'unlink': '0'}
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv', 'id': 'access_property_request_manager', 'model': 'model_wuchang_property_request', 'group': 'wuchang_property_core.group_property_manager', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/security/ir.model.access.csv', 'id': 'access_property_request_auditor', 'model': 'model_wuchang_property_request', 'group': 'wuchang_property_core.group_property_auditor', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}

#### views
- {'file': 'reviews/odoo18_property_candidate/wuchang_property_core/views/property_request_views.xml', 'target_models': ['wuchang.property.request'], 'action_models': ['wuchang.property.request'], 'menu_ids': ['menu_wuchang_property_root', 'menu_wuchang_property_requests']}

#### keyword hits
- reviews/odoo18_property_candidate/wuchang_property_core/models/property_request.py:報修
- reviews/odoo18_property_candidate/wuchang_property_core/views/property_request_views.xml:報修

### 7. liaoguo_digital_fantasy_ai

- score=3
- strength=related_candidate
- path=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai
- installable=True
- depends=base, mail, crm
- bagua_hint=unclassified

#### models
- liaoguo.ai.optimizer fields=11

#### access
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/security/ir.model.access.csv', 'id': 'access_liaoguo_ai_optimizer_user', 'model': 'model_liaoguo_ai_optimizer', 'group': 'base.group_user', 'read': '1', 'write': '0', 'create': '0', 'unlink': '0'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/security/ir.model.access.csv', 'id': 'access_liaoguo_ai_optimizer_manager', 'model': 'model_liaoguo_ai_optimizer', 'group': 'base.group_system', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

#### views
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/views/ai_computer_metrics_views.xml', 'target_models': ['liaoguo.ai.optimizer'], 'action_models': ['liaoguo.ai.optimizer'], 'menu_ids': ['menu_liaoguo_ai_root', 'menu_liaoguo_ai_dashboard']}

#### keyword hits
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/liaoguo_digital_fantasy_ai/OPTIMIZATION_MANIFESTO.md:管委會

### 8. wuchang_property_manpower_surface

- score=3
- strength=related_candidate
- path=Taiji_Odoo/addons/wuchang_property_manpower_surface
- installable=True
- depends=base
- bagua_hint=A2_resident_entry

#### models
- name fields=28
- wuchang.property.manpower.surface.line fields=28
- wuchang.property.manpower.surface.plan fields=28

#### access
- {'file': 'Taiji_Odoo/addons/wuchang_property_manpower_surface/security/ir.model.access.csv', 'id': 'access_wuchang_property_manpower_surface_plan', 'model': 'model_wuchang_property_manpower_surface_plan', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': 'Taiji_Odoo/addons/wuchang_property_manpower_surface/security/ir.model.access.csv', 'id': 'access_wuchang_property_manpower_surface_line', 'model': 'model_wuchang_property_manpower_surface_line', 'group': 'base.group_user', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

#### views
- {'file': 'Taiji_Odoo/addons/wuchang_property_manpower_surface/views/wuchang_property_manpower_surface_views.xml', 'target_models': ['wuchang.property.manpower.surface.plan'], 'action_models': ['wuchang.property.manpower.surface.plan'], 'menu_ids': ['menu_wuchang_property_manpower_surface_root', 'menu_wuchang_property_manpower_surface_plan']}

#### keyword hits
- Taiji_Odoo/addons/wuchang_property_manpower_surface/models/wuchang_property_manpower_surface.py:管委會

## 4. 裁決規則

- direct_committee_module 優先於 strong_candidate。
- canonical_candidate 優先於 runtime/staging/legacy。
- installable=True 仍需人工確認公司、個資、帳務、權限邊界。
- 若 8 個候選都只是關聯模組，才建立新的 `xiaoj_committee_service`。

## 5. Hardwall

- READ_ONLY=true
- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false

JSON=runtime/reports/W7TP_ODOO_COMMITTEE_CANDIDATE_DETAIL_20260526_004219.json
REPORT=runtime/reports/W7TP_ODOO_COMMITTEE_CANDIDATE_DETAIL_20260526_004219.md
