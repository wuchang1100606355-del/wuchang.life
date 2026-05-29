# W7TP Google Maps Nonprofit Credit Note

狀態：ARCHITECTURE NOTE / NO SECRET

## 原則

- 本系統可使用 Google 非營利組織相關地圖抵免額或公益額度。
- Google Maps API key 不得寫入 XML、JS、Git、log、prompt、memory、DLQ raw payload。
- Odoo / QWeb / JS 只能使用 key_alias、環境變數、系統參數或 Gateway 注入後的受控設定。
- 前端地圖功能應允許 fallback，例如 OpenStreetMap 或靜態位置摘要。
- Google Maps 使用應記錄 usage ledger / cost summary，不記錄實際 key。

## Hardwall

- google_maps_api_key_plaintext_in_repo=false
- google_maps_key_in_prompt=false
- google_maps_key_in_log=false
- google_maps_credit_available=true
- nonprofit_credit_policy_required=true
