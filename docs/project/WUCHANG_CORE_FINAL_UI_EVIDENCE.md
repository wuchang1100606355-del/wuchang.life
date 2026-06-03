# wuchang_core Final UI Evidence

TIME=2026-05-26T01:25:52+08:00

## Verdict

wuchang_core_installed=true
phase2b_orm_ui_created=true
web_ok=true
root_menu_id=342

## Module

 id  |     name     |   state   | latest_version 
-----+--------------+-----------+----------------
 682 | wuchang_core | installed | 18.0.2.0.0
(1 row)

## Menus

 id  |                     name                      | parent_id |          action           | sequence 
-----+-----------------------------------------------+-----------+---------------------------+----------
 341 | {"en_US": "五常社區管委會 / 小J"}             |           |                           |       60
 342 | {"en_US": "五常社區管委會 / 小J"}             |           |                           |       60
 343 | {"en_US": "五常 / ai.hallucination.monitor"}  |       342 | ir.actions.act_window,555 |        1
 344 | {"en_US": "五常 / ai.learning.log"}           |       342 | ir.actions.act_window,556 |        2
 345 | {"en_US": "五常 / ai.memory"}                 |       342 | ir.actions.act_window,557 |        3
 346 | {"en_US": "五常 / ai.prompt"}                 |       342 | ir.actions.act_window,558 |        4
 347 | {"en_US": "五常 / ai.supervisor.log"}         |       342 | ir.actions.act_window,559 |        5
 348 | {"en_US": "五常 / ai.trusted.device"}         |       342 | ir.actions.act_window,560 |        6
 349 | {"en_US": "五常 / chronos.device"}            |       342 | ir.actions.act_window,561 |        7
 350 | {"en_US": "五常 / coin.ledger"}               |       342 | ir.actions.act_window,562 |        8
 351 | {"en_US": "五常 / life.covenant"}             |       342 | ir.actions.act_window,563 |        9
 352 | {"en_US": "五常 / line.user"}                 |       342 | ir.actions.act_window,564 |       10
 353 | {"en_US": "五常 / property.building"}         |       342 | ir.actions.act_window,565 |       11
 354 | {"en_US": "五常 / property.committee.member"} |       342 | ir.actions.act_window,566 |       12
 355 | {"en_US": "五常 / property.community"}        |       342 | ir.actions.act_window,567 |       13
 356 | {"en_US": "五常 / property.complaint"}        |       342 | ir.actions.act_window,568 |       14
 357 | {"en_US": "五常 / property.financial.report"} |       342 | ir.actions.act_window,569 |       15
 358 | {"en_US": "五常 / property.unit"}             |       342 | ir.actions.act_window,570 |       16
 359 | {"en_US": "五常 / task"}                      |       342 | ir.actions.act_window,571 |       17
 360 | {"en_US": "五常 / voice.sample"}              |       342 | ir.actions.act_window,572 |       18
 361 | {"en_US": "五常 / volunteer.announcement"}    |       342 | ir.actions.act_window,573 |       19
 362 | {"en_US": "五常 / volunteer.meeting"}         |       342 | ir.actions.act_window,574 |       20
 363 | {"en_US": "五常 / volunteer.signup"}          |       342 | ir.actions.act_window,575 |       21
 364 | {"en_US": "五常 / volunteer.task"}            |       342 | ir.actions.act_window,576 |       22
(24 rows)

## Actions

 id  |                     name                      |             res_model             | view_mode 
-----+-----------------------------------------------+-----------------------------------+-----------
 555 | {"en_US": "五常 / ai.hallucination.monitor"}  | wuchang.ai.hallucination.monitor  | list,form
 556 | {"en_US": "五常 / ai.learning.log"}           | wuchang.ai.learning.log           | list,form
 557 | {"en_US": "五常 / ai.memory"}                 | wuchang.ai.memory                 | list,form
 558 | {"en_US": "五常 / ai.prompt"}                 | wuchang.ai.prompt                 | list,form
 559 | {"en_US": "五常 / ai.supervisor.log"}         | wuchang.ai.supervisor.log         | list,form
 560 | {"en_US": "五常 / ai.trusted.device"}         | wuchang.ai.trusted.device         | list,form
 561 | {"en_US": "五常 / chronos.device"}            | wuchang.chronos.device            | list,form
 562 | {"en_US": "五常 / coin.ledger"}               | wuchang.coin.ledger               | list,form
 563 | {"en_US": "五常 / life.covenant"}             | wuchang.life.covenant             | list,form
 564 | {"en_US": "五常 / line.user"}                 | wuchang.line.user                 | list,form
 565 | {"en_US": "五常 / property.building"}         | wuchang.property.building         | list,form
 566 | {"en_US": "五常 / property.committee.member"} | wuchang.property.committee.member | list,form
 567 | {"en_US": "五常 / property.community"}        | wuchang.property.community        | list,form
 568 | {"en_US": "五常 / property.complaint"}        | wuchang.property.complaint        | list,form
 569 | {"en_US": "五常 / property.financial.report"} | wuchang.property.financial.report | list,form
 570 | {"en_US": "五常 / property.unit"}             | wuchang.property.unit             | list,form
 571 | {"en_US": "五常 / task"}                      | wuchang.task                      | list,form
 572 | {"en_US": "五常 / voice.sample"}              | wuchang.voice.sample              | list,form
 573 | {"en_US": "五常 / volunteer.announcement"}    | wuchang.volunteer.announcement    | list,form
 574 | {"en_US": "五常 / volunteer.meeting"}         | wuchang.volunteer.meeting         | list,form
 575 | {"en_US": "五常 / volunteer.signup"}          | wuchang.volunteer.signup          | list,form
 576 | {"en_US": "五常 / volunteer.task"}            | wuchang.volunteer.task            | list,form
(22 rows)

## Non-blocking Warnings

KeyError: 'account.move'
2026-05-25 17:10:45,631 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'HR Employee: check work permit validity' (20) server action #336 failed 
Traceback (most recent call last):
KeyError: 'hr.employee'
2026-05-25 17:10:45,662 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Project: Send rating' (21) server action #376 failed 
Traceback (most recent call last):
KeyError: 'project.project'
2026-05-25 17:10:45,690 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Procurement: run scheduler' (22) server action #379 failed 
Traceback (most recent call last):
KeyError: 'procurement.group'
2026-05-25 17:10:45,722 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Disable unused snippets assets' (23) server action #474 failed 
Traceback (most recent call last):
KeyError: 'website'
2026-05-25 17:10:45,750 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Website Visitor : clean inactive visitors' (24) server action #476 failed 
Traceback (most recent call last):
KeyError: 'website.visitor'
2026-05-25 17:10:45,784 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Mail: Email Queue Manager' (3) server action #133 failed 
Traceback (most recent call last):
KeyError: 'mail.mail'
2026-05-25 17:10:45,816 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Users: Notify About Unregistered Users' (12) server action #159 failed 
Traceback (most recent call last):
AttributeError: 'res.users' object has no attribute 'send_unregistered_user_reminder'
Traceback (most recent call last):
    raise ValueError('%r while evaluating\n%r' % (e, expr))
ValueError: AttributeError("'res.users' object has no attribute 'send_unregistered_user_reminder'") while evaluating
2026-05-25 17:10:45,859 1 ERROR postgres odoo.addons.base.models.ir_cron: Job 'Partner Autocomplete: Sync with remote DB' (13) server action #211 failed 
Traceback (most recent call last):
KeyError: 'res.partner.autocomplete.sync'
2026-05-25 17:13:44,281 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:13:45,307 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:13:45,427 1 WARNING postgres odoo.fields: Field wuchang.volunteer.meeting.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:13:45,427 1 WARNING postgres odoo.fields: Field wuchang.volunteer.announcement.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:13:45,455 1 INFO postgres odoo.modules.registry: Registry loaded in 1.173s 
2026-05-25 17:22:43,152 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:22:44,189 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:22:44,307 1 WARNING postgres odoo.fields: Field wuchang.volunteer.meeting.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:22:44,307 1 WARNING postgres odoo.fields: Field wuchang.volunteer.announcement.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:22:44,337 1 INFO postgres odoo.modules.registry: Registry loaded in 1.183s 
2026-05-25 17:24:49,044 1 INFO ? odoo.service.server: HTTP service (werkzeug) running on 05d5febb8401:8069 
2026-05-25 17:24:50,398 1 WARNING postgres odoo.models: The model wuchang.ai.supervisor.log has no _description 
2026-05-25 17:24:50,495 1 WARNING postgres odoo.fields: Field wuchang.volunteer.meeting.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:24:50,495 1 WARNING postgres odoo.fields: Field wuchang.volunteer.announcement.team_id with unknown comodel_name 'wuchang.delivery.team' 
2026-05-25 17:24:50,513 1 INFO postgres odoo.modules.registry: Registry loaded in 1.469s 

## Next Patch Items

- Add _description to model wuchang.ai.supervisor.log.
- Add or restore model wuchang.delivery.team, or change team_id comodel target.
- These are warnings only; current registry and web service are loaded.

## Boundary

DB_READ=true
DB_WRITE=false
MODULE_INSTALL=false
SERVICE_RESTART=false
RAW_PII_TO_CLOUD=false
SECRET_READ=false
