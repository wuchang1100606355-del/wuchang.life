# Cafe Real Menu Only POS Human UX Review

## State

```text
STATE=FIELD_OBSERVED_TOTAL_FIELD_QUERIED
TASK=CAFE_REAL_MENU_ONLY_AND_HUMAN_POS_UX_REVIEW
POS_DB_WRITE_THIS_RUN=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
```

## Observed Menu Authority

Human-provided QuickClick screenshot rows are the current practical menu
authority for XiaoJ shadow configuration:

| ID | Product Code | Name | Category | Add-on Menu |
| --- | --- | --- | --- | --- |
| 49180031 | QC_P_39095596 | 招牌咖啡 | 義式咖啡 | 尺寸(30)+溫度+甜度 |
| 49180033 | QC_P_49180033 | 小沙彌素齋飯 | 聊國簡餐 | 定食飲料 |
| 49180034 | QC_P_39095604 | 耶加雪夫 | 單品手沖 | 手沖溫控方式 |
| 49180035 | QC_P_39095628 | 黃金曼特寧 | 濾掛咖啡 | 無 |
| 49180036 | QC_P_39095624 | 耶加雪夫 | 咖啡豆 | 黃金曼特寧+耶加雪夫 |
| 49180038 | QC_P_39095611 | 檸檬汁 | 無咖啡因 | 尺寸(10)+溫度+甜度 |

The following are not accepted as active menu examples:

```text
美式咖啡
拿鐵
卡布奇諾
紅茶
早餐套餐
三明治
蛋餅
```

## Human POS Usability Review

The current QuickClick backend menu-management screen is suitable for
administration, but it is not a good rush-hour cashier ordering surface.

Human concerns:

- Rows are dense and text wraps vertically, making item recognition slow.
- Action buttons are small and repeated per row, increasing accidental clicks.
- The sidebar consumes space and visually competes with the product table.
- Categories, add-on menus, and products are displayed as backend management
  fields rather than cashier-first choices.
- Price authority is not visible in the captured rows, so XiaoJ must not infer
  prices from memory or example data.

Recommended cashier-facing layout:

| Zone | Human Purpose | Suggested Form |
| --- | --- | --- |
| Category rail | Pick drink/meal type quickly | Large buttons: 義式咖啡, 聊國簡餐, 單品手沖, 濾掛咖啡, 咖啡豆, 無咖啡因 |
| Product grid | Tap actual menu item | Large cards with name, category, price, photo/icon if available |
| Option panel | Pick size/temp/sweetness/add-on | Step-by-step buttons matching the product's add-on menu |
| Candidate bar | Prevent wrong orders | Big repeat line: `大杯 / 冰 / 少糖 / 招牌咖啡` |
| Manager actions | Avoid accidental operations | Separate locked area for refund, price change, void |
| Language helper | Support Vietnamese manager | Chinese + Vietnamese labels on confirmation and manager prompts |

## XiaoJ Configuration Result

Local shadow resources now use the QuickClick screenshot rows only:

```text
runtime/xiaoj_practicum/av_model/menu_lexicon.json
runtime/xiaoj_practicum/p0_shadow_rehearsal/p0_shadow_menu_refs.json
runtime/xiaoj_practicum/p0_shadow_rehearsal/sample_candidate_order.json
runtime/xiaoj_practicum/p0_shadow_rehearsal/training_candidates.jsonl
```

No Odoo/POS database write was performed in this review.

## Next Safe Action

To actually delete or disable backend/POS products, provide a release packet
that explicitly authorizes Odoo/POS menu write, plus either:

- Full QuickClick menu export with prices and all pages, or
- Complete page-by-page screenshots including prices and all rows.
