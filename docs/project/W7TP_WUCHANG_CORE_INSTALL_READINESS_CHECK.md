# W7TP wuchang_core 安裝就緒檢查

TIME=2026-05-26T00:44:47
SOURCE=runtime/reports/W7TP_WUCHANG_CORE_COMMITTEE_MODULE_READ_20260526_004340.json
MODULE_PATH=/home/taiji_admin/wuchang_recovery/wuchangv600_extra-addons/wuchang_core

## 1. 模組身分

- module_name=Wuchang AI Task Force (Unified)
- version=17.0.2.0.0
- installable=True
- application=True
- depends=base, web, point_of_sale, website, hr, project, maintenance

## 2. 結構統計

- models=72
- access_rows=2
- menus=51
- actions=39
- views=74
- committee_keyword_hits=55

## 3. 安裝風險判斷

- installable=true，具備可安裝條件。
- ACCESS_COVERAGE_RISK=HIGH：models=72 但 access_rows=2。
- MISSING_ACCESS_MODEL_COUNT=70

## 4. 管委會相關模型

- wuchang.ai.agent
- wuchang.ai.config
- wuchang.ai.hallucination.monitor
- wuchang.ai.learning.log
- wuchang.ai.logic
- wuchang.ai.meeting
- wuchang.ai.memory
- wuchang.ai.perception.sensor
- wuchang.ai.prompt
- wuchang.ai.supervisor.log
- wuchang.ai.trusted.device
- wuchang.api.account.separation
- wuchang.audit.log
- wuchang.chronos.device
- wuchang.coin.ledger
- wuchang.collab.space
- wuchang.community.coin
- wuchang.customer.display.music.check
- wuchang.customer.display.music.config
- wuchang.customer.display.music.playlist
- wuchang.delivery.order
- wuchang.delivery.team
- wuchang.device.audio
- wuchang.device.control.execution.log
- wuchang.device.control.plan
- wuchang.device.display
- wuchang.device.node
- wuchang.digital.signage
- wuchang.infrastructure.device
- wuchang.jf.gateway
- wuchang.legal.doc
- wuchang.life.covenant
- wuchang.menu.addon
- wuchang.menu.attribute
- wuchang.menu.attribute.value
- wuchang.menu.item
- wuchang.menu.item.addon
- wuchang.menu.item.attribute
- wuchang.order
- wuchang.platform.admin
- wuchang.pos.expense
- wuchang.privacy.mask
- wuchang.property.building
- wuchang.property.committee.member
- wuchang.property.community
- wuchang.property.complaint
- wuchang.property.document
- wuchang.property.expert.ai
- wuchang.property.financial.report
- wuchang.property.unit
- wuchang.router.certificate
- wuchang.signage.content
- wuchang.sister.control
- wuchang.social.config
- wuchang.system.medic
- wuchang.task
- wuchang.ui.proxy
- wuchang.voice.conversation
- wuchang.voice.conversation.stats
- wuchang.voice.sample
- wuchang.volunteer.announcement
- wuchang.volunteer.meeting
- wuchang.volunteer.signup
- wuchang.volunteer.task
- wuchang.voucher.product
- wuchang.wit

## 5. 可能缺 access 的模型

- User
- community.bulletin
- community.fund.account
- community.fund.transaction
- community.package
- wuchang.ai.agent
- wuchang.ai.config
- wuchang.ai.hallucination.monitor
- wuchang.ai.learning.log
- wuchang.ai.logic
- wuchang.ai.meeting
- wuchang.ai.memory
- wuchang.ai.perception.sensor
- wuchang.ai.prompt
- wuchang.ai.supervisor.log
- wuchang.ai.trusted.device
- wuchang.api.account.separation
- wuchang.audit.log
- wuchang.coin.ledger
- wuchang.collab.space
- wuchang.community.coin
- wuchang.customer.display.music.check
- wuchang.customer.display.music.config
- wuchang.customer.display.music.playlist
- wuchang.delivery.order
- wuchang.delivery.team
- wuchang.device.audio
- wuchang.device.control.execution.log
- wuchang.device.control.plan
- wuchang.device.display
- wuchang.device.node
- wuchang.digital.signage
- wuchang.infrastructure.device
- wuchang.jf.gateway
- wuchang.legal.doc
- wuchang.menu.addon
- wuchang.menu.attribute
- wuchang.menu.attribute.value
- wuchang.menu.item
- wuchang.menu.item.addon
- wuchang.menu.item.attribute
- wuchang.order
- wuchang.platform.admin
- wuchang.pos.expense
- wuchang.privacy.mask
- wuchang.property.building
- wuchang.property.committee.member
- wuchang.property.community
- wuchang.property.complaint
- wuchang.property.document
- wuchang.property.expert.ai
- wuchang.property.financial.report
- wuchang.property.unit
- wuchang.router.certificate
- wuchang.signage.content
- wuchang.sister.control
- wuchang.social.config
- wuchang.system.medic
- wuchang.task
- wuchang.ui.proxy
- wuchang.voice.conversation
- wuchang.voice.conversation.stats
- wuchang.voice.sample
- wuchang.volunteer.announcement
- wuchang.volunteer.meeting
- wuchang.volunteer.signup
- wuchang.volunteer.task
- wuchang.voucher.product
- wuchang.wit
- 聊國咖啡重新總店

## 6. Actions target models

- account.move
- community.bulletin
- community.fund.account
- community.package
- pos.order
- res.config.settings
- transparency.log
- wish.tree.card
- wish.tree.fruit
- wuchang.ai.agent
- wuchang.ai.memory
- wuchang.ai.prompt
- wuchang.audit.log
- wuchang.chronos.device
- wuchang.coin.transaction
- wuchang.customer.display.music.check
- wuchang.customer.display.music.config
- wuchang.customer.display.music.playlist
- wuchang.device.audio
- wuchang.device.control.execution.log
- wuchang.device.control.plan
- wuchang.device.display
- wuchang.device.node
- wuchang.digital.signage
- wuchang.infrastructure.device
- wuchang.life.covenant
- wuchang.order
- wuchang.pos.expense
- wuchang.property.community
- wuchang.property.complaint
- wuchang.property.document
- wuchang.router.certificate
- wuchang.sister.control
- wuchang.system.medic
- wuchang.task
- wuchang.ui.proxy

## 7. Views target models

- account.move
- community.bulletin
- community.fund.account
- community.package
- pos.config
- pos.order
- res.config.settings
- res.partner
- transparency.log
- wish.tree.card
- wish.tree.fruit
- wuchang.ai.agent
- wuchang.ai.memory
- wuchang.ai.prompt
- wuchang.audit.log
- wuchang.chronos.device
- wuchang.coin.transaction
- wuchang.customer.display.music.check
- wuchang.customer.display.music.config
- wuchang.customer.display.music.playlist
- wuchang.device.audio
- wuchang.device.control.execution.log
- wuchang.device.control.plan
- wuchang.device.display
- wuchang.device.node
- wuchang.digital.signage
- wuchang.infrastructure.device
- wuchang.order
- wuchang.pos.expense
- wuchang.property.community
- wuchang.property.complaint
- wuchang.property.document
- wuchang.property.unit
- wuchang.router.certificate
- wuchang.sister.control
- wuchang.system.medic
- wuchang.task
- wuchang.ui.proxy

## 8. 裁決

- wuchang_core 是目前社區管委會真實主候選模組。
- 不應另起空白管委會模組取代它。
- 正確路線：先把 wuchang_core 標為 legacy_recovered_canonical_candidate，再補 access/security/manifest/path 對齊。
- 安裝前必須處理 access coverage，否則可能 UI/權限異常。

## 9. 下一步

1. 產出 wuchang_core canonical sync plan。
2. 補齊 ir.model.access.csv 草案。
3. 同步到正式 addons path。
4. 再由授權人執行 DB install/update。

## 10. Hardwall

- DB_WRITE=false
- MODULE_INSTALL=false
- SERVICE_RESTART=false
- SECRET_READ=false
- RAW_PII_TO_CLOUD=false
- READINESS_CHECK_ONLY=true
