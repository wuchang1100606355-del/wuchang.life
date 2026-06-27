# XiaoJ AV Ordering Market Competitiveness And Stickiness Packet

RUN_ID=D8_MANDATORY_TASK_20260624_082258_XIAOJ_AV_ORDERING_MARKET_COMPETITIVENESS_STICKINESS_TOTAL_FIELD_CONSULT
STATE=MARKET_COMPETITIVENESS_STICKINESS_PACKET_READY
ROOT=/home/taiji_admin/Taiji_Hub

## Product Intent

Build XiaoJ as the cafe-facing audio/video AI ordering product:

- cloud compute contributes candidate labor only
- local model and local brain keep authority
- one visible XiaoJ identity handles multi-intent work
- XiaoJ is lively, accurate, useful, and lightly funny
- LINE and Google registration/login must work before launch claims
- the product must compete on market value and customer stickiness, not only internal governance

## Market Reality From Total Field And Public References

| Market Pattern | Evidence | XiaoJ Response |
| --- | --- | --- |
| POS already has restaurant workflows | Odoo POS supports restaurant tables, orders, bills, tips, kitchen/bar notification, and takeout tax handling. Odoo also documents self-ordering and preparation display flows. | XiaoJ must not pretend to replace POS. It must become the trustworthy AI layer above Odoo/POS. |
| Competitors sell continuity | Toast documents offline mode and KDS/local sync behavior; Lightspeed and SpotOn also position offline operation as continuity. | XiaoJ must show local reconstruction, local queue, and evidence replay when cloud/network is degraded. |
| Competitors sell KDS and speed | Square KDS and Odoo preparation display emphasize front/back-of-house order visibility and prep flow. | XiaoJ must make order candidates clear for cashier, kitchen, and customer display without silently creating orders. |
| Competitors sell self-ordering | Odoo and Square both offer self-order/kiosk patterns. | XiaoJ must be more personal: image menu, voice guidance, bilingual assist, staff-confirmed candidate flow. |
| Competitors sell loyalty | Odoo loyalty/discount docs include coupons, loyalty cards, and promotions; Square and Toast market loyalty enrollment, points, rewards, and repeat visits. | XiaoJ must bind membership, repeat-visit memory refs, rewards, feedback, and community story without reading member plaintext. |

Public reference links used for market check:

- Odoo POS: https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale.html
- Odoo restaurant POS: https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/restaurant.html
- Odoo self-ordering: https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/extra/self_order.html
- Odoo preparation display: https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/extra/preparation.html
- Odoo loyalty and discounts: https://www.odoo.com/documentation/19.0/applications/sales/sales/products_prices/loyalty_discount.html
- Toast offline mode: https://support.toasttab.com/en/article/Using-Toast-in-Offline-Mode
- Toast local sync: https://doc.toasttab.com/doc/platformguide/platformOfflineModeLocalSync.html
- Toast loyalty: https://support.toasttab.com/en/article/Getting-Started-Toast-Loyalty
- Square KDS: https://squareup.com/us/en/point-of-sale/restaurants/kitchen-display-system
- Square kiosk: https://squareup.com/us/en/hardware/kiosk
- Square loyalty: https://squareup.com/us/en/software/loyalty
- Lightspeed offline mode: https://x-series-support.lightspeedhq.com/hc/en-us/articles/25534272395163-Selling-in-offline-mode

## Competitive Product Position

Do not sell XiaoJ as:

- a normal POS
- a normal chatbot
- a fake demo page
- a payment system
- a generic AI waiter
- a replacement for Odoo, Toast, Square, or QuickClick

Sell XiaoJ as:

```text
本地主權影音 AI 點餐與店務確認層：
AI 可以聽、看、整理、翻譯、提醒、開玩笑、做候選單，
但正式 POS、付款、會員與帳務都要經本地驗證與人員確認。
```

## Strongest Differentiators

| Differentiator | Why It Matters To Store | Proof Needed |
| --- | --- | --- |
| No blind AI write | 店長不用怕 AI 亂下單、亂改價、亂收款 | Candidate-only order flow verifier |
| One XiaoJ identity | 顧客和店員看到的是同一個小J，不是多個工具拼起來 | Local brain route with front persona |
| Real menu only | 防止 GPT 亂編商品，保住店內信任 | QuickClick/Odoo verified menu source hash |
| Audio/video ordering | 顧客看圖、聽小J、店員確認，降低點餐摩擦 | `/wuchang/xiaoj/ordering` authenticated UI |
| Bilingual manager mode | 越南店長能直接操作、確認、退單、改價 | Chinese/Vietnamese labels and confirmation flow |
| Member sticky loop | LINE/Google 註冊後能帶回訪、點數、偏好、公益故事 | Non-404 auth routes plus opaque member refs |
| Local continuity | 網路/雲端不穩時仍可本地整理候選、留證、恢復 | degraded-mode demo |
| Evidence-backed humor | 小J可以有笑點，但不亂承諾、不亂收款、不亂報菜 | persona guard tests |
| Community mission | 重新店營運支持協會數位公益，顧客消費有故事 | homepage/pilot copy with accounting separation |

## Customer Stickiness Loop

| Step | Customer Feeling | System Behavior | Guard |
| --- | --- | --- | --- |
| 1. Notice | 看到真照片/菜單/小J，覺得有趣 | AV menu display shows real products and XiaoJ prompt | Real menu source required |
| 2. Join | 用 LINE/Google/Odoo signup 進入會員 | Login/register creates opaque refs | No member plaintext exposure |
| 3. Order | 說話或點圖，小J整理候選單 | Multi-intent parser builds order candidate | No POS order yet |
| 4. Confirm | 店員/店長下拉確認、改價、退單 | Staff sees diff and confirms candidate | Human gate |
| 5. Reward | 得到點數、券、熟客稱呼、公益提示 | Loyalty/referral candidate emitted | No automatic accounting |
| 6. Remember | 下次回來，小J記得偏好但不暴露個資 | preference_ref / favorite_ref only | No plaintext memory |
| 7. Return | 生日、集點、越文提醒、公益活動帶回訪 | LINE/Google channel candidates | No external send without approval |
| 8. Advocate | 客人分享「會記得我、會講話、但很安全」 | referral/story card candidate | Human-approved copy |

## Must-Have Product Features

### A. Audio/Video Ordering

- real product photos
- category table
- size, temperature, sweetness, bean, meal/add-on choices
- voice input candidate
- touch fallback
- staff confirmation panel
- customer display summary
- kitchen/counter display candidate

### B. Multi-Intent Local Brain

- order intent
- menu question intent
- refund/cancel/price-change intent
- staff permission intent
- member registration intent
- loyalty/reward intent
- vendor/cash-advance evidence intent
- humor/small-talk intent
- HOLD intent for unsafe requests

### C. XiaoJ Personality

Tone rules:

- warm, lively, concise
- light humor only after task clarity
- never joke about payment, allergy, member data, or price authority
- Vietnamese manager mode must be clear and practical
- customer-facing voice must be friendly but not overpromise

Example safe style:

```text
我先幫你整理成候選單，店長確認後才會進 POS。
今天想喝熱的還是冰的？小J不搶收銀機，這點我很乖。
```

### D. LINE / Google Registration Login

Launch requirement:

- `/line/login` must be non-404 or controlled HOLD page
- `/line/callback` must be non-404 or controlled HOLD page
- `/google/member/login` must be non-404 or controlled HOLD page
- `/google/member/welcome` must be non-404 or controlled HOLD page
- `/wuchang/member/register/start` must be non-404 or controlled HOLD page
- `/web/signup` must remain 200

No OAuth secret value may be read or printed in this work.

### E. Loyalty And Retention

Candidate features:

- visit stamp candidate
- points/reward candidate
- birthday/monthly return reminder candidate
- favorite drink ref
- language preference ref
- staff note ref
- referral card candidate
- community support story card
- "today's familiar customer" display for staff only through masked refs

Forbidden until approved:

- automatic coupon issuance
- automatic LINE push
- automatic payment discount
- member plaintext lookup
- direct accounting write

## Market Gate

The product cannot claim strong market competitiveness until these are proven:

| Gate | Required Proof | Current Status |
| --- | --- | --- |
| Auth gate | LINE/Google/member routes non-404 or controlled HOLD | FAIL_RUNTIME_404 |
| Menu truth gate | Real QuickClick/Odoo source locked | HOLD_MENU_SOURCE_REQUIRED |
| AV UI gate | Authenticated `/wuchang/xiaoj/ordering` product UI tested | PARTIAL |
| Local brain gate | Front persona model connected with local route | PARTIAL |
| Candidate order gate | Candidate API validates menu/price/add-ons without POS write | NOT_PROVEN |
| Staff confirm gate | Busy-counter dropdown confirm/edit/cancel flow | NOT_PROVEN |
| Loyalty gate | Opaque-ref reward loop designed and testable | NOT_PROVEN |
| Bilingual gate | Chinese/Vietnamese manager UX verified | NOT_PROVEN |
| Continuity gate | Degraded network/local queue demo | NOT_PROVEN |
| ROI gate | repeat visit, confirm time, avoided wrong-order metrics | NOT_PROVEN |

## P1 Implementation Recommendation

Next task:

`XIAOJ_AV_ORDERING_AUTH_AND_STICKINESS_LAND_P1`

P1 target:

1. Make LINE/Google/member registration routes non-404 or controlled HOLD without reading secrets.
2. Surface `/wuchang/xiaoj/ordering` as a product-grade authenticated staff/customer display shell.
3. Add candidate-only local operation registry for menu browse, order candidate, validate, confirm dry-run, voice say, display render, loyalty candidate, and evidence seal.
4. Add Chinese/Vietnamese/English label contract.
5. Add persona guard tests for lively, accurate, light-humor XiaoJ.
6. Add retention metric schema without member plaintext.

## Stopline

If any implementation or copy claims the following before proof, stop:

```text
STATE=HOLD_PRODUCT_MARKET_OVERCLAIM
```

Stop claims:

- LINE/Google login works while runtime returns 404
- AI creates formal POS orders
- AI captures payment
- AI reads member plaintext
- menu is final without QuickClick/Odoo source lock
- customer retention is strongest without measured proof
- production release is ready

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
D8_LOCAL_DB_WRITE=TRUE
PRODUCTION_DB_WRITE=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE
PUBLIC_WEB_RESEARCH=TRUE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
ODOO_FILES_TOUCHED=FALSE
LINE_LOGIN_FILES_TOUCHED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
