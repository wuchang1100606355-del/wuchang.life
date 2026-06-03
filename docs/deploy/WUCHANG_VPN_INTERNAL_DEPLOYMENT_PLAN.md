# 五常智慧雲｜wuchang.life VPN 內網部署規劃

## 部署原則

首頁公開，後台內網。

公開服務：
- wuchang.life
- www.wuchang.life
- docs.wuchang.life
- business.wuchang.life
- property.wuchang.life
- fund.wuchang.life
- carbon.wuchang.life

VPN / Tailscale 內網服務：
- api.wuchang.life
- odoo.wuchang.life
- ai.wuchang.life
- spatial.wuchang.life
- voice.wuchang.life
- admin.wuchang.life

## 內網主節點

taiji01
Tailscale IP: 100.71.224.18

## 內網 DNS

api.wuchang.life      A 100.71.224.18 DNS only
odoo.wuchang.life     A 100.71.224.18 DNS only
ai.wuchang.life       A 100.71.224.18 DNS only
spatial.wuchang.life  A 100.71.224.18 DNS only
voice.wuchang.life    A 100.71.224.18 DNS only
admin.wuchang.life    A 100.71.224.18 DNS only

不得使用 Cloudflare proxy 橘雲代理 Tailscale 100.x 內網位址。

## 服務對應

api.wuchang.life      -> 127.0.0.1:8088
odoo.wuchang.life     -> 127.0.0.1:8069
ai.wuchang.life       -> 127.0.0.1:3000
spatial.wuchang.life  -> 127.0.0.1:8099
voice.wuchang.life    -> 127.0.0.1:8098

## 安全原則

- Odoo 不裸露公網。
- Taiji Gateway 不裸露公網。
- AI / Open WebUI 不裸露公網。
- Voice / Dynamic QR 不裸露公網。
- admin.wuchang.life 只能 VPN 內使用。
- 所有高權限服務仍須 Gateway、登入、稽核與本人度量規則。
- 目前為開發期間、原型驗證期間、公益實證準備期間，非正式營運期間。
