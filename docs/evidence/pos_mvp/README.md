# POS MVP Sandbox Evidence

STATE=POS_MVP_SANDBOX_AUTODEV
RUN_ID=POS_MVP_SANDBOX_AUTODEV_REAL_MENU_20260621
AUTHORITY=taiji01 Total Field

FACT: Sandbox menu must be generated from repo-local Odoo XML evidence.

FACT: Menu source files are:
- `Taiji_Odoo/addons/wuchang_core/data/breakfast_pos_menu.xml`
- `Taiji_Odoo/addons/wuchang_core/data/menu_setup.xml`

FACT: Runtime menu state must be `REAL_MENU_FROM_REPO_ODOO_XML`.

FACT: External mother file is known to be incorrect for this pass and must not be used as authority.

FACT: No xlsx export or QuickClick source file is required for this sandbox pass.

FACT: Product photos must be local files under `runtime/sandbox/pos_mvp_autodev/menu/product_photos`.

FACT: External photo fetch and generated product photos are not allowed as product evidence.

FACT: Product photos must meet `PHOTOBOOK_PRODUCT_GRADE` before market demo use.

FACT: Generated images, stock images, web-scraped images, and unknown-source images must not be used as product evidence.

FACT: Product photo AI prompts are generated from the real menu into `runtime/sandbox/pos_mvp_autodev/menu/product_photo_ai_prompts.json`.

FACT: Single-image Gemini handoff file is `runtime/sandbox/pos_mvp_autodev/menu/gemini_single_product_prompt.md`.

FACT: The single-image file lets the user change only product name, shot type, and angle for one image at a time.

FACT: All product photo prompts share style lock `LIAOGUO_PHOTOBOOK_STANDBY_STYLE_V1`.

FACT: Same visual series is required across different menu items; angle variation is allowed by shot type.

FACT: Google generation is user-manual only; the sandbox does not read Google accounts or call Google APIs.

FACT: AI-generated images remain candidate material until staff approval and must not be claimed as real product evidence.

INFO_REQUIRED: Current product photo state is `PHOTOBOOK_PRODUCT_PHOTOS_REQUIRED_NOT_ATTACHED`.

FACT: Standby display file is `runtime/sandbox/pos_mvp_autodev/ui/standby_xiaoj_menu.html`.

FACT: Standby display shows anchor XiaoJ and the real menu in the same frame.

FACT: Standby display is local display-only and must not control Chrome, external TV, Odoo, LINE, Google, or production services.

FACT: Production action remains blocked.

PRODUCTION_DEPLOY=FALSE
SERVICE_RESTART=FALSE
DB_WRITE=FALSE
ODOO_CORE_MUTATION=FALSE
PRODUCTION_LINE_ACTION=FALSE
PRODUCTION_GOOGLE_ACTION=FALSE
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
EXTERNAL_PHOTO_FETCH=FALSE
GENERATED_PRODUCT_PHOTO=FALSE
PHOTOBOOK_PRODUCT_GRADE_REQUIRED=TRUE
GOOGLE_ACCOUNT_ACTION=USER_MANUAL_ONLY
GOOGLE_API_CALL=FALSE
GENERATED_IMAGE_IS_PRODUCT_EVIDENCE=FALSE
SAME_STYLE_DIFFERENT_ITEMS_REQUIRED=TRUE
ANGLE_VARIATION_ALLOWED=TRUE
STANDBY_DISPLAY_ONLY=TRUE
CHROME_LIVE_CONTROL=FALSE

Verifier:

```bash
bash scripts/verify/verify_pos_mvp_sandbox.sh
```

Next HOLD boundary:

STATE=HOLD_PRODUCTION_ACTION
