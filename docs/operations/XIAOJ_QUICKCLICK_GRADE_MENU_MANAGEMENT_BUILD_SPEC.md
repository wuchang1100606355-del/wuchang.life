# XiaoJ QuickClick Grade Menu Management Build Spec

RUN_ID=D8_MANDATORY_TASK_20260624_083658_XIAOJ_QUICKCLICK_GRADE_MENU_AND_AUTH_LAND_PACKET_PREP
STATE=BUILD_SPEC_READY_FOR_HUMAN_REVIEW

## Design Principle

The cafe menu system must feel like a serious store tool, not a generated demo. It must use the shop's real menu and must be simple enough for a Vietnamese-speaking manager to operate during rush hour.

## Screen Modules

| Module | Must include |
| --- | --- |
| Store header | Store name, active menu, source lock status, route/auth gate status |
| Product table | Checkbox, ID/code, product name, category, add-on menu, inventory, updated time, actions |
| Category panel | Real category list, sort order, category edit, category move preview |
| Menu selector | Active QuickClick/Odoo menu, source hash, stale warning |
| Attribute panel | Size, temperature, sweetness, beans, meal type, custom shop attributes |
| Add-on panel | Required/optional groups, choices, price deltas, nested groups |
| Recommendations | Hidden, order-count based, custom recommended products |
| Batch tools | Select all/none, category move, availability, menu assignment, dry-run diff |
| Import/export | Import verified source, export menu index, export source hash |
| Message panel | Cashier/back-office live notices, cash advance evidence refs |
| XiaoJ operator | Browser action candidates, spoken summary, bilingual labels, confirm/cancel |

## Busy-Store Controls

| Operation | Control | Confirmation |
| --- | --- | --- |
| Price change | Dropdown or numeric stepper | Manager confirm |
| Return/refund candidate | Dropdown reason | Manager confirm, no payment capture in menu module |
| Category move | Dropdown category | Preview affected rows |
| Add-on assignment | Dropdown add-on group | Preview product option tree |
| Availability | Toggle | Dry-run then confirm |
| Batch update | Checkbox table | Diff summary before apply |
| Cash advance request | Form with reason/ref | Evidence record only |

## Language And Visual Layer

| Layer | Rule |
| --- | --- |
| Chinese | Source-of-truth product/menu text |
| Vietnamese | Manager-facing assist labels |
| English | Optional customer/training assist labels |
| Photos | Real product/store photos only |
| Tables | Primary representation for products and options |
| AI translation | Translate labels only; cannot create menu facts |

## XiaoJ Browser-Control Envelope

Every XiaoJ action must be represented as:

```json
{
  "intent": "candidate_action",
  "screen_ref": "menu_management",
  "target_ref": "product_or_menu_ref",
  "proposed_change": "human readable diff",
  "risk": "low|medium|high|hold",
  "requires_role": "manager|owner|cashier",
  "confirm_state": "draft|confirmed|cancelled",
  "member_plaintext": false,
  "payment_capture": false,
  "pos_order_created": false
}
```

## Required Verifiers Before Real Landing

| Verifier | Pass condition |
| --- | --- |
| Auth route verifier | LINE/Google/member registration routes are non-404 or intentionally held |
| Real menu verifier | QuickClick/Odoo/source documents agree or conflict is sealed |
| UI build verifier | Product table, selectors, attributes, add-ons, batch tools present |
| Role verifier | Owner/manager/cashier/staff action matrix present |
| Safety verifier | No secret read, no member plaintext, no POS order, no payment |
| Browser-control verifier | XiaoJ actions remain candidate-only until confirmed |

## Non-Negotiable Product Rules

- Do not create sandwich, egg pancake, or any invented item unless human source explicitly contains it.
- Do not use GPT prompt text as menu source.
- Do not treat translated labels as menu authority.
- Do not silently write Odoo/POS data from AI suggestions.
- Do not claim LINE/Google login works while routes are 404.
- Do not claim production-ready until real staff can use the flow end to end.

## Next LAND Implementation Order

1. Add/repair auth/member route shell so routes do not 404.
2. Add real menu source lock screen and conflict viewer.
3. Add menu management table with category/menu selectors.
4. Add attributes/add-ons panels.
5. Add edit/copy/archive candidate actions.
6. Add batch tools with preview diff.
7. Add Vietnamese manager labels and English assist labels.
8. Add live cashier/back-office message panel.
9. Add XiaoJ browser-control candidate envelope.
10. Run verifiers; hold before any restart, module upgrade, DB write, deploy, POS order, or payment.

## Current Prep Run Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
ODOO_DB_WRITE=FALSE
ODOO_MODULE_UPGRADE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
EMBEDDING_GENERATED=FALSE
ODOO_FILES_TOUCHED=FALSE
LINE_LOGIN_FILES_TOUCHED=FALSE
DO_NOT_TOUCH_AGENTS_MD=TRUE
