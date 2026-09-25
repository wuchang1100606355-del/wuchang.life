# 小J影音點餐雙軌實習精裝使用說明書

STATE=PREMIUM_USER_MANUAL_READY_RUNTIME_HOLD

本說明書給聊國咖啡館重新總店的店長、店員與總場人員使用。
它描述的是「下場實習雙軌制」：店內真營業照原本流程走，小J在旁邊練習、整理、翻譯、提示與產生候選單。

> 重要：本階段小J可訓練、可展示、可本地演練；尚不可直接寫入真 POS、不可真下單、不可真付款。

## 1. 一句話版本

小J是現場實習助手，不是收銀權限本身。

| 軌道 | 誰負責 | 可以做什麼 | 不可以做什麼 |
| --- | --- | --- | --- |
| A 軌：真營業 | 店員 / 店長 | 接客、收現、真 POS、收據、交班 | 讓小J自動下單或付款 |
| B 軌：小J實習 | 小J / 總場 | 聽文字、解析語音、翻譯、候選單、候選付款、候選收據、差異記錄 | 寫 Odoo DB、建 POS 訂單、capture payment |

固定口令：

```text
TRACK_A_LIVE_OPERATION=HUMAN_ONLY
TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY
```

## 2. 今日現場怎麼用

1. 店員照原本 POS / 櫃台流程服務客人。
2. 小J接收文字或 STT 後的文字稿。
3. 小J只產生候選，不直接操作 POS。
4. 店員或店長對照真實操作，判斷小J是否準。
5. 正確就記為實習成功；錯誤就記為改進項。
6. 真實收款與交班仍由人處理。

## 3. 店員語音 POS 規則

店員念餐點時，固定照順序念：

```text
尺寸 → 溫度 → 甜度 → 品項
```

範例：

```text
大冰少糖拿鐵
```

小J解析：

| 順序 | 中文 | English | Vietnamese | 範例值 |
| --- | --- | --- | --- | --- |
| 1 | 尺寸 | Size | Kich co | 大 |
| 2 | 溫度 | Temperature | Nhiet do | 冰 |
| 3 | 甜度 | Sweetness | Do ngot | 少糖 |
| 4 | 品項 | Item | Mon | 拿鐵 |

如果店員念成：

```text
拿鐵大冰少糖
```

小J不能直接下單，但可以複誦請示：

```text
我聽到像是「大冰少糖拿鐵」，請店員或店長確認。
```

此時狀態是 `repeat_confirmation_required=true`。確認前，小J仍不可寫 POS。

## 4. 越南店長快速確認表

| 店內中文 | Vietnamese | 使用時機 |
| --- | --- | --- |
| 確認候選 | Xac nhan ban nhap | 店長確認小J候選內容 |
| 只做演練 | Chi dien tap | 不進真 POS |
| 不寫 POS | Khong ghi POS | 小J不可直接落單 |
| 等店長確認 | Doi quan ly xac nhan | 改價、退單、預支 |
| 現金櫃台確認 | Quay xac nhan tien mat | 現金由櫃台確認 |

## 5. 小J可以幫忙的事

| 場景 | 小J輸出 | 人的責任 |
| --- | --- | --- |
| 店員語音點餐 | 解析尺寸/溫度/甜度/品項 | 確認是否與客人一致 |
| 菜單查詢 | 候選菜單說明 | 確認真實菜單 source 已鎖 |
| 翻譯 | 中文/越文/英文輔助句 | 不讓翻譯改變價格或餐點 |
| 下單 | order candidate | 店員在 A 軌真 POS 下單 |
| 付款 | payment candidate | 櫃台確認現金或授權支付 |
| 收據 | receipt candidate | 真 POS 產生正式收據 |
| 改價 | manager candidate | 店長確認 |
| 退單 | return candidate | 店長確認 |
| 現金預支 | evidence ref candidate | 店長/總場留證 |

## 6. 真菜單鎖定原則

小J不能使用 GPT 自己編的菜單。真菜單只能來自已鎖定 source。

目前狀態：

```text
HOLD_REAL_MENU_SOURCE_LOCK
```

這代表：

- QuickClick 視覺證據可作參考。
- 尚未完成 live export / source hash / 人審衝突確認。
- 小J不可把未鎖定商品拿去做真交易。
- 沒有價格權威時，候選單 amount 必須保守，不可亂填價格。

## 7. 下場實習日誌

每天可以用這張表記錄小J實習：

| 時間 | 店員說法 | 小J解析 | 真 POS 操作 | 是否一致 | 後續 |
| --- | --- | --- | --- | --- | --- |
| 例：09:10 | 大冰少糖拿鐵 | 大 / 冰 / 少糖 / 拿鐵 | 人工處理 | 待確認 | 菜單 source 未鎖 |

建議判定：

| 結果 | 意義 |
| --- | --- |
| PASS | 小J解析與人一致 |
| WARN | 小J解析可用但需店長修正 |
| HOLD | 菜單、價格、會員、付款或權限不足 |
| FAIL | 小J理解錯或有安全風險 |

## 8. 店內不可踩的線

小J在實習階段不可做：

- 不建立真 POS 訂單。
- 不 capture payment。
- 不寫 Odoo DB。
- 不保存 raw audio。
- 不讀會員明文。
- 不讀 secret。
- 不外部 API。
- 不 restart。
- 不 deploy。

## 9. 可以給店員的一句話

```text
你照「尺寸、溫度、甜度、品項」念，小J幫你整理成候選單；真正送 POS 還是你和店長確認。
```

Vietnamese:

```text
Nhan vien doc theo thu tu: kich co, nhiet do, do ngot, mon. XiaoJ chi tao ban nhap, quan ly xac nhan truoc khi ghi POS.
```

English:

```text
Staff speaks size, temperature, sweetness, then item. XiaoJ creates a draft only; the manager confirms before POS.
```

## 10. 可用命令

本地語音點餐演練：

```bash
python3 tools/xiaoj_p1_local_rehearsal.py --transcript '大冰少糖拿鐵'
```

驗證小J本地語音鏈：

```bash
python3 scripts/verify/verify_xiaoj_p1_local_rehearsal.py
```

驗證雙軌規則：

```bash
python3 scripts/verify/verify_xiaoj_field_practicum_dual_track.py
```

驗證 P1 console 原型：

```bash
python3 scripts/verify/verify_xiaoj_p1_console_prototype.py
```

## 11. 升級成正式營運的條件

小J要從 B 軌實習升級成「協助真營業」，至少要全部通過：

- LINE / Google / member registration route 不再 raw 404。
- 真實菜單 source lock 完成。
- 商品、分類、加購、價格有 source hash。
- Odoo module release 人審通過。
- POS order create 人審通過。
- Payment capture 人審通過。
- rollback plan 存在。
- 店長簽核。

在此之前：

```text
STATE=FIELD_PRACTICUM_ONLY
```

## 12. Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
