# W3 Master Deploy Index（生成式部署總索引）

RUN_ID=W3_MASTER_DEPLOY_INDEX_20260613_064840
STATE=MASTER_DEPLOY_INDEX_READY

## Safe Mode（安全模式）
- runtime_change=false
- service_restart=false
- odoo_db_write=false
- tailscale_change=false
- dns_change=false
- router_change=false
- secret_read=false
- raw_pii_read=false

## Current Git Anchor（目前 Git 錨點）
- branch=main
- head_before=e5d8f0c

## Indexed Deployment Evidence（已索引部署證據）
- Total Field（總場）: docs/total_field/XIAOJ_MEMBER_SIDEBAR_TOTAL_FIELD_20260613_052845.md
- Five-in-One Generative Deploy（五合一生成式部署）: docs/deploy/five_in_one/FIVE_IN_ONE_GENERATIVE_DEPLOY_20260613_061417.md
- Compliance Settings（合規設定）: docs/compliance/settings/COMPLIANCE_SETTINGS_GENERATIVE_WRITE_20260613_063312.md
- Local Network Compliance（本地網路合規）: docs/compliance/network/LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900.md
- Redteam Paste Integrity Gate（紅隊貼上完整性閘）: docs/redteam/operation_windows/REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516.md

## Deployment Windows（部署窗位）
- W0_READONLY_PREFLIGHT = allowed.
- W1_EVIDENCE_WRITE = allowed after gates.
- W2_GIT_COMMIT = allowed after verification and exact staged-file check.
- W3_GENERATIVE_DEPLOY = allowed for non-runtime deployment packages.
- W4_RUNTIME_CHANGE = HOLD unless explicit human approval.
- W5_SECRET_OR_PII = HOLD unless explicit approval and isolated protocol.

## Next Deployable Items（下一批可生成式部署項目）
1. 8D Packet Schema SDK（八維封包 SDK）.
2. Member Sidebar XiaoJ UI Scaffold（會員側邊欄小J UI 骨架）.
3. Browser Action Bus Contract（瀏覽器動作匯流排契約）.
4. No-Plaintext Context Broker Spec（無明文上下文代理規格）.
5. Hybrid Key / API Broker Spec（混合金鑰與 API 代理規格）.
6. Counter XiaoJ Avatar Spec（櫃台小J主播規格）.
7. Merchant / Committee Connector Spec（商家／管委會連接器規格）.
8. Tailscale ACL / Grants Draft（Tailscale 權限草案，不套用）.
9. Domain / DNS Plan（網域與 DNS 規劃，不套用）.

## Core Rule（核心規則）
生成式部署只產生規格、封包、驗證與證據；不啟動服務、不改網路、不讀密鑰、不碰會員明文。
