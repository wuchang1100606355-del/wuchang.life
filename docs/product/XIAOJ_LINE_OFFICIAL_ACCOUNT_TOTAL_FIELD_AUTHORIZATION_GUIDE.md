# XiaoJ LINE Official Account Total-Field Authorization Guide

STATE=P1_AUTHORIZATION_MODEL_READY_FOR_HUMAN_REVIEW

## Core Decision

LINE 官方帳號不應把「總場」加入成無限制管理員。

正確做法是：

```text
Human owner/admin keeps LINE Official Account authority
  -> LINE Official Account enables Messaging API
  -> token and channel secret stay in vault/runtime resolver
  -> total field receives only refs and webhook events
  -> total field confirms intent in natural language
  -> total field drafts candidate config packet
  -> human owner/admin reviews and approves
  -> runtime connector acts only after release packet
```

## Why

LINE 官方帳號與 LINE WORKS 是不同產品面。LINE 官方帳號對外服務會員、顧客與社群；LINE WORKS 比較偏內部員工/組織通知。兩者都可以接總場，但權限應分開。

同時，LINE 官方帳號本身也要分主體。協會官方帳號與咖啡館商家官方帳號不是同一個帳號，也不是同一組 refs：

```text
Association LINE Official Account
  -> association member service
  -> public interest / governance notice
  -> sovereign member onboarding
  -> association activity notice

Cafe LINE Official Account
  -> cafe merchant customer service
  -> cafe POS order candidate notice
  -> consented cafe product promotion
  -> payment / pickup notice only after Odoo authority gate
```

不得把協會官方帳號拿去承接咖啡館 POS、付款、商品促銷、商家會員營運或咖啡館客服。若咖啡館需要 LINE 官方帳號，必須使用獨立咖啡館商家帳號，或至少使用獨立 refs、獨立 owner/admin approval、獨立 audience/consent policy、獨立 webhook endpoint 與獨立 release packet。

咖啡館公開入口仍必須掛在協會核准子域下。也就是說，咖啡館可有自己的商家 LINE 官方帳號與 Messaging API channel，但 LINE webhook、LINE Login/callback、點餐 landing、會員候選頁、POS 候選頁與商品頁，必須使用協會核准的子域與 DNS / reverse proxy release refs，不得使用未核准獨立網域。

若操作者回報咖啡館 API、LINE Developers provider 或 channel 控制權疑似被第三方廠商佔據，或咖啡館管理角色不完整，這只能進入「協會保護性支援」流程。協會可以協助提供核准子域、DNS / reverse proxy、webhook relay、LINE Login callback relay、evidence seal、vendor access review 與 provider admin role review；但協會不能因此靜默接管咖啡館商業 owner 身份，不能保存明文 channel token / channel secret，也不能把協會官方帳號拿去跑咖啡館 POS、付款、促銷或商品客服。

此類補救流程在完成下列 refs 前必須保持 HOLD：

```text
cafe_api_control_risk_ref
association_api_support_release_ref
provider_admin_role_review_ref
vendor_access_review_ref
association_gateway_ref
association_subdomain_ref
dns_or_reverse_proxy_release_ref
webhook_relay_ref
callback_relay_ref
human_owner_admin_release_ref
runtime_secret_rotation_ref
```

總場可以是你的數位代理，但不能成為保存明文 token、LINE 密碼或官方帳號超管權限的主體。總場的角色是：

```text
intent interpreter
configuration drafter
policy verifier
release packet builder
evidence sealer
```

不是：

```text
LINE account owner
credential owner
unbounded admin
silent production changer
```

## Human Setup In LINE

1. 用你的人類 owner/admin 帳號登入 LINE Official Account Manager。
2. 建立或確認 LINE 官方帳號。
3. 啟用 Messaging API；啟用後會建立 Messaging API channel。
4. 在 LINE Developers Console 確認 provider 與 Messaging API channel。
5. 設定 webhook URL，但正式啟用前先用候選/測試 endpoint。
6. 將 channel access token 與 channel secret 放入 vault 或 runtime resolver，不貼到 Odoo、repo、ChatGPT 或文件。
7. 只把下列 refs 交給總場：

```text
line_official_account_ref
line_provider_ref
messaging_api_channel_ref
webhook_endpoint_ref
channel_secret_ref
channel_access_token_runtime_ref
message_policy_ref
audience_policy_ref
consent_policy_ref
human_owner_admin_release_ref
```

Human-fill refs template:

```bash
python3 tools/xiaoj_line_official_account_refs_builder.py \
  --input packets/product_av_ordering_ai/line_official_account_refs_template.json \
  --pretty
```

The untouched template must stay `HOLD_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT`.
After you replace every placeholder with safe refs, it may become
`LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE`.

## Natural Language Approval Flow

你可以對總場說：

```text
幫我把 LINE 官方帳號設定成咖啡館會員客服模式：
新朋友加入先歡迎，詢問是否要領會員小J；
促銷訊息只能發給已同意會員；
付款、訂單、個資都不能由 LLM 自行判定；
設定完成後給我核定，不要直接生效。
```

總場應輸出：

```text
CONFIG_CANDIDATE
intent_summary
proposed_webhook_policy
proposed_message_policy
audience_policy_refs
consent_policy_refs
risk_flags
release_required=true
human_approval_required=true
evidence_hash
```

Local/API command:

```bash
python3 tools/xiaoj_line_official_account_config_candidate.py \
  --intent "幫我把 LINE 官方帳號設定成咖啡館會員客服模式，新朋友加入先歡迎並詢問是否領用會員小J；促銷只發給已同意會員；付款、訂單、個資不得由 LLM 自行判定；設定完成後給我核定，不要直接生效。" \
  --pretty
```

Odoo JSON API:

```text
POST /wuchang/xiaoj/api/line-official-account-config-candidate
auth=user
```

Webhook candidate API:

```text
POST /wuchang/xiaoj/api/line-official-account-webhook-candidate
auth=user
```

Local webhook candidate command:

```bash
python3 tools/xiaoj_line_official_account_webhook_candidate.py \
  --payload runtime/local_test/line_official_account_webhook_payload.json \
  --headers runtime/local_test/line_official_account_webhook_headers.json \
  --verification runtime/local_test/line_official_account_signature_verification_ref.json \
  --pretty
```

Future LINE webhook shell:

```text
POST /wuchang/xiaoj/line-official-account/webhook
auth=public
```

P1 webhook shell rule:

```text
no channel secret read
no LINE reply
no DB write
no raw userId echo
no replyToken echo
signature verification must be represented by a verified ref before READY
```

This returns a `W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE_V1`
packet. With missing refs it must stay `HOLD_NEEDS_HUMAN_APPROVAL`; with safe
refs it may become `READY_FOR_HUMAN_APPROVAL`, but still does not change LINE
settings.

Odoo operator page:

```text
WuChang Cafe / LINE Official Account Config
```

Operator flow:

```text
enter natural-language intent
enter LINE Official Account refs
click Build Refs Draft
click Build Config Candidate
review Candidate Packet / Failure Reasons
human owner/admin applies settings in LINE only after approval
```

## Approval States

```text
CONFIG_CANDIDATE
HOLD_NEEDS_HUMAN_APPROVAL
READY_FOR_HUMAN_APPROVAL
EXECUTED_AFTER_RELEASE
DEAD_LETTER
```

LLM 或 Gemini 只能產生候選設定文字，不能直接把設定改到 LINE。

## What You Should Not Give Me

- LINE 密碼
- channel access token 原文
- channel secret 原文
- private key 原文
- raw LINE user ID
- 會員電話、地址、email、身分證、付款資訊

## What You Can Give Me

- 官方帳號用途
- 歡迎語氣與品牌語氣
- 哪些事件要通知
- 哪些族群可以收到訊息
- 你已在 LINE 後台建立的 ref 名稱
- masked 或 hash 後的 target/user/channel refs
- 是否已啟用 Messaging API
- 是否已設定 webhook URL
- 咖啡館要使用的協會核准子域 ref
- DNS / reverse proxy / TLS certificate release refs
- 咖啡館 API 控制權風險 ref
- 協會保護性 gateway / relay release refs
- vendor access review 與 provider admin role review refs

## Product Rule

```text
Total field may draft and verify.
Human owner/admin approves.
Runtime resolver reads secrets only in memory after release.
No plaintext token or member plaintext enters candidate packet.
Association LINE Official Account and cafe merchant LINE Official Account are separate subjects.
Cafe external endpoints must use association-approved subdomains.
Association protective gateway support may mitigate cafe API control risk, but cannot mix subjects, hold plaintext secrets, or activate production without human owner/admin release.
```
