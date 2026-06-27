# Market Feature Parity Matrix

STATE=MARKET_FEATURE_PARITY_CONVERGED

Each feature is included for product parity. `STATUS` is implementation state, not a claim that every feature is production-ready.

| FEATURE_NAME | USER_VALUE | SOURCE | STATUS | RISK | MINIMAL_SAFE_NEXT_ACTION |
|---|---|---|---|---|---|
| Menu browsing | Customer sees available products | ODOO_BUILTIN + EXISTING_WUCHANG_MODULE | READY | menu sync drift | Read Odoo product/menu through ORM |
| Categories | Faster ordering | ODOO_BUILTIN | READY | category mismatch | Map POS category to GUI filter |
| Product photos | Trust and appetite | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | generated photo may not match real product | Use reviewed product photo refs only |
| Product specifications | Avoid wrong orders | EXISTING_WUCHANG_MODULE | READY | option data incomplete | Use `wuchang.cafe.option.*` |
| Add-ons | Upsell and customization | EXISTING_WUCHANG_MODULE | READY | price delta mistakes | Backbrain validates option price |
| Ice level | Beverage personalization | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | option taxonomy drift | Map to option group |
| Sweetness | Beverage personalization | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | option taxonomy drift | Map to option group |
| Temperature | Beverage personalization | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | invalid combos | Backbrain rule table |
| Combo meal | Higher basket size | ODOO_BUILTIN + W7TP_8D_RUNTIME | PATCH_NEEDED | fiscal/discount ambiguity | Candidate only until POS rule mapping |
| Cart | Order staging | W7TP_8D_RUNTIME | PATCH_NEEDED | stale menu price | Recalculate locally before confirm |
| Quantity edit | Customer correction | W7TP_8D_RUNTIME | PATCH_NEEDED | negative qty | Backbrain bounds check |
| Notes | Special requests | ODOO_BUILTIN | PATCH_NEEDED | plaintext/sensitive notes | Limit to order note policy |
| Cancel | User control | W7TP_8D_RUNTIME | PATCH_NEEDED | accidental cancellation | Dry-run cancel packet |
| Reorder | Convenience | FUTURE_PAID_SERVICE | OPEN_SOURCE_REVIEW_NEEDED | member privacy | Use masked order template refs |
| Order summary | Prevent mistakes | W7TP_8D_RUNTIME | READY | projection mismatch | Use P2 projection pattern |
| Amount calculation | Trust and audit | ODOO_BUILTIN + NO_LLM_BACKBRAIN | READY | rounding/tax drift | Compare Odoo computed totals |
| Discount | Promotion support | ODOO_BUILTIN | CONFIG_NEEDED | unauthorized discount | Permissioned discount packet |
| Coupon | Campaign support | ODOO_BUILTIN | CONFIG_NEEDED | coupon fraud | Validate coupon server-side |
| Member price | Loyalty conversion | ODOO_BUILTIN + W7TP_8D_RUNTIME | CONFIG_NEEDED | plaintext member data | Use entitlement ref only |
| Pre-checkout confirm | Prevent wrong formal POS | W7TP_8D_RUNTIME | READY | bypass | Human confirm gate required |
| Product intro | AI sales support | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | hallucination | Cloud candidate plus local menu facts |
| Recommendation | Basket growth | CLOUD_ANCHOR_ADAPTER + NO_LLM_BACKBRAIN | PATCH_NEEDED | unsuitable recommendation | Rule-filtered candidate list |
| Add-on suggestion | Upsell | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | pushy UX | Limit to compatible option groups |
| Q&A | Customer support | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | hallucination | Answer from menu facts and evidence |
| Multi-turn dialogue | Natural ordering | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | lost state | Store 8D state refs only |
| Voice readout | Accessibility | SUNMI_CONTAINER | CONFIG_NEEDED | speaks sensitive content | Adapter blocks member/payment text |
| Customer screen mode | Self-order and display | EXISTING_WUCHANG_MODULE | READY | live control risk | Dry-run display first |
| Staff mode | Faster cashier work | ODOO_BUILTIN + W7TP_8D_RUNTIME | PATCH_NEEDED | permission bypass | Authenticated Odoo route |
| Creditor demo display | Funding/product proof | W7TP_8D_RUNTIME | PATCH_NEEDED | looks fake if disconnected | Evidence-backed route only |
| 70B candidate brain | Rich language and suggestions | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | cloud overreach | Candidate contract only |
| No-LLM backbrain | Deterministic trust | W7TP_8D_RUNTIME | READY | rule table incomplete | Expand verifier cases |
| Cloud anchor interface | Preserve existing anchor subscription | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | secret leakage | iframe/SDK placeholder only |
| Anchor iframe/SDK placeholder | Visual avatar continuity | CLOUD_ANCHOR_ADAPTER | PATCH_NEEDED | vendor lock-in | Adapter interface and no secrets |
| Sound output | Ordering feedback | SUNMI_CONTAINER | CONFIG_NEEDED | device API unknown | Add adapter interface |
| SUNMI voice container | Hardware-grade voice | SUNMI_CONTAINER | HOLD_OPERATOR_CONFIRM | API unavailable locally | Operator confirms docs/API |
| TTS adapter | Browser fallback | OPEN_SOURCE_CANDIDATE | OPEN_SOURCE_REVIEW_NEEDED | browser compatibility | Review Web Speech support |
| Volume/speed/role switch | Better UX | SUNMI_CONTAINER | PATCH_NEEDED | inconsistent device behavior | Normalize adapter settings |
| Offline prompts | Resilience | W7TP_8D_RUNTIME | PATCH_NEEDED | stale copy | Static phrase registry |
| Queue call voice | Store operations | SUNMI_CONTAINER | PATCH_NEEDED | wrong queue call | Packetized queue event |
| LINE login | Member entry | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | secret/config missing | Use config key names only |
| Google login | Member entry | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | secret/config missing | Use config key names only |
| Phone/email fallback | Inclusion | ODOO_BUILTIN | CONFIG_NEEDED | member plaintext exposure | Masked review fields |
| Group member 8D code | Viral group onboarding | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | DB upgrade needed | Operator module upgrade review |
| group_ref | Group routing | W7TP_8D_RUNTIME | PATCH_NEEDED | topology leakage | Redacted refs only |
| packet_ref | Short QR payload | W7TP_8D_RUNTIME | PATCH_NEEDED | spoofing | nonce + ttl + hash |
| d8_ref | Envelope proof | W7TP_8D_RUNTIME | PATCH_NEEDED | weak sealing | hmac_ref and evidence seal |
| Provisional registration | Safe onboarding | EXISTING_WUCHANG_MODULE | READY | duplicate identity | hash external auth |
| Human review | Trust gate | EXISTING_WUCHANG_MODULE | READY | review backlog | Admin list and status |
| Member permissions | Entitlement | ODOO_BUILTIN + W7TP_8D_RUNTIME | CONFIG_NEEDED | overgrant | role policy table |
| Masking | Privacy | EXISTING_WUCHANG_MODULE | READY | accidental display | List views hide plaintext |
| No member plaintext | Cloud safety | W7TP_8D_RUNTIME | READY | drift | verifier forbidden checks |
| Odoo POS | Formal transaction engine | ODOO_BUILTIN | READY | direct LLM write | formal gate contract |
| Product | Catalog authority | ODOO_BUILTIN | READY | stale cache | ORM read on candidate validate |
| Price | Payment trust | ODOO_BUILTIN | READY | price drift | Odoo recompute before confirm |
| Tax | Compliance | ODOO_BUILTIN | CONFIG_NEEDED | wrong tax mapping | POS config review |
| Inventory | Stock control | ODOO_BUILTIN | CONFIG_NEEDED | stock not enabled | Inventory policy review |
| Receipt | Customer proof | ODOO_BUILTIN | READY | print config | Odoo POS receipt config |
| Table number | Dine-in support | ODOO_BUILTIN | CONFIG_NEEDED | table mismatch | POS restaurant config |
| Takeout/dine-in | Operations | ODOO_BUILTIN | CONFIG_NEEDED | tax/service drift | Order type field |
| Kitchen ticket | Fulfillment | ODOO_BUILTIN | CONFIG_NEEDED | printer routing | Kitchen display/print review |
| Accounting | Legal records | ODOO_BUILTIN | READY | wrong journal | No AI write, Odoo only |
| Reports | Management | ODOO_BUILTIN + EXISTING_WUCHANG_MODULE | READY | scope mixing | topology filter |
| Multi-store | Branch growth | EXISTING_WUCHANG_MODULE | READY | branch accounting mix | topology boundary checks |
| Permissions | Staff safety | ODOO_BUILTIN | READY | public route overreach | auth/user route split |
| Audit trail | Proof | ODOO_BUILTIN + W7TP_8D_RUNTIME | PATCH_NEEDED | missing seal | evidence per candidate |
| CRM | Retention | ODOO_BUILTIN | CONFIG_NEEDED | consent | masked member refs |
| Loyalty | Repeat visits | ODOO_BUILTIN | CONFIG_NEEDED | program rules | Odoo loyalty config |
| Points / happiness coin | Community economy | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | value accounting | interface only first |
| Campaigns | Sales growth | ODOO_BUILTIN | CONFIG_NEEDED | abusive discounts | permissioned promotion |
| Community broadcast | Outreach | EXISTING_WUCHANG_MODULE | CONFIG_NEEDED | spam/privacy | consent gate |
| LINE OA | Messaging | FUTURE_PAID_SERVICE | HOLD_OPERATOR_CONFIRM | credentials/send risk | candidate notification only |
| Google member | Lower friction | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | OAuth config | no secret read |
| Revisit reminder | Retention | FUTURE_PAID_SERVICE | OPEN_SOURCE_REVIEW_NEEDED | consent | opt-in event only |
| Group member | Group onboarding | EXISTING_WUCHANG_MODULE | PATCH_NEEDED | review load | 8D QR provisional flow |
| Volunteer/community welfare | Differentiation | EXISTING_WUCHANG_MODULE | CONFIG_NEEDED | mission drift | separate scope |
| Public benefit feedback | Brand trust | EXISTING_WUCHANG_MODULE | CONFIG_NEEDED | accounting claims | evidence-backed reports |
| No direct LLM write | Safety | W7TP_8D_RUNTIME | READY | bypass | verifier |
| Formal POS gate | Transaction safety | W7TP_8D_RUNTIME | READY | operator misuse | separate authorization |
| Payment capture gate | Payment safety | W7TP_8D_RUNTIME | READY | accidental capture | payment false in contracts |
| W7TP 8D packet | Patent embodiment | W7TP_8D_RUNTIME | READY | malformed packet | schema verifier |
| Hash chain | Evidence | W7TP_8D_RUNTIME | PATCH_NEEDED | broken chain | parent hash test |
| Evidence seal | Proof | W7TP_8D_RUNTIME | READY | missing refs | Total Field seal |
| Role permission | Governance | ODOO_BUILTIN | READY | overgrant | group policy |
| Privacy boundary | Trust | W7TP_8D_RUNTIME | READY | plaintext leakage | forbidden scanner |
| No plaintext to cloud | Sovereignty | W7TP_8D_RUNTIME | READY | prompt leakage | cloud candidate contract |
| Dry-run/formal split | Deployment safety | W7TP_8D_RUNTIME | READY | confused state | formal gate contract |

