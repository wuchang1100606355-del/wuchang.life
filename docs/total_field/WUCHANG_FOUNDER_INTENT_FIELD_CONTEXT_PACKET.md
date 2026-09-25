# WUCHANG FOUNDER INTENT FIELD CONTEXT PACKET
# 五常創辦人意圖場脈絡封包

STATE: FOUNDER_CONTEXT_PACKET_CREATED
MODE: TOTAL_FIELD_CONTEXT
FINAL_AUTHORITY: OMEGA_GI_TOTAL_FIELD
AI_STATUS: CANDIDATE_ONLY
PRE_SEAL_POLICY: REPORT_ONLY

## 1. Purpose

本文件把創辦人脈絡收入總場，供總場與各分場理解「為什麼做、為誰做、哪些事情不能被 AI 或流程越權」。

本文件不是身份證明、不是會員資料庫、不是專利讓渡文件，也不是正式發布 seal。它是總場理解創辦人意圖、公益邊界、產品語氣、分場治理路由與「本源意圖場 8 維度空間封包拓樸圖」視覺語義的 context packet。

## 2. Founder Context Source

```text
FOUNDER_CONTEXT_SOURCE:
- web/founder_manifesto/index.html
- web/assets/homepage-intent-field-hero.png
- web/assets/homepage-intent-field-hero.webp
- docs/total_field/WUCHANG_FOUNDER_DONOR_ROLE_AND_PUBLIC_INTEREST_IP_BOUNDARY.md
- docs/total_field/W7TP_PROPERTY_ASSOCIATION_MERGE_RELATION_MAP.md
- docs/total_field/W7TP_XIAOJ_SERVICE_PERSONA_POLICY.md
- user_authorized_founder_manifesto_attachment
```

創辦人脈絡以 `founder_ref`、`evidence_ref`、`doc_ref`、`hash_ref` 方式進入總場。不得把私人記憶、會員明文、原始照護內容、金流資料或營業秘密規則表直接塞入分場。

## 3. Core Founder Narrative

創辦人不是大型資訊公司、不是高算力團隊，也不是靠資本堆 GPU 的雲端中心化路線。

核心背景：

- 14 年單品咖啡與在地服務經驗。
- 7 個月從基礎系統操作學起，逐步整理出 AI 賦能、社區服務、總場治理與產品頁落地。
- 技術目的不是炫技，而是把社區裡的人、服務、店家、長輩、公益與證據留痕放回同一個可審查場。
- 公益目標包含長輩早餐補助、在地店家受益、社區服務降低成本、使用者主權不被中心化平台抽走。

總場理解重點：

```text
FOUNDER_INTENT:
人主，不是 AI 主。
本地，不是雲端中心化剝削。
公益，不是純商業抽取。
候選，不是自動裁決。
證據，不是口號。
封裝前 report-only；封裝後才 strict enforcement。
```

## 4. Total Field Interpretation

總場應把創辦人理解為：

- 發明與系統設計之創作來源 ref。
- 公益落地、咖啡館測試場、協會服務場與社區總場之共同脈絡來源。
- 需要保留不可變創辦人標記的治理 ref。
- 不是可由 LLM、Odoo、分場角色、一般管理員或雲端 agent 取代的權威來源。

總場不得把創辦人脈絡降維成：

- 普通聊天機器人故事。
- 普通 ERP / Odoo 客製案。
- 普通公益網站文案。
- 普通 AI agent workflow。
- 普通 GPU 雲端推論服務。
- 單純個人經歷或情緒性敘事。

## 5. Branch Field Interpretation

### 5.1 Association Branch

協會分場可理解創辦人為公益服務與技術捐贈意圖來源，但不得因此自動核准補助、會員身份、職務升降、會務公告或正式對外文件。

Required routing:

```text
association_branch_output=candidate_only
formal_association_action_requires=human_confirm_ref + total_field_verify
role_conflict_disclosure_required=true
```

### 5.2 Property Branch

物業分場可理解創辦人提供社區總場設計、服務入口、修繕/住戶/公告候選整理方法，但不得因此讀取住戶明文、核准門禁、付款或角色升級。

Required routing:

```text
property_branch_output=candidate_only
resident_plaintext_read=false
access_or_payment_requires=human_confirm_ref + total_field_verify
```

### 5.3 Merchant Branch

商家分場可理解咖啡館為產品 proof-of-use 與公益商業灘頭堡。咖啡館營收、POS、Odoo、會員體驗與公益基金邏輯可作測試脈絡，但不得與協會非營利資源、會員資料或正式金流混同。

Required routing:

```text
merchant_branch_output=candidate_only
private_commerce_nonprofit_resource_mix=false
payment_execution_requires=owner_seal + total_field_verify
```

### 5.4 Product / Web Branch

產品頁、招募頁、展示頁與本機候選落地在封裝前採 `ALLOW_BY_DEFAULT_WITH_REPORT_ONLY_WARNINGS`。未落地安全規則不得阻擋 owner-authorized development。

Hard HOLD only when:

```text
live_db_write
payment_execution
formal_send
role_elevation
deploy_restart_push
TIPO_submission
third_party_data_exposure_without_owner_authorization
secret_rule_leakage_without_owner_intent
authority_drift
```

## 6. Machine-Readable Context Contract

```json
{
  "packet_id": "WUCHANG_FOUNDER_INTENT_FIELD_CONTEXT_PACKET",
  "state": "FOUNDER_CONTEXT_PACKET_CREATED",
  "authority": "OMEGA_GI_TOTAL_FIELD",
  "ai_status": "CANDIDATE_ONLY",
  "pre_seal_policy": "REPORT_ONLY",
  "founder_context": {
    "role": [
      "technical_developer",
      "technical_donor",
      "community_public_interest_operator"
    ],
    "narrative": [
      "14_year_single_origin_coffee_service",
      "7_month_ai_enabled_self_build_path",
      "community_total_field_public_interest_orientation",
      "elder_breakfast_subsidy_and_local_merchant_support"
    ],
    "must_not_reduce_to": [
      "generic_chatbot",
      "generic_erp_customization",
      "generic_ai_agent_workflow",
      "gpu_cloud_inference_service"
    ]
  },
  "branch_rules": {
    "association": "candidate_only_human_confirm_required",
    "property": "candidate_only_no_plaintext_no_access_grant",
    "merchant": "candidate_only_no_nonprofit_commerce_mix",
    "product_web": "pre_seal_allow_owner_authorized_public_pages_report_only"
  },
  "output_gate": {
    "db_write": "HOLD",
    "deploy": "HOLD",
    "payment": "HOLD",
    "formal_send": "HOLD",
    "role_elevation": "HOLD",
    "public_page_candidate": "ALLOW_PRE_SEAL_REPORT_ONLY"
  }
}
```

## 7. Red Team Notes

本封包可以協助總場與分場理解創辦人，但不得被誤用為：

- 專利新穎性或進步性唯一證明。
- 對外宣稱已正式上線或已完成公益金融平台。
- 對外宣稱 Google、Microsoft 或大型資訊業已背書。
- 會員明文、住戶明文、照護內容、付款內容或營業秘密規則的承載容器。
- AI 自動核准、AI 自動送件、AI 自動付款或 AI 自動角色升級的權限來源。

## 8. Launch State

FOUNDER_CONTEXT_PACKET_CREATED: TRUE
FOUNDER_CONTEXT_SOURCE_RECORDED: TRUE
TOTAL_FIELD_BRANCH_COMPREHENSION_ENABLED: TRUE
PRE_SEAL_REPORT_ONLY_RECORDED: TRUE
STRICT_ENFORCEMENT_AFTER_OWNER_SEAL_ONLY: TRUE
AI_CANDIDATE_ONLY: TRUE
NO_SECRET_RULE_DISCLOSURE: TRUE
NO_MEMBER_PLAINTEXT: TRUE
NO_PRODUCTION_RELEASE: TRUE
NO_TIPO_SUBMISSION: TRUE

FINAL_DECISION: FOUNDER_CONTEXT_ACCEPTED_AS_TOTAL_FIELD_CONTEXT_PACKET
