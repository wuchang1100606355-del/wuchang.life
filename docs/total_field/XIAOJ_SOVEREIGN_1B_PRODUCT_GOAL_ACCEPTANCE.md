# XiaoJ Sovereign 1B Product Goal Acceptance

STATE=XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL_ACCEPTANCE_READY
CHECK_DATE=2026-06-27

## Objective Under Test

產品級高質感的主權 AI 1B 控制瀏覽器，理解使用者傾向，呈現服務熱誠的社區小J，具備與本會的生成式傳輸，回傳無敏 8 維度封包，內含雲端算力與行為資訊。

## Acceptance Matrix

| Requirement | Evidence |
| --- | --- |
| Product-grade member browser surface | `web/xiaoj_member_browser_cockpit/`, `web/xiaoj_member_browser_extension/`, `runtime/member_browser/releases/*` |
| 1B-class local controller | `tools/member_browser/xiaoj_member_browser_1b_controller.py`, `tools/member_browser/Modelfile.xiaoj-member-browser-1b` |
| Browser control is symbolic and verifier-gated | `BROWSER_BRIDGE_RETURN_PACKET`, extension no host permissions, no cookie permission |
| User tendency is ref-only | `member_preference_ref`, `service_style_ref`, `member_tendency_ref`, `quota_bucket_ref` |
| Warm community XiaoJ posture | `service_style_ref:community_xiaoj_warm_daily`, Modelfile service rules |
| Generative transmission to association | `ASSOCIATION_USAGE_ADMISSION_PACKET`, `CLOUD_CANDIDATE_RETURN_PACKET` |
| No-sensitive 8D return | `member_plaintext_transferred=false`, `secret_transferred=false`, `raw_api_key_transferred=false`, `oauth_token_transferred=false` |
| Cloud compute and behavior info present | `cloud_compute_ref`, `behavior_info_ref`, `action_trace_ref`, `member_tendency_ref` |
| Odoo identity/function boundary | `odoo_identity_ref`, `odoo_role_ref`, `odoo_function_item_refs`, no Odoo write |
| Community daily-life service seed | `web/community_activities.json`, 五常公園熱舞社運動社團 |
| Payment boundary | management fee payment intent candidate only; payment capture remains false |
| Release self-verification | `scripts/verify/verify_xiaoj_member_browser_release.py` |
| Overall goal verification | `scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py` |

## Commands

```bash
python3 scripts/verify/verify_wuchang_website_quality.py
python3 scripts/verify/verify_xiaoj_member_browser_cockpit.py
python3 scripts/verify/verify_xiaoj_member_browser_release.py
python3 scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py
```

## Hard Safety Requirements

- No DB execution.
- No Odoo/POS write.
- No payment capture.
- No service restart or deploy.
- No secret, OAuth token, cookie, password, localStorage, member plaintext, raw audio, phone, address, ID.
- No cloud authority. Cloud returns candidate result only.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_API_KEY_OUTPUT=FALSE
RAW_AUDIO_SAVED=FALSE
DB_WRITE=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
