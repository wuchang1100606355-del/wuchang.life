# Gemini Single Product Prompt

STATE=GEMINI_SINGLE_PRODUCT_PROMPT_READY
STYLE_ID=LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1
SAME_STYLE_DIFFERENT_ITEMS_REQUIRED=TRUE
ANGLE_VARIATION_ALLOWED=TRUE
GOOGLE_ACCOUNT_ACTION=USER_MANUAL_ONLY
GOOGLE_API_CALL=FALSE
GENERATED_IMAGE_IS_PRODUCT_EVIDENCE=FALSE

## 使用方式

把下面整段貼給 Gemini。每次只改 `品名`、`shot_type`、`角度` 三欄，一次只生成一張。

## 單張出圖提示語

```text
請依照固定風格鎖生成一張上品聊國重新總店產品寫真集等級圖片。

品名：{請填品名}
shot_type：hero_product
角度：front_45_degree

固定風格鎖：
STYLE_ID=LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1
85mm lens look, commercial food photography, shallow depth of field, crisp product edge
single large softbox from upper left plus subtle warm fill, consistent soft shadow direction
matte warm gray stone tabletop, soft dark cafe background, no visible brand logo
warm neutral cafe palette, cream highlights, charcoal shadow, restrained amber accent
consistent product scale and clean negative space for menu layout; shot angle may vary by item and shot type
photorealistic, high resolution, natural texture, product photobook editorial consistency

一致性規則：
Keep lighting system, background material, color palette, lens language, shadow softness, product scale, and editorial finish consistent across all menu items; the shot angle may vary by item and shot type.

角度可選：
- front_45_degree：45 度正面英雄角，適合主產品圖
- top_down_30_degree：近似俯視 30 度，適合菜單格狀縮圖
- macro_detail_low_angle：低角度或微距特寫，適合質地細節
- menu_grid_centered：置中留白，適合待機菜單牆

輸出要求：
- 產品寫真集等級，PHOTOBOOK_PRODUCT_GRADE
- 同一系列視覺，不可改變攝影棚背景、光線方向、色彩基調、鏡頭語彙
- 可依品項與 shot_type 變換角度
- 不要出現文字、Logo、QR code、人臉、錯字
- 不要低解析、不要塑膠假食物質感、不要過度卡通化
- 生成圖只是候選素材，不得宣稱為真實實拍
```

## 可用真實菜單品名

- 紅茶 / DR_RED_TEA / 飲料類 / TWD 30
- 綠茶 / DR_GREEN_TEA / 飲料類 / TWD 30
- 煎餃 / FO_C_DUMPLING / 中式餐點類 / TWD 30
- 蘿蔔糕 / FO_C_RADISH / 中式餐點類 / TWD 30
- 漢堡 / FO_W_BURGER / 西式餐點類 / TWD 30
- 漢堡加蛋 / FO_W_BURGER_EGG / 西式餐點類 / TWD 40
- 總匯三明治 / FO_W_CLUB / 西式餐點類 / TWD 45
- 中式套餐 / SET_CHI_60 / 套餐類 / TWD 60
- 西式套餐 / SET_WES_60 / 套餐類 / TWD 60
- 豆漿 / ODOO_PROD_SOY_MILK / 早餐 / TWD 25
- 蛋餅 / ODOO_PROD_EGG_PANCAKE / 早餐 / TWD 40
- 皮蛋瘦肉粥 / ODOO_PROD_CONGEE / 早餐 / TWD 65
- 烤肉串 / ODOO_PROD_BBQ_SKEWER / 燒烤 / TWD 90
- 烤牛舌 / ODOO_PROD_BBQ_BEEF_TONGUE / 燒烤 / TWD 180
- 碳烤雞翅 / ODOO_PROD_BBQ_WINGS / 燒烤 / TWD 120
- 拿鐵 / ODOO_PROD_COFFEE_LATTE / 咖啡 / TWD 80
- 美式咖啡 / ODOO_PROD_COFFEE_AMERICANO / 咖啡 / TWD 60
- 卡布奇諾 / ODOO_PROD_COFFEE_CAPPUCCINO / 咖啡 / TWD 85
- 摩卡 / ODOO_PROD_COFFEE_MOCHA / 咖啡 / TWD 95
- 焦糖瑪奇朵 / ODOO_PROD_COFFEE_CARAMEL_MACCHIATO / 咖啡 / TWD 100
- 手沖咖啡 / ODOO_PROD_COFFEE_POUR_OVER / 咖啡 / TWD 90
- 冷萃咖啡 / ODOO_PROD_COFFEE_COLD_BREW / 咖啡 / TWD 90
- 馥芮白 / ODOO_PROD_COFFEE_FLAT_WHITE / 咖啡 / TWD 85
- 榛果拿鐵 / ODOO_PROD_COFFEE_HAZELNUT_LATTE / 咖啡 / TWD 95
- 黑糖拿鐵 / ODOO_PROD_COFFEE_BROWN_SUGAR_LATTE / 咖啡 / TWD 95
