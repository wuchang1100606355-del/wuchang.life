# POS Official Chain Lock

STATE=POS_OFFICIAL_CHAIN_LOCKED
SCOPE=TOTAL_FIELD_POS_LOCATION_BRIEF
FILES_CHANGED=SUMMARY_ONLY

## Canonical POS location

POS_OFFICIAL_CHAIN=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/wuchang_core/

## Definition

本系統之高級 POS 商用系統為 Odoo 內建商用 POS / 菜單 / 小J 接客顯示系統之整合主鏈，不是外掛 demo、不是普通網頁、不是普通 chatbot、不是普通 GPT 測試。

正式入口概念：

ENTRY=/wuchang/xiaoj/ordering

## Key paths

Taiji_Odoo/addons/wuchang_core/data/breakfast_pos_menu.xml
Taiji_Odoo/addons/wuchang_core/models/pos_config_ext.py
Taiji_Odoo/addons/wuchang_core/static/src/js/pos_extension.js
Taiji_Odoo/addons/wuchang_core/controllers/xiaoj_ordering_app_controller.py
Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/

## Product evidence

docs/evidence/product_av_ordering_ai/
packets/product_av_ordering_ai/

## Architecture

Odoo commercial POS
+ breakfast/menu data
+ POS extension
+ XiaoJ customer-facing ordering/display
+ candidate order layer
+ dry-run / governance gate
+ formal write/payment/release controlled by execution field

## Red-team rule

禁止再另開外部 demo POS。
禁止把 `/wuchang/xiaoj/ordering` 當普通網頁。
禁止把 XiaoJ POS 當普通 chatbot。
禁止繞過 Taiji_Odoo/addons/wuchang_core 主鏈。

## Safety

FORMAL_DB_WRITE=FALSE
FORMAL_POS_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

NEXT_ACTION=INSPECT_OFFICIAL_ODOO_XIAOJ_POS_CHAIN_ONLY
