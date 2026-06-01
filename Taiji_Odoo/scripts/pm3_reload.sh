#!/usr/bin/env bash
set -e

cd ~/Taiji_Hub/Taiji_Odoo

docker exec -it wuchang_os_odoo_18 odoo \
-u pm3_base \
-d postgres \
--db_host=wuchang_db \
--db_port=5432 \
--db_user=odoo \
--db_password=taiji_secret \
--stop-after-init
