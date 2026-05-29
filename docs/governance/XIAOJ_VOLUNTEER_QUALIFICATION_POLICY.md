# 小J志工資格與接單政策

狀態：PLANONLY / GOVERNANCE DESIGN ONLY

## 1. 制度目的

志工外送服務涉及弱勢居民、實體接觸與最小必要個資揭露，因此志工不得只因登入、加入群組或自行點選就能接單。

## 2. 接單前必要條件

- volunteer_verified=true
- staff_approved=true
- renyi_store_staff_approved=true
- renyi_store_staff_accompaniment_required=true
- renyi_store_staff_hash 必須存在
- training_status=completed 或符合服務類型要求
- suspension_status=clear
- service_scope 符合任務區域
- high_risk_service_allowed=false，除非人工特別核准

## 3. 仁義店職員核定陪同硬條件

- 志工不得自行接單。
- 志工接單前必須由仁義店職員核定。
- 任務若涉及外送、實體接觸、弱勢居民、地址揭露或安全風險，必須有仁義店職員陪同、監督或到場確認。
- 沒有仁義店職員核定時，狀態不得從 waiting_volunteer_accept 轉為 accepted。
- 沒有仁義店職員陪同或監督紀錄時，不得進入 pii_limited_unlocked。

## 4. 志工可見範圍

- waiting_volunteer_accept：只看區域級資訊、物品摘要、時間窗。
- accepted：經仁義店職員核定後，才可限時揭露最小必要資訊。
- delivery_completed/service_closed：自動收回前端可見權限。

## 5. 停權條件

- 未經仁義店職員核定自行接單。
- 未陪同或未受監督卻嘗試接觸居民。
- 截圖外流。
- 任務資訊轉傳。
- 未經授權聯絡居民。
- 重複取消接單。
- 回報不實。
- 嘗試取得非必要個資。

## 6. 高風險服務

以下不得由普通志工自動接單：

- 金流 / 代付款
- 藥品
- 貴重物
- 緊急救命事件
- 單獨進屋服務
- 涉及健康、家庭、財務高度敏感資訊

## 7. Hardwall

- login_is_not_volunteer_verified=true
- wifi_is_not_identity=true
- ai_auto_dispatch=false
- volunteer_self_accept_allowed=false
- renyi_store_staff_approval_required=true
- renyi_store_staff_accompaniment_required=true
- raw_pii_to_cloud=false
- odoo_write=false
- human_review_required_for_high_risk=true

## 8. 仁義店職員照服員資格安全理由

仁義店職員具照服員資格，因此在志工外送服務中不是一般旁觀者，而是具備高齡者照護、安全判斷、服務風險辨識與現場陪同能力的核定角色。

本制度要求志工接單須有仁義店職員核定陪同，原因包括：

- 高齡志工可能需要現場安全協助。
- 高齡居民或弱勢居民服務需要照護敏感度。
- 外送過程可能涉及跌倒、身體不適、失智、溝通困難或突發狀況。
- 仁義店職員可協助判斷是否應轉人工關懷、DLQ、緊急協助或取消派送。
- 仁義店職員陪同可降低志工單獨接觸弱勢居民的風險。

因此，志工自行接單仍禁止；仁義店照服員資格職員核定與陪同是安全硬條件。
