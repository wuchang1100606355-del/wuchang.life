# PUBLIC_TEST_LANDING_FLOW_V1
中文名稱：上品聊國咖啡館重新總店公開測試落地流程候選

## 狀態

STATE=CANDIDATE_ONLY  
中文狀態=候選流程，尚未正式上線

## 邊界

允許：

- 前場自然語言點餐測試
- Odoo 菜單唯讀引用
- 小J產生候選單
- 店員或創辦人人審
- 十組現場案例驗收
- 前場入口候選文件

禁止：

- 讀 raw key/token/password/secret
- 讀 .env
- 讀 google_credentials.xml
- 讀 data/internal_members
- 讀會員明文
- dump DB
- DB write
- 寫入 Odoo
- 正式金流
- deploy/restart/reboot
- git push

## 流程

1. S01_SCOPE_LOCK：公開測試範圍鎖定
2. S02_MENU_READONLY：Odoo 菜單唯讀引用
3. S03_NL_COUNTER_PACKET：自然語言櫃台候選單
4. S04_HUMAN_CONFIRM_GATE：店員或創辦人人審確認
5. S05_REAL_WORLD_TESTS：十組現場測試案例驗收
6. S06_PUBLIC_TEST_ENTRY_READY：前場公開測試入口候選準備

## 下一步

NEXT_SINGLE_ACTION=建立 PUBLIC_TEST_ENTRY_CANDIDATE_V1
