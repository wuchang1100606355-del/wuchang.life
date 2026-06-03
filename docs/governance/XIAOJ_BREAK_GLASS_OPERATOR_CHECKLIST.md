# 小J Break-glass Operator Checklist

狀態：PLANONLY / CHECKLIST ONLY

## 開封前

- [ ] 是否有合法目的。
- [ ] 是否有案件編號或服務理由。
- [ ] 是否已定義 requested_data_scope。
- [ ] 是否已選擇 2_of_3 或 3_of_3。
- [ ] 是否確認非好奇查詢、非工程除錯、非雲端要求。

## 開封中

- [ ] 是否只顯示最小必要欄位。
- [ ] 是否禁止截圖、複製、匯出。
- [ ] 是否記錄 opened_by、opened_at、expiry_time。
- [ ] 是否確認 raw_pii_to_cloud=false。

## 開封後

- [ ] 是否 revoke access。
- [ ] 是否建立 audit record。
- [ ] 是否通知必要審核者。
- [ ] 是否確認未寫入 logs、memory、prompt、DLQ raw payload。
