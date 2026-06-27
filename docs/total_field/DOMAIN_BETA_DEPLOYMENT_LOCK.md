# Domain Beta Deployment Lock

STATE=DOMAIN_BETA_DEPLOYMENT_REQUIRED

## Reason

127.0.0.1 / localhost cannot be treated as the real association officer closed-beta entry.

Missing Google login and LINE login on the intended Odoo login page is a deployment/configuration error for the target system.

## Required domain entry map

assoc.wuchang.life
- 協會幹部封測入口
- Odoo backend / officer login
- requires Odoo account + valid 8D packet

pos.wuchang.life
- 重新總店小J POS入口
- maps to /wuchang/xiaoj/ordering
- requires 8D packet gate or counter-AI guest packet

auth.wuchang.life
- Google / LINE OAuth callback / authorization bridge
- not a personal identity authority by itself

api.wuchang.life
- LINE webhook / Odoo API / XiaoJ callback
- no plaintext behavior logs only

node.wuchang.life
- 團體會員節點機管理與健康檢查
- managed node identity and 8D packet status

## Identity rule

LINE OA = 團體會員通道
Google / LINE login = entry channel only
Odoo-issued / association-governed 8D packet = actual authority
8D code / QR / URL = packet_ref or controlled reference

## 8D packet gate

/wuchang/xiaoj/ordering must require valid 8D packet or controlled packet_ref.

8D packet contains or references:
- AI identity
- device binding
- Odoo function authority
- AI function authority
- dedicated XiaoJ service
- association-verifiable true identity
- non-plaintext front-stage behavior refs
- execution permissions
- GT transmit/receive rights
- Total Field feature code
- receiver generation code requirement

## Data rule

Plaintext and trade secrets only on developer local external hard drive.

Cloud / Odoo / LINE / node machines may store only:
packet_ref, manifest_ref, hash, ledger_receipt, device_ref, AI ref, auth scope, action type, risk state, receipt.

## Safety

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

NEXT_ACTION=INSPECT_DOMAIN_DNS_PROXY_ODOO_BASE_URL
