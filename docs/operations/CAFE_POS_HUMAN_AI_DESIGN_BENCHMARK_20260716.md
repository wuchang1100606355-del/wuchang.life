# 咖啡館 POS 人類與 AI 共用操作基準

## 範圍與證據

本基準只研究主要 POS 官方文件中可驗證的操作模式，不複製任一廠商介面，也不把第三方評論當產品事實。目標是讓「聊閣社區咖啡重新店-QC」來源菜單可由人員快速操作，也可讓裝置端 AI 產生可覆核候選。

本次檢視的官方來源：

- Square：商品可綁定 modifier set，規則可指定必填、單選／複選、最少／最多數量與價差；題組順序可依商品調整，Restaurant POS 另提供 Add／No／Extra 的 conversational modifiers。<https://squareup.com/help/us/en/article/5119-create-and-manage-item-modifiers>
- Toast：required modifier 未選完前不得送單；optional 題組可設定 POS prompt；required 題組在 POS 流程優先出現。<https://central.toasttab.com/articles/Knowledge/Creating-Modifier-Groups-and-Modifiers-1492803987509>、<https://central.toasttab.com/articles/Knowledge/Advanced-Modifier-Configuration>
- Lightspeed Restaurant：modifier 在群組內可排序，排序會決定 Restaurant POS 的顯示順序。<https://resto-support.lightspeedhq.com/hc/en-us/articles/226404688-Sorting-modifiers>
- Shopify POS：以可自訂 smart grid 提供快速入口；離線結帳必須清楚顯示連線狀態、權限與主管核准，回線後再同步訂單與庫存。<https://help.shopify.com/en/manual/sell-in-person/getting-started/smart-grid>、<https://help.shopify.com/en/manual/sell-in-person/shopify-pos/selling-offline/offline-checkout>
- Clover：商品、分類、modifier group 與 modifier 分層管理；modifier 應先與商品關聯，再作為 line item modification 加入訂單，避免 AI 直接創造不存在的選項。<https://docs.clover.com/dev/docs/working-with-inventory>、<https://docs.clover.com/dev/docs/creating-custom-orders>

## 可直接採用的共同模式

1. 商品先由「分類＋大觸控按鈕」進入，搜尋或 AI 只作另一個入口，兩者共用同一份來源資料。
2. 點商品後只顯示該商品綁定的題組；必填題組未完成時，不得加入候選單。
3. 題組按人員說話與製作順序呈現：尺寸 → 溫度 → 甜度 → 口味／其他加購。來源未提供的題目不得補造。
4. 每個選項在按鈕上同時顯示名稱與價差；負價差與零價差不可隱藏。
5. 候選單逐行重述「商品、選項、數量、單價與小計」，修改後使舊雜湊與舊覆核失效。
6. 離線、回線待重驗、來源告警與主管權限必須是常駐狀態，不藏在設定頁。
7. AI 僅能把自然語句對應到來源商品與來源選項；遇到同名商品、缺少必填選項或無法辨識時，明確要求人員補選。
8. AI 不得自動送單、付款、改價或建立新商品；產出始終是可見、可改、可拒絕的 L3 候選。
9. 每一個來源 SKU 只呈現一張商品卡；尺寸、溫度、甜度、口味與加購都留在商品下方，不複製成另一個商品。

## 本案人類流程

`服務方式 → 分類 → 商品 → 來源綁定題組 → 加入候選 → 逐行覆誦 → 8D 候選 → 店員覆核 → 合成佇列`

- 沒有選項的商品可直接加入。
- 有必填選項的商品先進入設定面板，完成後才加入。
- 相同商品但不同選項必須是不同候選列；完全相同才合併數量。
- 正式訂單、金流、發票與 production DB 寫入仍維持關閉。

## 本案 AI 流程

`裝置端語句 → 精確商品比對 → 來源題組比對 → 顯示已辨識／未辨識 → 人員補選 → 人員確認加入`

- 自然語句解析使用裝置端確定性規則，伺服器不執行 LLM。
- 同名商品必須用分類或商品代碼消歧，不能由模型猜測。
- 大／中／小杯可映射到來源的 L／M／S，但畫面仍顯示來源選項值。
- AI 填完也不自動加入；「確認加入候選」是獨立的人類動作。

## 分類與啟用策略

來源分類整合為 5 大操作類：

```python
MAJOR_CATEGORIES = [
    {"id": "coffee", "label": "咖啡飲品"},
    {"id": "tea-other", "label": "茶與無咖啡因"},
    {"id": "food", "label": "餐食與點心"},
    {"id": "beans", "label": "咖啡豆"},
    {"id": "drip", "label": "濾掛咖啡"},
]
SOURCE_CATEGORY_TO_MAJOR = {
    "義式咖啡": "coffee",
    "單品手沖": "coffee",
    "聊國簡餐": "food",
    "茶": "tea-other",
    "無咖啡因": "tea-other",
    "點心": "food",
    "咖啡豆": "beans",
    "濾掛咖啡": "drip",
}
```

- 「咖啡飲品」在商品卡上繼續顯示「義式咖啡／單品手沖」原始細分類。
- 「濾掛咖啡」保留於分類規格與原始證據，但 6 項商品依創辦人商品策略暫停販售；人類與 AI 都不能加入候選。
- 因此來源總數為 64，公開啟用商品為 58。

## 員工、AI 與共用產出

- 人類端契約為 Odoo；目前公開頁是 `ODOO_IMPORT_PREVIEW_ONLY`，不假裝已寫入正式 Odoo POS。
- AI 端契約為 ADI；目前只使用由來源 SHA 綁定的 `DEMO_FIXED_CANDIDATE_ONLY` reference set，production ADI 維持 `HOLD_ADI_NOT_CONFIGURED`。
- LLM 只准在使用者設備執行；taiji01 守門固定回 `HOLD_USER_DEVICE_LLM_REQUIRED`，伺服器不載入模型、不接收原始提示。
- `cafe-pos-staff-flow.js` 承載共用總場整流器：驗證來源商品／題目／選項，產生標準化選項、價差、單價與 line key。
- `cafe-pos-ai-intent.js` 只能從 ADI 候選 reference set 查找，再輸出商品 ID 與來源選項 ID；不操作購物車。
- `cafe-pos-demo.js`：Odoo 人類點選與 ADI AI 填入都必須呼叫同一個 `normalizeConfiguration`，通過後才可形成相同格式的 L3 候選列。
- Odoo、ADI 與總場整流器分離維護；Odoo 與 ADI 不得各自計價、繞過來源選項驗證或自行形成 D8。

## ADI 與 8D 的責任分離

- 商品識別使用 QuickClick menu ID、SKU、source product ID 與來源 SHA-256；不另造一套 8D 商品碼。
- ADI 展示只提供不透明、版本化且有來源 SHA 證據綁定的固定候選 reference set；正式 production mapping contract 未完成前維持 `HOLD_ADI_NOT_CONFIGURED`。
- 同名商品先以來源 ref／SKU 消歧，中文名稱只作顯示與輔助比對。
- 選項座標使用完整的「來源 ref／題目／選項」路徑。QuickClick 的 `QC_OI` 因存在跨名稱重用，只保留作來源追溯，不能單獨當 AI 主鍵。
- 8D 保留給整筆訂單 L3 候選封套與人工 D8 覆核，不取代 ADI，也不重複建立商品資料庫。

## QuickClick 來源治理

- 原始 XLSX 兩份雲端候選的 SHA-256 均為 `18798f9fe998b68bbe1ff168110ef2521c03404ff0950730b729823e13086109`。
- 權威匯出含 64 項商品、21 個選項組及 242 筆原始選項列。
- 來源存在選項代碼跨名稱重用與重複語意列。總場保留原始檔與告警，不修改來源；公開操作層以「題目、選項文字、價差、子選單」作語意鍵去重，得到 212 個可操作選項。
- QuickClick 代碼只作來源追溯，不作畫面上唯一的人類識別，也不作 AI 自動送單依據。
