# wuchang_core Truth Audit Fixed

TIME=2026-05-26T01:21:01+08:00

## Module State
 id  |               name                |    state    | latest_version 
-----+-----------------------------------+-------------+----------------
 681 | wuchang_cafe_menu_options         | uninstalled | 
 682 | wuchang_core                      | installed   | 18.0.2.0.0
 713 | wuchang_fund_allocation           | uninstalled | 
 705 | wuchang_google_member_login       | installed   | 18.0.1.0.0
 714 | wuchang_knowledge_sync            | uninstalled | 
 704 | wuchang_line_login                | installed   | 18.0.1.0
 715 | wuchang_property_local_cloud      | uninstalled | 
 716 | wuchang_property_manpower_surface | uninstalled | 
 717 | wuchang_wish_tree_coin            | uninstalled | 
(9 rows)

## Counts
      kind       | count 
-----------------+-------
 wuchang_models  |    22
 wuchang_menus   |     0
 wuchang_actions |     0
(3 rows)

## Menus
 id | name | parent_id | action 
----+------+-----------+--------
(0 rows)

## Web
WEB_OK=true

## Verdict
wuchang_core_installed=true
odoo_web_ok=true
wrong_table_fixed=ir_act_window

## Boundary
DB_READ=true
DB_WRITE=false
MODULE_INSTALL=false
SERVICE_RESTART=false
RAW_PII_TO_CLOUD=false
SECRET_READ=false
