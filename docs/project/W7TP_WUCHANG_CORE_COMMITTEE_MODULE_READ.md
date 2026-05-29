# W7TP wuchang_core 社區管委會模組讀取

TIME=2026-05-26T00:43:41
MODULE_PATH=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core

## 1. Manifest

- name=Wuchang AI Task Force (Unified)
- version=17.0.2.0.0
- installable=True
- application=True
- category=Productivity
- depends=base, web, point_of_sale, website, hr, project, maintenance

## 2. 結構統計

- py_files=68
- xml_files=65
- csv_files=1
- models=75
- fields=614
- access_rows=2
- views=74
- menus=51
- actions=39
- committee_keyword_hits=55

## 3. Models

- 聊國咖啡重新總店 (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py)
- wuchang.volunteer.task (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/Untitled-2.py)
- wuchang.volunteer.signup (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/Untitled-2.py)
- wuchang.ai.agent (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_agent_new.py)
- wuchang.ai.trusted.device (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_guard.py)
- wuchang.ai.hallucination.monitor (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_guard.py)
- wuchang.ai.learning.log (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_guard.py)
- wuchang.ai.logic (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_logic.py)
- wuchang.ai.memory (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_memory.py)
- wuchang.ai.perception.sensor (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_perception_sensor.py)
- User (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_perception_sensor.py)
- wuchang.ai.prompt (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_prompt.py)
- wuchang.property.expert.ai (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_property_expert.py)
- wuchang.api.account.separation (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/api_account_separation.py)
- wuchang.coin.ledger (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/coin_ledger.py)
- wuchang.collab.space (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/collab_meeting.py)
- wuchang.ai.meeting (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/collab_meeting.py)
- wuchang.privacy.mask (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/core_logic.py)
- wuchang.wit (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/core_logic.py)
- wuchang.platform.admin (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/core_logic.py)
- wuchang.customer.display.music.playlist (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/customer_display_music.py)
- wuchang.customer.display.music.config (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/customer_display_music.py)
- wuchang.customer.display.music.check (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/customer_display_music.py)
- wuchang.delivery.team (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py)
- wuchang.delivery.order (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py)
- wuchang.voucher.product (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py)
- wuchang.community.coin (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py)
- wuchang.pos.expense (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py)
- wuchang.social.config (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/delivery.py)
- wuchang.device.node (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control.py)
- wuchang.device.display (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control.py)
- wuchang.device.audio (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control.py)
- wuchang.device.control.plan (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control_plan.py)
- wuchang.device.control.execution.log (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/device_control_plan.py)
- community.fund.account (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/finance.py)
- community.fund.transaction (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/finance.py)
- wuchang.legal.doc (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/governance.py)
- wuchang.ai.config (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/governance.py)
- wuchang.infrastructure.device (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/infrastructure.py)
- wuchang.jf.gateway (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/jf_gateway.py)
- wuchang.menu.attribute (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py)
- wuchang.menu.attribute.value (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py)
- wuchang.menu.addon (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py)
- wuchang.menu.item (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py)
- wuchang.menu.item.addon (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py)
- wuchang.menu.item.attribute (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/menu.py)
- wuchang.order (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/order.py)
- wuchang.digital.signage (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/pos_config_ext.py)
- wuchang.signage.content (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/pos_config_ext.py)
- wuchang.pos.expense (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/pos_expense.py)
- wuchang.property.document (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py)
- wuchang.property.community (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- wuchang.property.building (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- wuchang.property.unit (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- wuchang.property.committee.member (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- wuchang.property.complaint (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- wuchang.property.financial.report (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- community.bulletin (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- community.package (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py)
- wuchang.router.certificate (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/router_certificate.py)
- wuchang.sister.control (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/sister_control.py)
- wuchang.system.medic (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/system_tools.py)
- wuchang.audit.log (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/system_tools.py)
- wuchang.task (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/task.py)
- wuchang.ui.proxy (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ui_proxy.py)
- wuchang.voice.conversation (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/voice_conversation.py)
- wuchang.voice.conversation.stats (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/voice_conversation.py)
- wuchang.volunteer.task (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py)
- wuchang.volunteer.signup (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py)
- wuchang.voice.sample (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py)
- wuchang.volunteer.meeting (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py)
- wuchang.volunteer.announcement (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py)
- wuchang.ai.supervisor.log (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py)
- wuchang.chronos.device (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/wuchang_task_force.py)
- wuchang.life.covenant (/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/wuchang_task_force.py)

## 4. Access

- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_wuchang_chronos_device', 'model': 'model_wuchang_chronos_device', 'group': '', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/security/ir.model.access.csv', 'id': 'access_wuchang_life_covenant', 'model': 'model_wuchang_life_covenant', 'group': '', 'read': '1', 'write': '1', 'create': '1', 'unlink': '1'}

## 5. Views / Actions / Menus

### Views
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_agent_views.xml', 'model': 'wuchang.ai.agent'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_agent_views.xml', 'model': 'wuchang.ai.agent'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_memory_views.xml', 'model': 'wuchang.ai.memory'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_memory_views.xml', 'model': 'wuchang.ai.memory'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_prompt_views.xml', 'model': 'wuchang.ai.prompt'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_prompt_views.xml', 'model': 'wuchang.ai.prompt'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'model': 'wuchang.customer.display.music.playlist'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'model': 'wuchang.customer.display.music.playlist'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'model': 'wuchang.customer.display.music.config'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'model': 'wuchang.customer.display.music.config'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'model': 'wuchang.customer.display.music.check'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'model': 'wuchang.customer.display.music.check'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'model': 'wuchang.device.control.plan'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'model': 'wuchang.device.control.plan'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'model': 'wuchang.device.control.plan'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'model': 'wuchang.device.control.execution.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'model': 'wuchang.device.node'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'model': 'wuchang.device.node'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'model': 'wuchang.device.display'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'model': 'wuchang.device.audio'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'community.fund.account'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'community.fund.account'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'transparency.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'wuchang.coin.transaction'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'wish.tree.fruit'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'wish.tree.card'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'model': 'res.partner'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml', 'model': 'wuchang.infrastructure.device'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml', 'model': 'wuchang.infrastructure.device'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_views.xml', 'model': 'wuchang.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_views.xml', 'model': 'wuchang.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_config_views.xml', 'model': 'pos.config'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_config_views.xml', 'model': 'wuchang.digital.signage'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_config_views.xml', 'model': 'wuchang.digital.signage'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'model': 'wuchang.pos.expense'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'model': 'wuchang.pos.expense'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'model': 'wuchang.pos.expense'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'model': 'wuchang.pos.expense'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'model': 'pos.config'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml', 'model': 'wuchang.property.document'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml', 'model': 'wuchang.property.document'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml', 'model': 'wuchang.property.document'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'wuchang.property.community'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'wuchang.property.community'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'wuchang.property.unit'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'wuchang.property.complaint'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'community.bulletin'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'community.bulletin'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'community.package'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'model': 'community.package'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'model': 'pos.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'model': 'pos.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'model': 'account.move'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'model': 'account.move'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml', 'model': 'wuchang.router.certificate'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml', 'model': 'wuchang.router.certificate'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml', 'model': 'wuchang.router.certificate'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/service_dashboard.xml', 'model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/service_dashboard.xml', 'model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml', 'model': 'res.config.settings'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml', 'model': 'wuchang.sister.control'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml', 'model': 'wuchang.sister.control'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'model': 'wuchang.system.medic'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'model': 'wuchang.system.medic'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'model': 'wuchang.audit.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'model': 'wuchang.audit.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml', 'model': 'wuchang.ui.proxy'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml', 'model': 'wuchang.ui.proxy'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml', 'model': 'wuchang.ui.proxy'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_task_force_views.xml', 'model': 'wuchang.chronos.device'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_task_force_views.xml', 'model': 'wuchang.chronos.device'}

### Actions
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_agent_views.xml', 'res_model': 'wuchang.ai.agent'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_memory_views.xml', 'res_model': 'wuchang.ai.memory'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_prompt_views.xml', 'res_model': 'wuchang.ai.prompt'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'res_model': 'wuchang.customer.display.music.playlist'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'res_model': 'wuchang.customer.display.music.config'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'res_model': 'wuchang.customer.display.music.check'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'res_model': 'wuchang.device.control.plan'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'res_model': 'wuchang.device.control.execution.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'res_model': 'wuchang.device.node'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'res_model': 'wuchang.device.display'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'res_model': 'wuchang.device.audio'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'res_model': 'community.fund.account'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'res_model': 'transparency.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'res_model': 'wuchang.coin.transaction'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'res_model': 'wish.tree.fruit'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'res_model': 'wish.tree.card'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml', 'res_model': 'wuchang.infrastructure.device'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_views.xml', 'res_model': 'wuchang.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_config_views.xml', 'res_model': 'wuchang.digital.signage'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'res_model': 'wuchang.pos.expense'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml', 'res_model': 'wuchang.property.document'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml', 'res_model': 'wuchang.property.document'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'res_model': 'wuchang.property.community'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'res_model': 'wuchang.property.complaint'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'res_model': 'community.bulletin'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'res_model': 'community.package'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'res_model': 'pos.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'res_model': 'account.move'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'res_model': 'pos.order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml', 'res_model': 'wuchang.router.certificate'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/service_dashboard.xml', 'res_model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml', 'res_model': 'res.config.settings'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml', 'res_model': 'wuchang.sister.control'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'res_model': 'wuchang.system.medic'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'res_model': 'wuchang.audit.log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'res_model': 'wuchang.task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml', 'res_model': 'wuchang.ui.proxy'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_task_force_views.xml', 'res_model': 'wuchang.chronos.device'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_task_force_views.xml', 'res_model': 'wuchang.life.covenant'}

### Menus
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_agent_views.xml', 'menu_id': 'menu_wuchang_ai_agent'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_memory_views.xml', 'menu_id': 'menu_wuchang_ai_memory'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ai_prompt_views.xml', 'menu_id': 'menu_wuchang_ai_prompt'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/client_actions.xml', 'menu_id': 'menu_community_super_app'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'menu_id': 'menu_customer_display_music'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'menu_id': 'menu_customer_display_music_playlist'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'menu_id': 'menu_customer_display_music_config'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/customer_display_music_views.xml', 'menu_id': 'menu_customer_display_music_check'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_plan_views.xml', 'menu_id': 'menu_device_control_plan'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'menu_id': 'menu_wuchang_iot_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'menu_id': 'menu_wuchang_device_node'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'menu_id': 'menu_wuchang_device_display'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_control_views.xml', 'menu_id': 'menu_wuchang_device_audio'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'menu_id': 'menu_fund_pool'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'menu_id': 'menu_transparency_log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'menu_id': 'menu_coin_transaction'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'menu_id': 'menu_wish_fruits'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/finance_views.xml', 'menu_id': 'menu_wish_cards'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml', 'menu_id': 'menu_wuchang_infrastructure'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/infrastructure_views.xml', 'menu_id': 'menu_wuchang_infrastructure_device'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_views.xml', 'menu_id': 'menu_wuchang_order'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'menu_id': 'menu_wuchang_pos_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/pos_expense_views.xml', 'menu_id': 'menu_pos_expense'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'menu_id': 'menu_property_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'menu_id': 'menu_property_community'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'menu_id': 'menu_property_complaint'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'menu_id': 'menu_bulletin'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml', 'menu_id': 'menu_package'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'menu_id': 'menu_wuchang_reports_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'menu_id': 'menu_pos_sales_report'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'menu_id': 'menu_expense_report'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/report_views.xml', 'menu_id': 'menu_business_evaluation'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/router_certificate_views.xml', 'menu_id': 'menu_router_certificate'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/service_dashboard.xml', 'menu_id': 'menu_wuchang_service_dashboard'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml', 'menu_id': 'menu_wuchang_settings'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml', 'menu_id': 'menu_wuchang_sister_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/sister_control_views.xml', 'menu_id': 'menu_wuchang_sister_control'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'menu_id': 'menu_wuchang_system_tools'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'menu_id': 'menu_wuchang_system_medic'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/system_tools_views.xml', 'menu_id': 'menu_wuchang_audit_log'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_command_center'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_command_voice'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_command_voice_reference'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_supreme_menu'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_task_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/task_views.xml', 'menu_id': 'menu_wuchang_task'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ui_proxy_views.xml', 'menu_id': 'menu_ui_proxy'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_menus.xml', 'menu_id': 'menu_wuchang_root'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_menus.xml', 'menu_id': 'menu_wuchang_chronos'}
- {'file': '/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/wuchang_menus.xml', 'menu_id': 'menu_wuchang_covenant'}

## 6. Committee Keyword Hits

- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py:notice
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/main.py:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/order_site.py:announcement
- PY_PARSE_FAIL:/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/controllers/sister_controller.py:invalid non-printable character U+FEFF (<unknown>, line 1)
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:notice
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:公告
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/committee_document_templates.xml:管理委員
- XML_PARSE_FAIL:/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/meeting_setup.xml:not well-formed (invalid token): line 1, column 2
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/meeting_setup.xml:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/data/meeting_setup.xml:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_property_expert.py:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/ai_property_expert.py:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/collab_meeting.py:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:notice
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:公告
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_document.py:管理委員
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:repair
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:報修
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/property_management.py:公告
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_partner.py:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/res_partner.py:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/settings.py:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/settings.py:公告
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py:meeting
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/models/volunteer.py:公告
- XML_PARSE_FAIL:/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/static/src/xml/delivery_interfaces.xml:mismatched tag: line 98, column 10
- XML_PARSE_FAIL:/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/ambassador.xml:not well-formed (invalid token): line 50, column 162
- XML_PARSE_FAIL:/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/device_web_app_templates.xml:not well-formed (invalid token): line 57, column 53
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/knowledge_templates.xml:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/knowledge_templates.xml:會議
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/knowledge_templates.xml:公告
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/order_website.xml:announcement
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_document_views.xml:管理委員
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml:committee
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml:管委會
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/property_views.xml:報修
- /home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core/views/settings_views.xml:announcement

## 7. 判讀

- `wuchang_core` 是目前場觀排名最高的 direct_committee_module。
- 下一步應判斷它是否為 canonical path，或需要同步到目前正式 Odoo addons path。
- 安裝前須確認是否已有同名模組、資料模型是否與現有 DB 相容、權限是否符合小J域與 W7TP hardwall。

## 8. Hardwall

- READ_ONLY=true
- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false

JSON=runtime/reports/W7TP_WUCHANG_CORE_COMMITTEE_MODULE_READ_20260526_004340.json
REPORT=runtime/reports/W7TP_WUCHANG_CORE_COMMITTEE_MODULE_READ_20260526_004340.md
