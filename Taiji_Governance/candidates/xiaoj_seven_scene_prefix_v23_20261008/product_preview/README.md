# 五常小J社區服務完成系統

這是依同 lineage active 產品根建立的全新原創隔離候選。產品以居民、商業雲、物業雲三場景為主，Open WebUI不參與產品架構；Odoo仍是會員、角色、組織、商家、物業、流程與帳務權威。

## 候選邊界

- 不連正式Odoo API。
- 不連9107或雲端模型。
- 不讀會員明文或secret。
- 不執行DB write、外部傳送、deploy、restart或runtime變更。
- 所有副作用操作只產生Action Review Packet；批准後仍維持正式效果封鎖。

## 本機檢查

```bash
python3 tests/validate_candidate.py
python3 -m http.server 19090 --bind 127.0.0.1
```

開啟 `http://127.0.0.1:19090/` 可查看隔離候選。此指令只用於本機驗收，不是部署。

根封包：

`runtime/total_field/product_system_root/PRODUCT_SYSTEM_ROOT_SUCCESSOR_WUCHANG_XIAOJ_20260730T190929Z/W7TP_PRODUCT_SYSTEM_ROOT_SUCCESSOR.json`

根封包 SHA-256：

`336ec63144db4840c2cb716cd7e035a1e8c6441fc4d12b67779bd0da0627fafe`
