# PUBLIC_TEST_ENTRY_CANDIDATE_V1

中文名稱：上品聊國咖啡館重新總店前場公開測試入口候選

## 狀態

STATE=CANDIDATE_ONLY  
中文狀態=前場入口候選，尚未正式上線

## 顯示文案

標題：上品聊國咖啡館｜小J公開測試

提示：

目前為候選測試，不會自動成立正式訂單或付款。  
請由店員或創辦人確認後再執行下一步。  
若涉及會員資料、付款、密碼、權杖或正式訂單，小J必須暫停並交由人審。

## 可見功能

1. 我要點餐
2. 我要預購
3. 我要查寄杯
4. 我要使用任務券
5. 今天推薦什麼
6. 詢問公益活動
7. 店員確認候選單

## 禁止

- 讀 raw key/token/password/secret
- 讀 .env
- 讀 google_credentials.xml
- 讀 data/internal_members
- 讀會員明文
- dump DB
- DB write
- 寫入 Odoo
- 正式建立訂單
- 正式金流
- deploy/restart/reboot
- router write
- git push

## 下一步

NEXT_SINGLE_ACTION=建立 PUBLIC_TEST_CHAIN_FINAL_REVIEW_V1
