# W7TP 8D Identity Feature Marking Policy

Status: draft for review  
Scope: 8D identity-code feature markers for community, merchant, property, association, personal, group, vehicle, equipment, and facility contexts

## Purpose

八維碼身份可標記身份特徵，但標記不是正式身分裁決。任何居民、商家、物業、協會、設備、車輛、個人或團體身份特徵，皆只能作為候選標記，必須回到總場 / Odoo / Vault / 人工授權資料進行驗證。

Required invariants:

- `contains_member_plaintext=false`
- `plaintext_identity_forbidden=true`
- `feature_assertion_mode=candidate_marker_only`
- `requires_total_field_verify=true`
- 不保存姓名、電話、地址、車牌、身分證字號、token、secret

## Static Group Spatial Positioning

7/8 維封包不只可以記錄資訊，也可以做空間定位；但本 policy 將定位限定為「靜態團體定位」，不是個人定位。

允許定位：

- 本會轄區
- 里級或服務區級邊界
- 團體 / 組織 / 協會
- 物業 / 大樓
- 商家場域 / 服務點
- 設備 / 設施

定位資料應使用：

- `coordinate_ref`
- `geometry_ref`
- `jurisdiction_ref`
- `statistic_ref`
- `evidence_ref`

不得在身份特徵封包內直接保存自然人、會員、住戶或家庭的精密座標。

Required static spatial invariants:

- `static_group_positioning_only=true`
- `personal_positioning_allowed=false`
- `contains_precise_person_location=false`
- `contains_member_plaintext=false`
- `requires_total_field_verify=true`

## Masking Definition

本系統對「遮罩」採用嚴格定義：遮罩後必須無法辨識個資。

若 payload 仍可辨識或重識別自然人、會員、住戶、家庭或個人精密位置，即不算遮罩資料，應視為個資明文或高風險個資。

Required masking invariants:

- `masking_definition=MASKED_DATA_IS_NON_IDENTIFIABLE_PERSONAL_DATA`
- `reidentification_possible=false`
- `masked_payload_can_identify_person=false`

## Aggregate Demographic Spatial Analysis

本會為社區公益服務、補助、照護、活動、災防與公共通知規劃，有職權知道轄區內不同區域的人口結構差異，例如：

- 哪個里高齡者較多
- 哪個里兒童較多
- 哪個里青年或年輕成人較多
- 哪個服務區需要更多長照、親子、青年、志工或災防資源

此權限定位為社區發展協會基於章程、主管機關治理、公益服務與居民保護目的所需的公共利益資料治理能力。本會不是商業資料變現機構；資料使用意圖是保護居民、安排服務、配置資源、保存社區公共資訊與降低風險。

此類資料應作為 `aggregate_demographic_context`，限於里級、服務區級或公開統計區層級，不得下鑽成可識別個人或家庭的標籤。

Allowed cohort buckets:

- `CHILDREN`
- `YOUTH`
- `YOUNG_ADULTS`
- `WORKING_AGE`
- `ELDERLY`
- `OLDER_ELDERLY`

Required aggregate demographic invariants:

- `aggregation_level=LI_LEVEL | SERVICE_AREA_LEVEL | PUBLIC_STATISTICAL_AREA`
- `ranking_allowed=true`
- `person_level_data_allowed=false`
- `household_level_data_allowed=false`
- `contains_member_plaintext=false`
- `reidentification_possible=false`
- `requires_total_field_verify=true`

## Base Identity Features

八維碼可標記基礎身份：

- 社區居民
- 非社區居民
- 社區商家
- 非社區商家
- 基礎個人身份
- 團體身份

These markers are expressed as refs and enums, not raw personal data.

## Merchant Feature Functions

商家特徵功能包含但不限於：

- 負責人
- 店長
- 店員
- 標籤會員
- 會員

商家角色不可單獨授權 POS 寫入、付款、正式通知或會員明文查詢。

## Property Feature Functions

物業特徵功能包含但不限於：

- 主委
- 副主委
- 財委
- 總幹事
- 區分所有權人
- 住戶
- 車輛種類
- 車輛顏色
- 各類設備
- 各類設施

車輛、設備、設施以 `asset_ref`、`vehicle_ref`、`equipment_ref`、`facility_ref` 表示，不保存車牌或住戶明文。

## Association Feature Functions

協會特徵功能包含但不限於：

- 創辦人（不可變更）
- 理事長
- 總幹事
- 副理事長
- 常務理事
- 理事
- 常務監事
- 監事
- 秘書
- 幹事
- 社團社員

協會角色標記不得自動代表簽章、付款、對外正式發文或資料庫寫入權限。

### Immutable Founder Marker

`ASSOCIATION_IMMUTABLE_FOUNDER` 是創辦人身份特徵標記，不是一般任期職務。它不可被理事長、總幹事、理監事、秘書、幹事或社團社員等可輪替職務覆蓋，也不可由一般 role update 自動刪除或改寫。

Required boundary:

- `immutable_founder_marker=true`
- `founder_marker_mutable=false`
- `role_rotation_can_override=false`
- `requires_total_field_verify=true`
- 只能保存 `founder_ref` / `evidence_ref`，不得保存創辦人姓名、電話、地址、身分證字號或任何會員明文

創辦人標記仍不得直接產生簽章、付款、對外正式發文、Odoo DB 寫入、secret read 或正式身份裁決。

## Packet Boundary

八維碼身份特徵封包只做：

- 標記候選身份特徵
- 綁定 subject / group / node / role refs
- 綁定靜態團體 / 場域 / 轄區 / 設備 / 設施的空間 ref
- 綁定里級或服務區級聚合人口統計 ref
- 提供服務路由、畫面、候選說明的上下文
- 交給總場驗證

不得做：

- final decision
- db write
- secret read
- member plaintext persist
- personal positioning
- precise member location persist
- reidentifiable masked payload
- payment execute
- formal send
- role elevation without verifier

## Final Rule

八維碼可標記個人、團體、社區、商家、物業、協會、不可變更創辦人、車輛、設備與設施特徵；也可為靜態團體、轄區、物業、商家場域、設備與設施建立空間定位 ref，並可承載里級或服務區級聚合人口統計 ref。標記只作候選服務路由、公益服務規劃與總場驗證前上下文，不是正式身份裁決，也不是個人定位系統。
