# Local Network Compliance Addendum（本地網路合規補充）

RUN_ID=LOCAL_NETWORK_COMPLIANCE_ADDENDUM_20260613_063900
STATE=LOCAL_NETWORK_COMPLIANCE_ADDENDUM_READY

## Safe Mode（安全模式）
- runtime_change=false
- tailscale_change=false
- dns_change=false
- router_change=false
- ddns_change=false
- service_restart=false
- secret_read=false
- raw_pii_read=false

## Local Network Profile（本地網路輪廓）
- ISP = Chunghwa Telecom fixed public IP network（中華電信固定 IP 網路）.
- Router / Gateway = ASUSWRT（華碩路由器）.
- ASUS DDNS = available as public naming resource（華碩 DDNS 可作為公開命名資源）.
- Link capacity = 1G network（1G 網路）.
- LAN gateway observed = 192.168.50.1.
- taiji01 LAN IP observed = 192.168.50.249.
- Tailscale observed public IPv4 = 220.135.21.74.
- taiji01 Tailscale IPv4 = 100.71.224.18.
- taiji01 Tailscale IPv6 = fd7a:115c:a1e0::b3a:e012.

## Governance Rule（治理規則）
- Fixed IP and ASUS DDNS are infrastructure resources, not permission grants.
- 固定 IP 與 ASUS DDNS 是入口資源，不是公開核心服務的理由。
- Public domain / DDNS must not directly expose SSH, Postgres, Docker, Odoo admin, Key Broker, Member Vault, or raw internal service ports.
- taiji01 remains core server / evidence chain / governance backend.
- Tailscale remains private management mesh.
- Public access must go through governed gateway, TLS, OAuth/SSO, ACL, audit, and no-plaintext context rules.

## Runtime HOLD（執行期維持 HOLD）
- no port forward change.
- no DDNS target change.
- no ASUS router setting change.
- no Tailscale ACL/grants change.
- no MagicDNS / DNS change.
- no Odoo exposure.
- no direct public SSH exposure.

## Final Sentence（核心句）
中華電信固定 IP、ASUS DDNS 與 1G 網路可作為本會服務入口資源；但核心服務不得裸露，必須經由 Tailscale 私有網、受控 Gateway、OAuth/SSO、ACL、稽核與無明文上下文治理。
