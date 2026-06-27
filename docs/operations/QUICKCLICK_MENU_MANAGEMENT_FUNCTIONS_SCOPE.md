# QuickClick Style Menu Management Functions Scope

RUN_ID=D8_MANDATORY_TASK_20260624_071412_QUICKCLICK_MENU_MANAGEMENT_FUNCTIONS_SCOPE_CAPTURE
STATE=FIELD_OBSERVED_TOTAL_FIELD_QUERIED
TARGET=聊國咖啡館重新總店菜單與 POS 後台功能

## Purpose

This scope captures the functions visible in the QuickClick menu management screen and converts them into a safe implementation target for the cafe system.

This is not a menu invention pass. Product names, categories, prices, add-ons, photos, translations, and availability must come from real cafe sources such as QuickClick export, verified screenshots, Odoo records, or human-approved shop materials.

## Required Function Groups

| Group | Function | Product Rule |
| --- | --- | --- |
| Product list | Display product code, product name, product attributes, category, add-on menu, inventory, update time, and row actions | Must use real source rows only |
| Product category selector | Filter product list by category | Category names must match real cafe taxonomy |
| Menu selector | Select active menu for the store, such as `聊國咖啡館重新店-QC` | Store/menu identity must pass collision check |
| Product category settings | Create, edit, sort, and assign categories | No fake emergency category as final authority |
| Add product | Add a new product only from human-approved real source | No GPT invented menu item |
| Edit product | Update product metadata, category, attribute, add-on group, photo, and availability | Requires preview and human confirmation before Odoo/POS write |
| Copy product | Duplicate a real product as a draft candidate | Must remain draft until verified |
| Delete product | Prefer disable/archive over destructive delete | Requires human approval |
| Recommended products | Support hidden, order-count based, and custom recommendations | Recommendation must not alter accounting/order records |
| Product attributes | Manage attribute groups and values such as size, temperature, sweetness, beans, meal type | Attribute ordering affects POS display |
| Add-on menu | Manage add-on groups, choices, price deltas, and required/optional rules | Add-ons must match real shop choices |
| Batch update | Select all/none and apply category/menu/availability changes | Batch writes require dry-run diff first |
| Import menu | Import production menu from verified QuickClick/Odoo source | Import must detect stale source conflict |
| Export/audit | Export current menu index, source hash, and change evidence | Required for rollback and store review |
| Role permission | Owner, manager, cashier, and staff scopes | Vietnamese manager flow must be clear enough for direct operation |
| Live notice | Back office and cash register need immediate messages | Message must be evidence-backed, not payment/order automation |
| Vendor advance | If vendor fees are paid from store cash advance, record as cash custody evidence | Does not create payment capture or accounting posting without approval |
| Multi-language support | Chinese source with English/Vietnamese assistive labels | AI may translate labels, but not invent menu facts |
| Photo support | Attach real product/store photos as references | Generated images are not menu truth |

## Minimum Product-Grade Behavior

1. The first screen should be operational, not marketing copy.
2. Menu management must work by table, image, and category, with clear icon actions.
3. A Vietnamese-speaking manager must be able to confirm what each button does without reading long Chinese instructions.
4. Dropdowns are acceptable for busy store operations such as return, price change, category move, and add-on selection, but the final action must show a confirmation state.
5. Every AI suggestion must be a candidate. It cannot silently create products, orders, payments, accounting entries, or member records.
6. Real menu source has priority over GPT text, demo JSON, emergency menu, and product prompt packs.

## Required Data Fields

| Field | Meaning |
| --- | --- |
| store_ref | Store identity, such as 聊國咖啡館重新總店 |
| menu_ref | Menu identity and source hash |
| product_code | QuickClick/Odoo product code |
| product_name_zh | Real Chinese product name |
| product_name_vi | Vietnamese assistive label |
| product_name_en | English assistive label |
| category_ref | Product category |
| addon_menu_ref | Add-on group |
| attribute_refs | Size, temperature, sweetness, bean, meal, or other attribute references |
| price | Human-approved price |
| inventory_state | Visible stock/availability status |
| available_in_pos | POS visibility flag |
| photo_ref | Real product or shop photo reference |
| source_ref | QuickClick export, screenshot, Odoo row, or human-approved document |
| source_hash | Evidence hash for the source |
| review_status | draft, verified, approved, landed, disabled |
| audit_ref | Change evidence and rollback pointer |

## Safety Gates

| Gate | Rule |
| --- | --- |
| Source gate | HOLD if real menu source is missing or contradictory |
| Collision gate | HOLD if store/menu/POS identity conflicts |
| Dry-run gate | All batch/product writes require a preview diff |
| Human gate | Odoo/POS writes require explicit human release |
| Payment gate | No payment capture in menu management |
| Order gate | No POS order creation in menu management |
| Member gate | No member plaintext in menu management |
| Secret gate | No `.env`, token, password, or config secret read |

## Implementation Phases

| Phase | Scope | Landing Rule |
| --- | --- | --- |
| P0 Source lock | Bring in verified QuickClick export/screenshots and current Odoo read-only product index | Docs/runtime only unless approved |
| P1 Catalog UI | Product list, filters, edit/copy/archive draft actions | Code changes require new task capsule |
| P2 Menu/category UI | Menu selector, category settings, sorting, assignment | Dry-run first |
| P3 Attributes/add-ons | Product attributes and add-on menu management | Must match real cafe options |
| P4 Recommendations | Hidden/order-count/custom recommendation controls | No accounting/order side effect |
| P5 Batch operations | Select all/none, category move, availability update | Preview diff required |
| P6 Translation/photo layer | Chinese source with Vietnamese/English assist labels and photo refs | Translation cannot create facts |
| P7 Store messaging | Back office/cashier live messages and cash advance evidence | No payment capture |
| P8 Odoo/POS landing | Write approved products/options into Odoo/POS | Requires explicit human authorization |

## Current Decision

STATE=HOLD_FOR_IMPLEMENTATION_APPROVAL

The functions are valid product targets. This run captured the scope only. Actual implementation will touch Odoo addon/UI/data paths and therefore requires a new explicit LAND packet that names allowed code paths and write limits.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
