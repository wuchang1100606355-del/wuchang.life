# 品牌、商業主體與公益主體映射

版本：2026-05-12

## 狀態

```text
ACTIVE_GOVERNANCE_MAPPING_ONLY
```

此文件只建立治理映射，不直接修改 Odoo production、Google Business Profile、商業登記或協會登記資料。

## 商業品牌與實際主體

| Field | Value | Status |
|---|---|---|
| 品牌 / 場景名稱 | 聊國咖啡館重新店 | user-provided |
| 實際商業主體 | 上品食品行 | user-confirmed; public-source conflict requires official check |
| 統一編號 | 34778660 | corrected by user; previous `34775660` was a typo |
| 地址 | 新北市三重區重新路三段204號1樓 | public-source-supported |
| Google 商家檔案 | 聊國咖啡館重新店 / 總店 Google 商家檔案 URL | user-confirmed as store/main-store public profile |

## 公益治理主體

| Field | Value | Status |
|---|---|---|
| 名稱 | 新北市三重區五常社區發展協會 | user-provided and public-source-supported as community association name |
| 會址 | 新北市三重區五常里28鄰仁義街161號一樓 | user-provided, needs official-source confirmation |
| 所轄範圍 | 新北市三重區五常里、仁忠里、五順里 | user-provided; public source observed 五常、仁忠、五順 and also mentions 五福 in one statistical table, needs final official confirmation |
| Google 商家檔案 | 五常智慧社區雲 / 協會所屬 Google 商家檔案 URL | user-confirmed as association-owned public profile |

## Google 商家檔案分窗

| Profile | Owner Window | Role |
|---|---|---|
| 聊國咖啡館重新店 / 總店 | 上品食品行 / 聊國咖啡館重新店 | commercial main-store / developer vendor profile |
| 五常智慧社區雲 | 新北市三重區五常社區發展協會 | association public-interest profile |

## 登記號衝突

```yaml
previous_association_registration_id: 新北市社區補字第1100606355號
business_tax_id_active: 34778660
business_tax_id_typo_retracted: 34775660
decision: active_business_tax_id_corrected_to_34778660
risk_level: L1_near
```

`34778660` 依使用者更正作為上品食品行 / 聊國咖啡館重新店統一編號。`34775660` 已標記為筆誤，不作為 active mapping。

## Odoo Representation

```yaml
odoo_mapping:
  public_interest_controller:
    name: 新北市三重區五常社區發展協會
    role: odoo_main_company / main_public_interest_governance_entity
  commercial_business_entity:
    name: 上品食品行
    tax_id: "34778660"
    role: developer_vendor / cooperation_contractor / technology_transferor
  brand_scene:
    name: 聊國咖啡館重新店
    role: brand_scene_for_pos_service_development_and_technology_transfer
```

## Boundary

- 品牌不等於公益主體。
- 上品食品行不等於協會控制者。
- 協會公益資產、資料、基金池不可與私人商業帳務混同。
- 協會為 Odoo 主公司。
- 聊國咖啡館重新店 / 上品食品行為開發商、協力廠商、技術轉移者。
- 聊國咖啡館重新店可作為 POS/場景實作、技術支援、設備借用或社區產業合作節點。
- Odoo 中須以 company / branch / customer / service node / sponsor role 分窗表示。

## Sources

- User-provided Google business profile/search URLs.
- User clarification: 五常智慧社區雲 Google 商家檔案屬於協會。
- User clarification: 先前貼入的 Google 商家檔案共有兩個，其中一個為聊國咖啡館總店/重新店商家檔案。
- User correction: 協會為 Odoo 主公司；聊國咖啡館重新店為開發商協力廠商與技術轉移者。
- User correction: `34775660` 為筆誤，`34778660` 才是上品食品行 / 聊國咖啡館重新店之統一編號。
- Public web search result for 三重區統計資料 listing 五常社區發展協會.

## Five-Metric Code

```yaml
intent: business_public_interest_subject_separation
resource: brand_legal_entity_association_metadata
time: development_pre_live_odoo_mutation
authority: human_confirmed_mapping_with_conflict_marker
topology: odoo_identity_model_pos_brand_public_interest_governance
```
