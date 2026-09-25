# XiaoJ Browser Packaged Pages

STATE=BROWSER_PACKAGED_APP_PATCH_READY
ROUTE=/wuchang/xiaoj/ordering

This patch adds an Odoo-integrated browser-packaged app shell. It is served by `wuchang_core` and can be wrapped by browser kiosk, WebView, Chrome app mode, or a PWA-style shortcut.

It is not a sidecar, not a standalone server, and not a fake Odoo page.

## Pages

- `staff_pos`: 店員 POS.
- `counter_service_touch`: 櫃台客戶服務觸控頁面.
- `av_ai_menu_display`: 影音 AI 影像菜單顯示場.
- `business_management`: 商業管理分級子功能頁.
- `hardware_menu_business_settings`: 硬體菜單設定營業資訊頁面.

## Customer Display Ticker

The AV menu display page includes two customer-display ticker bands:

- Top ticker: announcements, promotions, group member QR reminders, local verification notices.
- Bottom ticker: candidate order summary, queue prompt, maintenance notice, formal gate warning.

Ticker content is display-only candidate information. It does not trigger formal POS write, payment capture, member plaintext lookup, service restart, or deploy.

## XiaoJ VRM Customer Display Slot

The AV menu display page now reserves a XiaoJ VRM asset slot for the large menu display and customer-facing display machine.

- Avatar file: `lung.vrm`
- Static path: `/wuchang_core/static/src/xiaoj_ordering/avatar/lung.vrm`
- Display mode: `customer_menu_display`
- State: `VRM_ASSET_SLOT_READY`

The slot is display-only. Loading the avatar asset does not trigger formal POS write, payment capture, member plaintext lookup, service restart, or deploy.

## Files

- Controller: `Taiji_Odoo/addons/wuchang_core/controllers/xiaoj_ordering_app_controller.py`
- HTML shell route: `/wuchang/xiaoj/ordering`
- Static app: `Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.js`
- CSS: `Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.css`
- Browser manifest: `Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering.webmanifest`
- Avatar directory: `Taiji_Odoo/addons/wuchang_core/static/src/xiaoj_ordering/avatar/`

## Safety

- `FORMAL_DB_WRITE=FALSE`
- `FORMAL_POS_WRITE=FALSE`
- `PAYMENT_CAPTURE=FALSE`
- `SERVICE_RESTART=FALSE`
- `DEPLOY=FALSE`
- `PRODUCTION_RELEASE=FALSE`
- `SECRET_READ=FALSE`
- `MEMBER_PLAINTEXT_READ=FALSE`

## Next Safe Action

Operator review, then Odoo module upgrade only if explicitly authorized.
